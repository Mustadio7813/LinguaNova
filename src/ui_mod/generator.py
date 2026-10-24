# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — standalone interface MOD generator.
"""Scan, translate, validate and publish the isolated interface MOD.

Corrections of 2026-10-17 (root causes confirmed on the Portuguese→Polish case):

1. Language codes: target/source now go through ``languages.api_code`` (the
   five-language catalogue). The old 10-entry table forwarded Ren'Py folder
   names such as ``"polish"`` to the engines.
2. Source language: ``auto`` is resolved like the main pipeline (offline
   py3langid, then the engine's own detector). Before, ``sl=auto`` went to
   Google's batch-separator request, which detects ONE language for up to 50
   joined strings; alphabetically-sorted batches full of English/debug strings
   were read as English and the Portuguese was left in place.
3. Acceptance: every answer passes ``quality.validate_translation`` (structure,
   target script, language identification, untranslated residue). Rejected
   answers are retried one by one and otherwise stay pending — never published.
4. Caches: MOD bypasses the shared TranslationManager cache (keyed by
   target+text, ignoring the source language) and keeps its own provenance in
   ``linguanova_mod_hook_data.json``. ``linguanova_mod_manual.json`` now holds only
   hand edits; the old file, which mirrored every machine answer and was re-read
   as "manual" on the next run, is backed up and no longer trusted.
5. Candidates: Python code, expressions and debug formats are excluded
   (``filters.code_exclusion_reason``).
6. Output: readable multilanguage ``.rpy``; all files are staged, checked and then
   published together with a backup of the previous MOD files.
"""
from __future__ import annotations

import asyncio
from contextlib import nullcontext
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import unicodedata
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.core.translator import TranslationRequest

from .engine_support import request_code, support as engine_support
from .filters import code_exclusion_reason, unwrap_marked_literal
from .fonts import FontFetcher, plan_fonts
from .glossary import GLOSSARY_FILE, consistent, exact_term, leaked_term_tokens, load_glossary, protect_terms, restore_terms
from .hook_check import check_hook
from .languages import ModLanguage, api_code, char_script, folder_aliases, resolve_language
from .protect import is_junk, preserve_edge_whitespace, protect_mod_text, restore_mod_text, validate_mod_translation
from .quality import (
    VALIDATION_VERSION, QualityVerdict, language_identification_available, summarise, validate_translation,
)
from .scanner import ModProjectScanner, ModScanReport, find_legacy_mod_tl_files, resolve_game_dir
from .ui_mod_hook_template import MOD_HOOK_FORMAT, render_ui_mod_hook_multi

logger = logging.getLogger("LinguaNova")

DATA_SCHEMA = 2
DATA_FILE = "linguanova_mod_hook_data.json"
MANUAL_FILE = "linguanova_mod_manual.json"
REPORT_FILE = "linguanova_mod_report.json"
BACKUP_DIR = "linguanova_mod_backup"
TRANSLATION_CHUNK = 200
# Second-opinion retries go one string per request. Two in flight (was 4)
# keeps Google/Bing below their burst limits; the engines' own 429 cooldown
# still applies on top of this.
RETRY_CONCURRENCY = 2
# A whole chunk that fails with an exception (network drop, 429 storm) is
# retried as a chunk after these pauses before falling back to 200 single
# requests, which would only make a rate limit worse.
CHUNK_RETRY_DELAYS = (4.0, 12.0)
# UI strings whose translation grows this much are listed in the report as
# possible overflow candidates (fixed-size boxes in the game's screens).
EXPANSION_REPORT_RATIO = 1.25
EXPANSION_REPORT_MIN_CHARS = 40


def _api_language(value: str) -> str:
    """Return an engine code only for the five supported languages."""
    return api_code(value)


@dataclass
class ModGenerationResult:
    success: bool
    message: str
    output_path: str = ""
    candidates: int = 0
    translated: int = 0
    rejected: int = 0
    coverage: float = 0.0
    visible_rpy_files: int = 0
    decompiled_rpyc_files: int = 0
    archive_script_files: int = 0
    skipped_compiled_files: int = 0
    pending: int = 0
    excluded: int = 0
    partial: bool = False
    unchanged: int = 0
    source_language: str = ""
    target_language: str = ""
    report_path: str = ""
    message_key: str = ""
    languages_generated: int = 0
    languages_total: int = 0


# ── user-facing messages ─────────────────────────────────────────────────────
# #MOD — every message has a locale key (locales/<lang>.json); the English text
# is the fallback. The backend passes its own translator (``ui_text``) so the
# messages follow LinguaNova's interface language.
UiText = Callable[..., str]

MESSAGES: Dict[str, str] = {
    "mod_msg_no_candidates": "No interface text candidates were detected.",
    "mod_msg_unknown_target": "Unknown MOD target language: {language}",
    "mod_msg_unknown_source": "Unknown MOD source language: {language}",
    "mod_msg_same_language": "Source language ({source}) equals the target ({target}); nothing to translate.",
    "mod_msg_engine_unsupported": "The selected engine cannot translate into {target}: {detail}. "
                                  "Nothing was sent or written.",
    "mod_msg_all_rejected": "All detected MOD strings were rejected or failed translation; nothing was written. "
                            "Pending={pending}.",
    "mod_msg_analysis": "MOD analysis complete: {total} unique interface texts from {sources} script source(s); "
                        "{excluded} code/debug strings excluded. Visible .rpy={rpy}, decompiled .rpyc={rpyc}, "
                        "RPA scripts={rpa}, unresolved compiled={unresolved}.",
    "mod_msg_generated": "MOD generated: {translated}/{total} game texts ({coverage}%) for {target} "
                         "[source {source} via {method}]. Pending={pending}, unchanged={unchanged}, "
                         "excluded code/debug={excluded}. Report: {report}. Output: {output}",
    "mod_msg_generated_partial": "MOD generated PARTIALLY: {translated}/{total} game texts ({coverage}%) for "
                                 "{target} [source {source} via {method}]. Pending={pending}, "
                                 "unchanged={unchanged}, excluded code/debug={excluded}. Report: {report}. "
                                 "Output: {output}",
    "mod_msg_legacy_warning": "WARNING: {count} old MOD native file(s) still active in tl/{folder}/ (see report).",
    "mod_progress_start": "MOD: source={source} ({method}), target={target}",
    "mod_progress_chunk": "MOD: {done}/{total} → {target}",
    "mod_progress_retry": "MOD: retrying {count} rejected strings individually",
    "mod_progress_done": "MOD: {translated} translated, {unchanged} unchanged, {pending} pending of {total}",
}


def _message(ui_text: Optional[UiText], key: str, **values) -> str:
    """Localized text for ``key``; English if the translator is missing or fails."""
    default = MESSAGES[key]
    if ui_text is not None:
        try:
            text = ui_text(key, default, **values)
            if isinstance(text, str) and text:
                return text
        except Exception:
            pass
    try:
        return default.format(**values)
    except (KeyError, IndexError, ValueError):
        return default


@dataclass
class _Entry:
    translation: str
    origin: str                  # manual | machine | existing_tl | reused
    engine: str = ""
    source_lang: str = ""
    target_lang: str = ""
    validation: int = VALIDATION_VERSION
    status: str = "accepted"     # accepted | manual_unchecked

    def to_json(self) -> Dict[str, object]:
        return {
            "translation": self.translation, "origin": self.origin, "engine": self.engine,
            "source_lang": self.source_lang, "target_lang": self.target_lang,
            "validation": self.validation, "status": self.status,
        }


def _safe_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "game").encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").lower()
    return normalized or "game"


def _project_game_name(project_path: str, game_dir: Path) -> str:
    p = Path(project_path)
    if p.is_file() and p.suffix.lower() == ".exe":
        return _safe_slug(p.stem)
    root = game_dir.parent if game_dir.name.lower() == "game" else game_dir
    return _safe_slug(root.name)


def _json_dumps(payload: Dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def _read_json(path: Path) -> Optional[Dict[str, object]]:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"MOD file is invalid JSON: {path} (line {exc.lineno}, column {exc.colno})") from exc
    except OSError as exc:
        raise OSError(f"Could not read MOD file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"MOD file must contain a JSON object: {path}")
    return payload


def _write_json_atomic(path: Path, payload: Dict[str, object]) -> None:
    """Kept for compatibility with older callers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(_json_dumps(payload))
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


# ── candidates ───────────────────────────────────────────────────────────────

def _collect_candidates(grouped: Dict[str, list]) -> Tuple[List[str], Dict[str, List[str]], Dict[str, str]]:
    """Return (originals, contexts, excluded{text: reason})."""
    contexts: Dict[str, set] = {}
    excluded: Dict[str, str] = {}
    for raw_text, occurrences in grouped.items():
        text = unwrap_marked_literal(raw_text) or raw_text
        if is_junk(text):
            excluded[raw_text] = "junk"
            continue
        reason = code_exclusion_reason(text)
        if reason:
            excluded[raw_text] = reason
            continue
        bucket = contexts.setdefault(text, set())
        for occurrence in occurrences:
            if getattr(occurrence, "screen", ""):
                bucket.add(occurrence.screen)
    originals = sorted(contexts, key=lambda s: (s.casefold(), s))
    return originals, {k: sorted(v) for k, v in contexts.items()}, excluded


# ── source language ──────────────────────────────────────────────────────────

def _run(loop: asyncio.AbstractEventLoop, coro):
    return loop.run_until_complete(coro)


def _resolve_source_language(
    requested: Optional[ModLanguage],
    texts: Sequence[str],
    target: ModLanguage,
    engine,
    translation_manager,
    loop: asyncio.AbstractEventLoop,
    detector: Optional[Callable[[Sequence[str]], Optional[str]]] = None,
) -> Tuple[Optional[ModLanguage], str]:
    """Same order as the main pipeline: explicit > offline py3langid > engine detector."""
    if requested is not None:
        return requested, "requested"
    samples = [t for t in texts if len(t.split()) >= 3][:2000]
    detected: Optional[str] = None
    method = "undetermined"
    try:
        if detector is not None:
            detected = detector(samples)
            method = "custom"
        else:
            from src.utils.lang_detect import detect_source_language
            detected = detect_source_language(samples)
            method = "offline_py3langid"
    except Exception as exc:
        logger.debug("[#MOD] offline source detection failed: %s", exc)
        detected = None
    if not detected:
        translator = getattr(translation_manager, "translators", {}).get(engine) if translation_manager else None
        detect = getattr(translator, "detect_language", None)
        if callable(detect) and samples:
            try:
                detected = _run(loop, detect(samples, target_lang=target.api))
                method = "engine_detector"
            except Exception as exc:
                logger.warning("[#MOD] engine source detection failed: %s", exc)
                detected = None
    lang = resolve_language(detected) if detected else None
    if lang is None:
        return None, "undetermined"
    return lang, method


# ── translation ──────────────────────────────────────────────────────────────

def _bypass(translation_manager):
    factory = getattr(translation_manager, "bypass_cache", None)
    if callable(factory):
        try:
            return factory()
        except Exception:
            return nullcontext()
    return nullcontext()


async def _translate_requests(translation_manager, requests: List[TranslationRequest]):
    results = await translation_manager.translate_batch(requests)
    if results is None or len(results) != len(requests):
        got = 0 if results is None else len(results)
        raise RuntimeError(f"MOD translation returned {got} results for {len(requests)} requests")
    return list(results)


async def _translate_one_by_one(translation_manager, requests: List[TranslationRequest]):
    semaphore = asyncio.Semaphore(RETRY_CONCURRENCY)

    async def one(request):
        async with semaphore:
            try:
                out = await translation_manager.translate_batch([request])
                return out[0] if out else None
            except Exception as exc:
                logger.debug("[#MOD] single retry failed: %s", exc)
                return None

    return await asyncio.gather(*(one(r) for r in requests))


def _result_text(result, token_map: Dict[str, str]) -> Tuple[str, str]:
    if result is None:
        return "", "engine_no_result"
    if not getattr(result, "success", False):
        return "", "engine_error:" + str(getattr(result, "error", "") or "failed")[:120]
    raw = getattr(result, "translated_text", "") or ""
    if not raw.strip():
        return "", "engine_empty"
    return restore_mod_text(raw, token_map), ""


# ── existing data ────────────────────────────────────────────────────────────

def _load_own_data(path: Path) -> Tuple[Optional[Dict[str, object]], bool]:
    """Return (payload, is_current_schema)."""
    payload = _read_json(path)
    if payload is None:
        return None, False
    return payload, payload.get("schema") == DATA_SCHEMA


def _load_manual(path: Path) -> Tuple[Dict[str, str], bool]:
    """Return (hand edits, legacy_file). Legacy files mirrored machine output."""
    payload = _read_json(path)
    if payload is None:
        return {}, False
    if payload.get("schema") != DATA_SCHEMA:
        return {}, True
    mapping = payload.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError(f"Manual MOD translation file must contain a JSON object named 'mapping': {path}")
    return {k: v for k, v in mapping.items() if isinstance(k, str) and isinstance(v, str)}, False


def load_interface_mod_translations(project_path: str, target_language: str) -> List[Dict[str, str]]:
    """Load generated MOD text and its optional manual edits for the in-app editor."""
    target = resolve_language(target_language)
    if target is None:
        raise ValueError(f"Unsupported MOD target language: {target_language}")
    scanner = ModProjectScanner()
    game_dir = resolve_game_dir(project_path)
    language_id = scanner.language_id(project_path, target.renpy)
    data_dir = game_dir / "tl" / language_id
    payload = _read_json(data_dir / DATA_FILE)
    if payload is None:
        return []
    mapping = payload.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError(f"MOD data does not contain a valid translation mapping: {data_dir / DATA_FILE}")
    manual, _legacy = _load_manual(data_dir / MANUAL_FILE)
    return [
        {"source": source, "target": manual.get(source, translated)}
        for source, translated in sorted(mapping.items())
        if isinstance(source, str) and isinstance(translated, str)
    ]


def save_interface_mod_corrections(
    project_path: str,
    target_language: str,
    corrections: Sequence[Dict[str, str]],
) -> int:
    """Persist only edits made in the MOD editor; machine data remains optional."""
    target = resolve_language(target_language)
    if target is None:
        raise ValueError(f"Unsupported MOD target language: {target_language}")
    scanner = ModProjectScanner()
    game_dir = resolve_game_dir(project_path)
    language_id = scanner.language_id(project_path, target.renpy)
    data_dir = game_dir / "tl" / language_id
    data_path = data_dir / DATA_FILE
    payload = _read_json(data_path)
    if payload is None:
        raise FileNotFoundError("Generate the interface MOD before saving manual corrections.")
    mapping = payload.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError(f"MOD data does not contain a valid translation mapping: {data_path}")

    manual_path = data_dir / MANUAL_FILE
    manual, legacy = _load_manual(manual_path)
    if legacy:
        manual = {}
    for row in corrections:
        source = row.get("source")
        translated = row.get("target")
        if not isinstance(source, str) or source not in mapping:
            raise ValueError("A correction refers to text that is not in the generated MOD.")
        if not isinstance(translated, str):
            raise ValueError("Manual corrections must be text.")
        if not translated.strip() or translated == mapping[source]:
            manual.pop(source, None)
        else:
            manual[source] = translated

    _write_json_atomic(manual_path, {
        "schema": DATA_SCHEMA,
        "help": "Managed by LinguaNova's MOD editor. These corrections take priority on regeneration.",
        "mapping": manual,
    })
    return len(manual)


# ── publishing ───────────────────────────────────────────────────────────────

def _publish(files: Dict[Path, str], backup_root: Path) -> List[str]:
    """Stage every file, back up the previous versions and replace them together.

    On failure every replaced file is restored from its backup and new files are
    removed, so the game never keeps a half-written MOD.
    """
    staged: Dict[Path, Path] = {}
    try:
        for target, content in files.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
            staged[target] = Path(temp_name)
        backups: Dict[Path, Path] = {}
        existing = [t for t in files if t.exists()]
        if existing:
            backup_root.mkdir(parents=True, exist_ok=True)
            for target in existing:
                # ".bak" suffix: Ren'Py never loads a backup as script.
                backup = backup_root / (target.parent.name + "__" + target.name + ".bak")
                shutil.copy2(target, backup)
                backups[target] = backup
        replaced: List[Path] = []
        try:
            for target, temp in staged.items():
                os.replace(temp, target)
                replaced.append(target)
        except Exception:
            for target in replaced:
                if target in backups:
                    shutil.copy2(backups[target], target)
                else:
                    target.unlink(missing_ok=True)
            raise
        return [str(p) for p in backups.values()]
    finally:
        for temp in staged.values():
            if temp.exists():
                temp.unlink()


def _discover_other_languages(game_dir: Path, current_folder: str) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    tl_root = game_dir / "tl"
    if not tl_root.is_dir():
        return out
    for folder in sorted(p for p in tl_root.iterdir() if p.is_dir()):
        if folder.name.casefold() == current_folder.casefold():
            continue
        data = folder / DATA_FILE
        if data.is_file():
            out[folder.name] = data
    return out


def _game_tl_languages(game_dir: Path, mod_languages) -> List[str]:
    """tl/ folders the game itself ships (not MOD languages): fonts are reset for them."""
    from src.core.language_menu_template import RESOURCE_FOLDERS
    tl_root = game_dir / "tl"
    if not tl_root.is_dir():
        return []
    taken = {lang.casefold() for lang in mod_languages}
    return sorted(path.name for path in tl_root.iterdir()
                  if path.is_dir() and path.name.casefold() not in taken
                  and path.name.casefold() not in RESOURCE_FOLDERS
                  and path.name.casefold() != "none" and not path.name.startswith("."))


def _panel_label(folder: str, language: Optional[ModLanguage]) -> str:
    """Use native names for Latin targets and Russian after Cyrillic font planning."""
    if language is None:
        return folder
    native = language.native or language.english
    if language.api == "ru" or all(char_script(c) in ("", "LATIN") for c in native):
        return native
    return language.english or folder


def _revalidate_mapping(
    mapping: Dict[str, str], target: Optional[ModLanguage], source: Optional[ModLanguage], originals: set
) -> Tuple[Dict[str, str], int]:
    kept: Dict[str, str] = {}
    dropped = 0
    for src, dst in mapping.items():
        if not isinstance(src, str) or not isinstance(dst, str) or src not in originals:
            dropped += 1
            continue
        if target is None:
            ok = validate_mod_translation(src, dst)
        else:
            ok = validate_translation(src, dst, target, source).accepted
        if ok:
            kept[src] = dst
        else:
            dropped += 1
    return kept, dropped


# ── public API ───────────────────────────────────────────────────────────────

def analyze_interface_mod(project_path: str, ui_text: Optional[UiText] = None) -> ModGenerationResult:
    report = ModProjectScanner().scan(project_path)
    originals, _contexts, excluded = _collect_candidates(report.unique_texts())
    total = len(originals)
    source_count = report.visible_rpy_files + report.decompiled_rpyc_files + report.archive_script_files
    if total <= 0:
        return ModGenerationResult(
            False, _message(ui_text, "mod_msg_no_candidates"), candidates=0, message_key="mod_msg_no_candidates",
            visible_rpy_files=report.visible_rpy_files, decompiled_rpyc_files=report.decompiled_rpyc_files,
            archive_script_files=report.archive_script_files, skipped_compiled_files=report.skipped_compiled_files,
            excluded=len(excluded),
        )
    message = _message(
        ui_text, "mod_msg_analysis", total=total, sources=source_count, excluded=len(excluded),
        rpy=report.visible_rpy_files, rpyc=report.decompiled_rpyc_files, rpa=report.archive_script_files,
        unresolved=report.skipped_compiled_files,
    )
    return ModGenerationResult(
        True, message, candidates=total, message_key="mod_msg_analysis", coverage=100.0 if report.skipped_compiled_files == 0 else 0.0,
        visible_rpy_files=report.visible_rpy_files, decompiled_rpyc_files=report.decompiled_rpyc_files,
        archive_script_files=report.archive_script_files, skipped_compiled_files=report.skipped_compiled_files,
        excluded=len(excluded),
    )


def generate_interface_mod(
    project_path: str,
    source_language: str,
    target_language: str,
    engine,
    translation_manager,
    progress: Optional[Callable[[int, int, str], None]] = None,
    source_detector: Optional[Callable[[Sequence[str]], Optional[str]]] = None,
    font_fetcher: Optional[FontFetcher] = None,
    ui_text: Optional[UiText] = None,
    allow_identity_language: bool = False,
    scan_report: Optional[ModScanReport] = None,
) -> ModGenerationResult:
    """Scan, translate, validate and publish one language of the multilang interface MOD."""
    target = resolve_language(target_language)
    if target is None:
        return ModGenerationResult(False, _message(ui_text, "mod_msg_unknown_target", language=repr(target_language)),
                                   message_key="mod_msg_unknown_target")
    requested_source = None
    if (source_language or "auto").strip().lower() != "auto":
        requested_source = resolve_language(source_language)
        if requested_source is None:
            return ModGenerationResult(
                False, _message(ui_text, "mod_msg_unknown_source", language=repr(source_language)),
                message_key="mod_msg_unknown_source")

    scanner = ModProjectScanner()
    report = scan_report if scan_report is not None else scanner.scan(project_path)
    originals, contexts, excluded = _collect_candidates(report.unique_texts())
    total = len(originals)
    base_kwargs = dict(
        visible_rpy_files=report.visible_rpy_files, decompiled_rpyc_files=report.decompiled_rpyc_files,
        archive_script_files=report.archive_script_files, skipped_compiled_files=report.skipped_compiled_files,
        excluded=len(excluded), target_language=target.renpy,
    )
    if not originals:
        return ModGenerationResult(False, _message(ui_text, "mod_msg_no_candidates"),
                                   message_key="mod_msg_no_candidates", **base_kwargs)

    game_dir = resolve_game_dir(project_path)
    language_id = scanner.language_id(project_path, target.renpy)
    data_dir = game_dir / "tl" / language_id
    data_path = data_dir / DATA_FILE
    manual_path = data_dir / MANUAL_FILE
    report_path = data_dir / REPORT_FILE
    glossary_path = data_dir / GLOSSARY_FILE
    terms, glossary_payload, glossary_changed = load_glossary(glossary_path, report.character_names)
    engine_name = str(getattr(engine, "value", engine) or "")
    original_set = set(originals)

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        source, source_method = _resolve_source_language(
            requested_source, originals, target, engine, translation_manager, loop, source_detector
        )
        identity_language = source is not None and source.api == target.api
        if identity_language and not allow_identity_language:
            return ModGenerationResult(
                False,
                _message(ui_text, "mod_msg_same_language", source=source.renpy, target=target.renpy),
                message_key="mod_msg_same_language", candidates=total, source_language=source.renpy, **base_kwargs,
            )
        api_source = source.api if source is not None else "auto"
        target_support, target_detail = engine_support(engine, target, "target")
        if target_support == "unsupported":
            return ModGenerationResult(
                False, _message(ui_text, "mod_msg_engine_unsupported", target=target.renpy, detail=target_detail),
                message_key="mod_msg_engine_unsupported", candidates=total, source_language=source.renpy if source else "auto", **base_kwargs,
            )
        engine_target = request_code(engine, target, "target")
        engine_source = request_code(engine, source, "source")
        source_support, source_detail = engine_support(engine, source, "source")
        if source_support == "unsupported":
            engine_source = "auto"   # engine detects; answers are still validated against the target
        if progress:
            progress(0, total, _message(ui_text, "mod_progress_start", source=api_source,
                                        method=source_method, target=target.api))

        entries: Dict[str, _Entry] = {}
        notes: List[str] = []
        stats = {"manual": 0, "manual_unchecked": 0, "manual_rejected": 0, "reused": 0,
                 "reuse_dropped": 0, "existing_tl": 0, "legacy_entries_not_trusted": 0,
                 "glossary": 0, "glossary_dropped": 0}

        # 1) Hand edits (structure is mandatory; language check is advisory).
        manual, legacy_manual = _load_manual(manual_path)
        for src, dst in manual.items():
            if src not in original_set:
                continue
            dst = preserve_edge_whitespace(src, dst)
            if is_junk(dst) or not validate_mod_translation(src, dst):
                stats["manual_rejected"] += 1
                continue
            verdict = validate_translation(src, dst, target, source)
            status = "accepted" if verdict.status in ("accepted", "invariant") else "manual_unchecked"
            stats["manual" if status == "accepted" else "manual_unchecked"] += 1
            entries[src] = _Entry(dst, "manual", status=status)

        # 2) MOD's own cache: only schema-2 entries for this target and source.
        own, current_schema = _load_own_data(data_path)
        legacy_mapping: Dict[str, str] = {}
        if own is not None and current_schema and own.get("api_target") == target.api:
            for src, meta in (own.get("entries") or {}).items():
                if src in entries or src not in original_set or not isinstance(meta, dict):
                    continue
                if meta.get("origin") == "manual":
                    continue  # a removed hand edit must not come back from the cache
                recorded_source = str(meta.get("source_lang") or "")
                if source is not None and recorded_source not in ("", "auto", source.api):
                    stats["reuse_dropped"] += 1
                    continue
                dst = meta.get("translation")
                if isinstance(dst, str) and not consistent(src, dst, terms):
                    stats["glossary_dropped"] += 1   # glossary changed since: translate again
                    continue
                if isinstance(dst, str) and validate_translation(src, dst, target, source).accepted:
                    entries[src] = _Entry(dst, "reused", str(meta.get("engine") or ""),
                                          recorded_source, target.api)
                    stats["reused"] += 1
                else:
                    stats["reuse_dropped"] += 1
        elif own is not None:
            legacy_mapping = own.get("mapping") if isinstance(own.get("mapping"), dict) else {}
            stats["legacy_entries_not_trusted"] = len(legacy_mapping)
            notes.append(
                "Previous MOD data had no provenance (older generator); its machine translations were "
                "backed up and retranslated instead of being reused."
            )
        if legacy_manual:
            notes.append(
                f"{MANUAL_FILE} was an old full copy of the machine output; it was backed up and replaced "
                "by an empty hand-edit file. Copy any real hand edits from the backup into the new file."
            )

        # 3) Native translations already installed for this language.
        existing_tl = scanner.existing_tl_translations(project_path, target.renpy)
        for src in originals:
            if src in entries:
                continue
            dst = existing_tl.get(src)
            if dst is None or is_junk(dst):
                continue
            dst = preserve_edge_whitespace(src, dst)
            if validate_translation(src, dst, target, source).accepted:
                entries[src] = _Entry(dst, "existing_tl", "", api_source, target.api)
                stats["existing_tl"] += 1

        # 4) Whole strings that are a glossary term (a name, a menu label...).
        glossary_same: List[str] = []
        for src in originals:
            if src in entries:
                continue
            dst = exact_term(src, terms)
            if dst is None:
                continue
            if dst == src:
                glossary_same.append(src)   # kept as is on purpose (a name)
            else:
                entries[src] = _Entry(dst, "glossary", "", api_source, target.api)
                stats["glossary"] += 1

        # 5) Machine translation of what is still missing.
        same_set = set(glossary_same)
        identity_sources = set()
        if identity_language:
            for src in originals:
                if src not in entries:
                    entries[src] = _Entry(src, "identity", engine_name, api_source, target.api, status="invariant")
                    identity_sources.add(src)
        pending = [src for src in originals if src not in entries and src not in same_set]
        verdicts: Dict[str, QualityVerdict] = {}
        failures: Dict[str, str] = {}
        done_before = len(entries)

        def build_requests(texts: Sequence[str], sl: str):
            maps, reqs = [], []
            for text in texts:
                protected, token_map = protect_mod_text(text)
                protected, term_map = protect_terms(protected, terms)
                maps.append((token_map, term_map))
                reqs.append(TranslationRequest(
                    text=protected, source_lang=sl, target_lang=engine_target, engine=engine,
                    metadata={"text_type": "interface_mod", "mod": True},
                ))
            return reqs, maps

        def judge(src: str, result, maps_pair, used_source: str) -> bool:
            token_map, term_map = maps_pair
            text, error = _result_text(result, token_map)
            if not error and term_map:
                text = restore_terms(text, term_map)
                if leaked_term_tokens(text):
                    error = "glossary_token_lost"
            if error:
                failures[src] = error
                return False
            text = preserve_edge_whitespace(src, text)
            verdict = validate_translation(src, text, target, source)
            verdicts[src] = verdict
            if verdict.accepted:
                failures.pop(src, None)
                entries[src] = _Entry(text, "machine", engine_name, used_source, target.api)
                return True
            failures[src] = f"{verdict.status}:{verdict.reason}" + (f"({verdict.detected})" if verdict.detected else "")
            return False

        with _bypass(translation_manager):
            retry: List[str] = []
            for start in range(0, len(pending), TRANSLATION_CHUNK):
                chunk = pending[start:start + TRANSLATION_CHUNK]
                reqs, maps = build_requests(chunk, engine_source)
                results = None
                for attempt in range(len(CHUNK_RETRY_DELAYS) + 1):
                    try:
                        results = _run(loop, _translate_requests(translation_manager, reqs))
                        break
                    except Exception as exc:
                        if attempt >= len(CHUNK_RETRY_DELAYS):
                            logger.warning("[#MOD] translation chunk failed after %d attempts: %s",
                                           attempt + 1, exc)
                            break
                        delay = CHUNK_RETRY_DELAYS[attempt]
                        logger.warning("[#MOD] translation chunk failed (%s); retrying in %.0fs", exc, delay)
                        time.sleep(delay)
                if results is None:
                    results = [None] * len(chunk)
                for src, res, token_map in zip(chunk, results, maps):
                    if not judge(src, res, token_map, api_source):
                        retry.append(src)
                if progress:
                    progress(done_before + start + len(chunk), total,
                             _message(ui_text, "mod_progress_chunk", done=min(start + len(chunk), len(pending)),
                                      total=len(pending), target=target.api))
            # Second opinion, one string per request and per-string source detection:
            # catches strings written in another language than the bulk of the game.
            retry = [s for s in retry if not str(failures.get(s, "")).startswith("invariant")]
            if retry:
                if progress:
                    progress(len(entries), total, _message(ui_text, "mod_progress_retry", count=len(retry)))
                reqs, maps = build_requests(retry, "auto")
                results = _run(loop, _translate_one_by_one(translation_manager, reqs))
                for src, res, token_map in zip(retry, results, maps):
                    judge(src, res, token_map, "auto")
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()
        asyncio.set_event_loop(None)

    identity_sources.update(src for src, entry in entries.items() if entry.origin == "identity")
    invariant = sorted(identity_sources | {
        s for s in originals if s not in entries and (
            s in same_set or (verdicts.get(s) and verdicts[s].status == "invariant")
        )
    })
    invariant_set = set(invariant)
    pending_final = {s: failures.get(s, "not_translated") for s in originals
                     if s not in entries and s not in invariant_set}
    mapping = {src: e.translation for src, e in entries.items()}
    translated_count = sum(1 for entry in entries.values() if entry.origin != "identity")
    coverage = translated_count / total * 100.0
    if progress:
        # Last progress line = final result. Before, the monitor kept showing
        # "MOD: retrying N rejected strings individually" after the run ended.
        progress(total, total, _message(ui_text, "mod_progress_done", translated=translated_count,
                                        unchanged=len(invariant), pending=len(pending_final), total=total))
    if not mapping and not identity_language:
        return ModGenerationResult(
            False,
            _message(ui_text, "mod_msg_all_rejected", pending=len(pending_final)),
            message_key="mod_msg_all_rejected",
            candidates=total, rejected=len(pending_final), pending=len(pending_final),
            source_language=source.renpy if source else "auto", **base_kwargs,
        )

    target_contexts = {src: contexts.get(src, []) for src in mapping}

    # Fonts: only game fonts that cannot draw this language are replaced.
    try:
        font_plan, font_info = plan_fonts(game_dir, report.font_files, target, mapping.values(), font_fetcher)
    except Exception as exc:  # never lose the translation because of a font problem
        logger.warning("[#MOD] font plan failed: %s", exc)
        font_plan, font_info = {}, {"status": "error", "error": str(exc)}
    if font_info.get("status") == "missing":
        notes.append(
            f"No font able to draw every {target.renpy} character could be obtained; some letters may "
            "show as squares. Put a suitable .ttf in game/linguanova_mod_fonts/ and generate again."
        )
    language_stats = [translated_count, total, len(pending_final)]
    data_payload = {
        "schema": DATA_SCHEMA, "hook_format": MOD_HOOK_FORMAT, "validation": VALIDATION_VERSION,
        "language": language_id, "api_target": target.api,
        "api_source": api_source, "source_detection": source_method, "engine": engine_name,
        "mapping": mapping, "contexts": target_contexts,
        "fonts": font_plan, "stats": language_stats,
        "entries": {src: e.to_json() for src, e in sorted(entries.items())},
    }

    # Other languages: keep current-schema data; re-check legacy data before embedding.
    languages: Dict[str, Dict[str, object]] = {language_id: {"mapping": mapping, "contexts": target_contexts}}
    aliases: Dict[str, List[str]] = {language_id: folder_aliases(target.renpy)}
    labels: Dict[str, str] = {language_id: _panel_label(language_id, target)}
    panel_stats: Dict[str, List[int]] = {language_id: language_stats}
    fonts_by_language: Dict[str, Dict[str, str]] = {language_id: font_plan}
    rtl_languages: List[str] = [language_id] if target.rtl else []
    files: Dict[Path, str] = {}
    other_report: Dict[str, Dict[str, object]] = {}
    for folder, path in _discover_other_languages(game_dir, language_id).items():
        try:
            payload, current = _load_own_data(path)
        except (ValueError, OSError) as exc:
            other_report[folder] = {"status": "unreadable", "error": str(exc)}
            continue
        if payload is None:
            continue
        other_lang = resolve_language(payload.get("api_target") or folder)
        omap = payload.get("mapping") if isinstance(payload.get("mapping"), dict) else {}
        octx = payload.get("contexts") if isinstance(payload.get("contexts"), dict) else {}
        if current:
            languages[folder] = {"mapping": omap, "contexts": octx}
            other_report[folder] = {"status": "kept", "entries": len(omap)}
        else:
            kept, dropped = _revalidate_mapping(omap, other_lang, source, original_set)
            languages[folder] = {"mapping": kept, "contexts": {k: octx.get(k, contexts.get(k, [])) for k in kept}}
            other_report[folder] = {"status": "legacy_revalidated", "kept": len(kept), "dropped": dropped}
            files[path] = _json_dumps({
                "schema": DATA_SCHEMA, "hook_format": MOD_HOOK_FORMAT, "validation": VALIDATION_VERSION,
                "language": folder, "api_target": other_lang.api if other_lang else "",
                "api_source": api_source, "source_detection": "legacy_revalidated", "engine": "",
                "mapping": kept, "contexts": languages[folder]["contexts"],
                "entries": {k: _Entry(v, "reused", "", "", other_lang.api if other_lang else "").to_json()
                            for k, v in sorted(kept.items())},
            })
        aliases[folder] = folder_aliases(other_lang.renpy) if other_lang else [folder.casefold()]
        labels[folder] = _panel_label(folder, other_lang)
        ostats = payload.get("stats")
        if current and isinstance(ostats, list) and len(ostats) == 3 and all(isinstance(n, int) for n in ostats):
            panel_stats[folder] = ostats
        else:
            panel_stats[folder] = [len(languages[folder]["mapping"]), total, 0]
        ofonts = payload.get("fonts") if current else None
        fonts_by_language[folder] = {k: v for k, v in (ofonts or {}).items()
                                     if isinstance(k, str) and isinstance(v, str)
                                     and (game_dir / v).is_file()}
        if other_lang is not None and other_lang.rtl:
            rtl_languages.append(folder)
        if folder.casefold() not in aliases[folder]:
            aliases[folder].insert(0, folder.casefold())

    game_name = _project_game_name(project_path, game_dir)
    out_path = game_dir / f"linguanova_mod_{game_name}_multilang.rpy"
    game_tl_languages = _game_tl_languages(game_dir, languages)
    hook = render_ui_mod_hook_multi(
        languages, language_id, aliases,
        header_notes=[f"Último idioma generado: {language_id} (origen {api_source} → destino {target.api}, "
                      f"motor {engine_name or '-'}), cobertura {coverage:.1f}%"],
        labels=labels, stats=panel_stats, fonts=fonts_by_language, rtl_languages=rtl_languages,
        other_languages=game_tl_languages,
        other_labels={folder: _panel_label(folder, resolve_language(folder)) for folder in game_tl_languages},
    )
    check_hook(hook)

    files[out_path] = hook
    # Publish resource protection with the MOD, including when the main
    # translator's optional language-menu integration was never used.
    from src.core.language_menu_template import RESOURCE_FILTER_FILE, render_resource_filter
    files[game_dir / RESOURCE_FILTER_FILE] = render_resource_filter()
    files[data_path] = _json_dumps(data_payload)
    if glossary_changed:
        files[glossary_path] = _json_dumps(glossary_payload)
    if legacy_manual or not manual_path.exists():
        files[manual_path] = _json_dumps({
            "schema": DATA_SCHEMA,
            "help": "Solo correcciones manuales: \"texto original\": \"traducción\". "
                    "Tienen prioridad sobre la traducción automática en la próxima generación.",
            "mapping": {},
        })

    legacy_native = find_legacy_mod_tl_files(game_dir, target.renpy)
    if legacy_native:
        notes.append(
            f"{len(legacy_native)} native file(s) from an earlier LinguaNova MOD build were found under "
            f"tl/{language_id}/ ({', '.join(legacy_native[:5])}). Ren'Py loads them directly, so their "
            "translations are still shown in game; move them out of the game folder to stop old mixed text."
        )
    reason_counts: Dict[str, int] = {}
    for reason in pending_final.values():
        key = reason.split("(", 1)[0]
        reason_counts[key] = reason_counts.get(key, 0) + 1

    # Where the pending texts live (the scanner keeps file and line of every
    # occurrence), so they can be found without reading the whole game.
    grouped = report.unique_texts()
    pending_by_file: Dict[str, List[Dict[str, object]]] = {}
    for src_text, reason in sorted(pending_final.items()):
        seen_files = set()
        for occ in grouped.get(src_text, []):
            fp = str(getattr(occ, "file_path", "") or "?")
            if fp in seen_files:
                continue
            seen_files.add(fp)
            pending_by_file.setdefault(fp, []).append({
                "line": int(getattr(occ, "line_number", 0) or 0),
                "reason": reason, "text": src_text[:200],
            })
    excluded_reason_counts: Dict[str, int] = {}
    for reason in excluded.values():
        excluded_reason_counts[reason] = excluded_reason_counts.get(reason, 0) + 1
    # Possible overflow in fixed-size boxes: long UI texts that grew a lot.
    # Fix them in linguanova_mod_manual.json with a shorter wording.
    long_expansions = []
    for src_text, dst_text in mapping.items():
        if len(src_text) >= EXPANSION_REPORT_MIN_CHARS and len(dst_text) >= len(src_text) * EXPANSION_REPORT_RATIO:
            long_expansions.append({
                "source": src_text, "translation": dst_text,
                "ratio": round(len(dst_text) / max(1, len(src_text)), 2),
                "contexts": contexts.get(src_text, []),
            })
    long_expansions.sort(key=lambda item: -item["ratio"])
    report_payload = {
        "game": game_name, "language": language_id, "api_target": target.api,
        "source_requested": (source_language or "auto"), "api_source": api_source,
        "source_detection": source_method, "engine": engine_name,
        "engine_codes": {"source": engine_source, "target": engine_target},
        "engine_support": {"target": [target_support, target_detail], "source": [source_support, source_detail]},
        "validation_version": VALIDATION_VERSION,
        "validation_level": "full" if language_identification_available() else "basic",
        "counter_definitions": {
            "candidates": "unique interface/dialogue texts found by the MOD scanner after code exclusion "
                          "(the MOD page 'Detected'); candidates = translated + invariant + pending",
            "translated": "texts with an accepted translation registered by the hook",
            "invariant": "texts that need no change (names, numbers, identical words)",
            "pending": "texts without a valid translation; they stay in the original language",
            "excluded_not_text": "code/debug strings removed BEFORE counting (not part of candidates)",
            "translation_pipeline": "the Translation page counts tl/ lines per occurrence (dialogue + strings); "
                                    "it is a different population and is not comparable with these numbers",
        },
        "candidates": total, "translated": translated_count, "coverage_percent": round(coverage, 2),
        "partial": bool(pending_final), "pending": len(pending_final), "pending_reasons": reason_counts,
        "pending_texts": pending_final, "invariant": len(invariant), "invariant_texts": invariant,
        "excluded_not_text": len(excluded), "excluded_texts": excluded,
        "excluded_reasons": dict(sorted(excluded_reason_counts.items())),
        "pending_files": len(pending_by_file), "pending_by_file": pending_by_file,
        "long_expansions": long_expansions[:300], "long_expansions_total": len(long_expansions),
        "origins": {o: sum(1 for e in entries.values() if e.origin == o)
                    for o in ("manual", "reused", "existing_tl", "glossary", "machine", "identity")},
        "manual_entries_used": stats["manual"], "manual_entries_unchecked": stats["manual_unchecked"],
        "manual_entries_rejected": stats["manual_rejected"],
        "cache_entries_dropped": stats["reuse_dropped"],
        "legacy_entries_not_trusted": stats["legacy_entries_not_trusted"],
        "machine_verdicts": summarise(verdicts.values()),
        "other_languages": other_report, "notes": notes,
        "legacy_mod_native_files": legacy_native,
        "visible_source_files": report.visible_rpy_files, "archive_source_files": report.archive_script_files,
        "compiled_scripts_read": report.decompiled_rpyc_files,
        "compiled_scripts_unreadable": report.skipped_compiled_files,
        "fonts": font_info, "font_replacements": font_plan, "rtl": bool(target.rtl),
        "glossary_file": GLOSSARY_FILE, "glossary_terms": len(terms),
        "glossary_entries_used": stats["glossary"], "glossary_cache_dropped": stats["glossary_dropped"],
        "glossary_kept_as_is": len(glossary_same),
        "character_names": sorted(report.character_names),
        "language_button": "Shift+L / botón \"Idioma / Language\"",
        "parse_errors": report.parse_errors[:50],
        "hook_file": out_path.name, "data_file": DATA_FILE, "editable_file": MANUAL_FILE,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    files[report_path] = _json_dumps(report_payload)

    backup_root = data_dir / BACKUP_DIR / time.strftime("%Y%m%d-%H%M%S")
    backups = _publish(files, backup_root)
    if backups:
        logger.info("[#MOD] previous MOD files backed up to %s", backup_root)

    message_key = "mod_msg_generated_partial" if pending_final else "mod_msg_generated"
    message = _message(
        ui_text, message_key, translated=len(mapping), total=total, coverage=f"{coverage:.1f}",
        target=target.renpy, source=api_source, method=source_method, pending=len(pending_final),
        unchanged=len(invariant), excluded=len(excluded), report=REPORT_FILE, output=out_path.name,
    )
    if legacy_native:
        message += " " + _message(ui_text, "mod_msg_legacy_warning", count=len(legacy_native), folder=language_id)
    return ModGenerationResult(
        True, message, str(out_path), total, translated_count, len(pending_final), coverage,
        report.visible_rpy_files, report.decompiled_rpyc_files, report.archive_script_files,
        report.skipped_compiled_files, pending=len(pending_final), excluded=len(excluded),
        partial=bool(pending_final), unchanged=len(invariant),
        source_language=source.renpy if source else "auto",
        target_language=target.renpy, report_path=str(report_path), message_key=message_key,
    )


def generate_interface_mod_languages(
    project_path: str,
    source_language: str,
    target_languages: Sequence[str],
    engine,
    translation_manager,
    progress: Optional[Callable[[int, int, str], None]] = None,
    source_detector: Optional[Callable[[Sequence[str]], Optional[str]]] = None,
    font_fetcher: Optional[FontFetcher] = None,
    ui_text: Optional[UiText] = None,
) -> ModGenerationResult:
    """Generate a set of MOD languages with one engine into the same runtime hook."""
    targets: List[ModLanguage] = []
    seen = set()
    for value in target_languages:
        target = resolve_language(value)
        if target is None:
            return ModGenerationResult(
                False, _message(ui_text, "mod_msg_unknown_target", language=repr(value)),
                message_key="mod_msg_unknown_target",
            )
        if target.renpy not in seen:
            targets.append(target)
            seen.add(target.renpy)
    if not targets:
        return ModGenerationResult(False, "No target languages were selected.")

    scan_report = ModProjectScanner().scan(project_path)
    results: List[ModGenerationResult] = []
    for index, target in enumerate(targets, 1):
        def report_progress(current: int, total: int, message: str, language=target, position=index):
            if progress:
                progress(current, total, f"{language.native} ({position}/{len(targets)}): {message}")

        results.append(generate_interface_mod(
            project_path=project_path,
            source_language=source_language,
            target_language=target.renpy,
            engine=engine,
            translation_manager=translation_manager,
            progress=report_progress,
            source_detector=source_detector,
            font_fetcher=font_fetcher,
            ui_text=ui_text,
            allow_identity_language=True,
            scan_report=scan_report,
        ))

    completed = [result for result in results if result.success and result.output_path]
    output_path = completed[-1].output_path if completed else ""
    candidates = sum(result.candidates for result in results)
    translated = sum(result.translated for result in results)
    pending = sum(result.pending for result in results)
    unchanged = sum(result.unchanged for result in results)
    coverage = translated / candidates * 100.0 if candidates else 0.0
    failed = [
        f"{target.native}: {result.message}"
        for target, result in zip(targets, results)
        if not result.success
    ]
    if completed:
        names = ", ".join(target.native for target, result in zip(targets, results) if result.success)
        message = (
            f"Generated MOD languages {len(completed)}/{len(targets)}: {names}. "
            f"All generated languages share {Path(output_path).name}."
        )
        if failed:
            message += " Failed: " + " | ".join(failed)
    else:
        message = "No MOD language was generated. " + " | ".join(failed)

    return ModGenerationResult(
        success=bool(completed),
        message=message,
        output_path=output_path,
        candidates=candidates,
        translated=translated,
        rejected=pending,
        coverage=coverage,
        visible_rpy_files=sum(result.visible_rpy_files for result in results),
        decompiled_rpyc_files=sum(result.decompiled_rpyc_files for result in results),
        archive_script_files=sum(result.archive_script_files for result in results),
        skipped_compiled_files=sum(result.skipped_compiled_files for result in results),
        pending=pending,
        excluded=sum(result.excluded for result in results),
        partial=len(completed) != len(targets) or any(result.partial for result in completed),
        unchanged=unchanged,
        source_language=source_language or "auto",
        target_language=", ".join(target.renpy for target in targets),
        report_path=completed[-1].report_path if completed else "",
        languages_generated=len(completed),
        languages_total=len(targets),
    )
