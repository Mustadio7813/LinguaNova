# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Saving-stage functions extracted from TranslationPipeline.
Includes strings.json generation, runtime hook management, variant synthesis,
coverage warnings, and translation report writing.
"""

import os
import re
import json
import time
import logging
from typing import List, Dict, Optional, Tuple, Any, Set, Callable
from pathlib import Path

from .constants import (
    RENPY_TO_API_LANG, HOTKEY_SOURCE_RE, HOTKEY_VISIBLE_RE,
    ANGLE_WRAPPED_SINGLE_RE, VISIBLE_TEXT_APOSTROPHES, VISIBLE_TEXT_DASHES,
    VISIBLE_TEXT_SENTENCE_RE, VISIBLE_TEXT_BRIDGE_PREFIXES,
    TRANSLATION_ID_KEY_RE, COVERAGE_WARNING_UI_KEYS, is_rtl_language,
)
from .translating import classify_translation_corruption, normalize_outer_color_wrapper
from .validating import is_runtime_hook_enabled as _is_runtime_hook_enabled

logger = logging.getLogger(__name__)

RENPY_DISPLAY_TAG_RE = re.compile(
    r'\{/?(?:b|i|u|s|plain|color|font|size|cps|nw|fast|w|p|a|'
    r'outlinecolor|alpha|k|rt|rb|image|space|vspace)(?:=[^}]*)?\}'
)


def synthesize_hotkey_visible_variants(mapping: Dict[str, str]) -> Dict[str, str]:
    additions: Dict[str, str] = {}
    for original, translated in mapping.items():
        match = HOTKEY_SOURCE_RE.match((original or '').strip())
        if not match:
            continue
        label = match.group('label').strip()
        hotkey = match.group('hotkey').upper()
        visible_key = f"{label} [{hotkey}]"
        translated_stripped = (translated or '').strip()
        translated_label = translated_stripped

        translated_hotkey_match = HOTKEY_SOURCE_RE.match(translated_stripped)
        if translated_hotkey_match:
            translated_label = translated_hotkey_match.group('label').strip()
        else:
            visible_match = HOTKEY_VISIBLE_RE.match(translated_stripped)
            if visible_match and visible_match.group('hotkey').upper() == hotkey:
                translated_label = visible_match.group('label').strip()

        visible_value = f"{translated_label} [{hotkey}]"
        if (
            visible_key
            and visible_value
            and visible_key != visible_value
            and visible_key not in mapping
            and visible_key not in additions
        ):
            additions[visible_key] = visible_value
    return additions


def _unwrap_single_angle_text(text: str) -> Optional[str]:
    stripped = (text or '').strip()
    if not stripped:
        return None
    match = ANGLE_WRAPPED_SINGLE_RE.match(stripped)
    if match:
        return match.group('label').strip() or None
    if stripped.startswith('<') and stripped.endswith('>') and '|' not in stripped:
        return stripped[1:-1].strip() or None
    if stripped.startswith('<') and '|' not in stripped:
        return stripped[1:].strip() or None
    if stripped.endswith('>') and '|' not in stripped:
        return stripped[:-1].strip() or None
    return None


def synthesize_angle_wrapper_variants(mapping: Dict[str, str]) -> Dict[str, str]:
    additions: Dict[str, str] = {}
    for original, translated in mapping.items():
        inner_original = _unwrap_single_angle_text(original)
        if not inner_original:
            continue
        translated_stripped = (translated or '').strip()
        inner_translated = _unwrap_single_angle_text(translated_stripped) or translated_stripped
        inner_translated = inner_translated.strip()
        if (
            not inner_translated
            or inner_original == inner_translated
            or inner_original in mapping
            or inner_original in additions
        ):
            continue
        additions[inner_original] = inner_translated
    return additions


def generate_visible_text_aliases(text: str) -> List[str]:
    stripped = (text or '').strip()
    if not stripped:
        return []
    variants: set[str] = set()
    if any(ch in stripped for ch in VISIBLE_TEXT_APOSTROPHES):
        for apostrophe in VISIBLE_TEXT_APOSTROPHES:
            candidate = stripped
            for current in VISIBLE_TEXT_APOSTROPHES:
                candidate = candidate.replace(current, apostrophe)
            if candidate != stripped:
                variants.add(candidate)
    if "..." in stripped:
        variants.add(stripped.replace("...", "\u2026"))
    if "\u2026" in stripped:
        variants.add(stripped.replace("\u2026", "..."))
    for dash in VISIBLE_TEXT_DASHES:
        if dash in stripped:
            for replacement in VISIBLE_TEXT_DASHES:
                if replacement != dash:
                    variants.add(stripped.replace(dash, replacement))
    normalized_space = re.sub(r"\s+", " ", stripped.replace("\u00a0", " ")).strip()
    if normalized_space != stripped:
        variants.add(normalized_space)
    return sorted(v for v in variants if v and v != stripped)


def synthesize_visible_text_variants(mapping: Dict[str, str]) -> Dict[str, str]:
    additions: Dict[str, str] = {}
    blocked: set[str] = set()
    for original, translated in mapping.items():
        translated_stripped = (translated or '').strip()
        if not translated_stripped:
            continue
        for alias in generate_visible_text_aliases(original):
            if alias in blocked:
                continue
            if alias in mapping:
                blocked.add(alias)
                additions.pop(alias, None)
                continue
            existing = additions.get(alias)
            if existing is not None and existing != translated_stripped:
                blocked.add(alias)
                additions.pop(alias, None)
                continue
            additions[alias] = translated_stripped
    return additions


def _split_visible_sentences(text: str) -> List[str]:
    stripped = (text or '').strip()
    if not stripped:
        return []
    parts = [match.group(0).strip() for match in VISIBLE_TEXT_SENTENCE_RE.finditer(stripped)]
    return [part for part in parts if part]


def _build_bridge_prefixed_variant(text: str, prefix: str) -> Optional[str]:
    stripped = (text or '').strip()
    if not stripped:
        return None
    if stripped.lower().startswith(prefix.lower() + ' '):
        return None
    if stripped[0].isalpha():
        stripped = stripped[0].lower() + stripped[1:]
    return f"{prefix} {stripped}"


def synthesize_visible_fragment_variants(mapping: Dict[str, str], is_aggressive: bool = False) -> Dict[str, str]:
    additions: Dict[str, str] = {}
    blocked: set[str] = set()
    min_source_length = 64 if is_aggressive else 80
    min_source_sentences = 2 if is_aggressive else 3
    min_target_sentences = 1 if is_aggressive else 2
    max_count_limit = 3 if is_aggressive else 2
    min_fragment_length = 36 if is_aggressive else 48
    min_fragment_words = 5 if is_aggressive else 7

    for original, translated in mapping.items():
        source = (original or '').strip()
        target = (translated or '').strip()
        if not source or not target:
            continue
        if len(source) < min_source_length:
            continue
        if any(token in source for token in ('[', ']', '{', '}')):
            continue

        source_sentences = _split_visible_sentences(source)
        target_sentences = _split_visible_sentences(target)
        if len(source_sentences) < min_source_sentences or len(target_sentences) < min_target_sentences:
            continue

        max_count = min(max_count_limit, len(source_sentences) - 1, len(target_sentences))
        for count in range(1, max_count + 1):
            source_fragment = ' '.join(source_sentences[:count]).strip()
            target_fragment = ' '.join(target_sentences[:count]).strip()
            if len(source_fragment) < min_fragment_length or source_fragment.count(' ') < min_fragment_words:
                continue

            candidate_keys = [source_fragment]
            for prefix in VISIBLE_TEXT_BRIDGE_PREFIXES:
                prefixed = _build_bridge_prefixed_variant(source_fragment, prefix)
                if prefixed:
                    candidate_keys.append(prefixed)

            for candidate in candidate_keys:
                if candidate in blocked:
                    continue
                if candidate in mapping:
                    blocked.add(candidate)
                    additions.pop(candidate, None)
                    continue
                existing = additions.get(candidate)
                if existing is not None and existing != target_fragment:
                    blocked.add(candidate)
                    additions.pop(candidate, None)
                    continue
                additions[candidate] = target_fragment

    return additions


def _normalize_runtime_alias_text(text: str) -> str:
    normalized = (text or '').strip()
    if not normalized:
        return ''
    for current in VISIBLE_TEXT_APOSTROPHES:
        normalized = normalized.replace(current, "'")
    normalized = normalized.replace('\u2026', '...')
    normalized = normalized.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
    normalized = re.sub(r'\s+', ' ', normalized.replace('\u00a0', ' ')).strip()
    return normalized.casefold()


def _find_runtime_alias_match_index(container_text: str, source_text: str) -> int:
    lowered_container = container_text.casefold()
    lowered_source = source_text.casefold()
    start = lowered_container.find(lowered_source)
    if start < 0:
        return -1
    end = start + len(source_text)
    before = container_text[start - 1] if start > 0 else ''
    after = container_text[end] if end < len(container_text) else ''
    if before and before.isalnum():
        return -1
    if after and after.isalnum():
        return -1
    return start


def _build_runtime_observed_alias(observed_text: str, source_text: str, translated_text: str) -> Optional[str]:
    observed = (observed_text or '').strip()
    source = (source_text or '').strip()
    translated = (translated_text or '').strip()
    if not observed or not source or not translated:
        return None
    if _normalize_runtime_alias_text(observed) == _normalize_runtime_alias_text(source):
        return translated
    start = _find_runtime_alias_match_index(observed, source)
    if start < 0:
        return None
    end = start + len(source)
    return observed[:start] + translated + observed[end:]


def get_diagnostics_dir(lang_dir: str, target_language: Optional[str] = None) -> str:
    """
    Returns the isolated diagnostics directory path outside tl/<lang>/.
    Ren'Py ignores directories starting with a dot ('.').
    Structure: <tl_parent_or_tl>/.diagnostics/<lang>/
    """
    lang_path = Path(lang_dir)
    lang_name = target_language or lang_path.name
    if lang_path.parent.name == 'tl':
        base_dir = lang_path.parent
    elif lang_path.name == 'tl':
        base_dir = lang_path
    else:
        base_dir = lang_path
    diag_dir = os.path.join(str(base_dir), '.diagnostics', lang_name)
    os.makedirs(diag_dir, exist_ok=True)
    return diag_dir


def synthesize_runtime_observed_variants(mapping: Dict[str, str], lang_dir: str, is_aggressive: bool = False) -> Dict[str, str]:
    diag_dir = get_diagnostics_dir(lang_dir)
    log_path = Path(diag_dir) / 'runtime_missed_strings.jsonl'
    if not log_path.is_file():
        legacy_path = Path(lang_dir) / 'diagnostics' / 'runtime_missed_strings.jsonl'
        if legacy_path.is_file():
            log_path = legacy_path
        else:
            return {}

    analysis = analyze_runtime_miss_log(str(log_path))
    additions: Dict[str, str] = {}
    blocked: set[str] = set()
    accepted_actions = {'promote_alias', 'review_candidate'} if is_aggressive else {'promote_alias'}
    min_source_length = 24 if is_aggressive else 32
    min_source_words = 3 if is_aggressive else 4
    normalized_mapping = {
        _normalize_runtime_alias_text(source): (source, target)
        for source, target in mapping.items()
        if source and target
    }

    eligible_sources: List[Tuple[str, str]] = [
        (s_clean, t_clean)
        for source_text, translated_text in mapping.items()
        if (s_clean := (source_text or '').strip())
        and (t_clean := (translated_text or '').strip())
        and len(s_clean) >= min_source_length
        and s_clean.count(' ') >= min_source_words
        and not any(token in s_clean for token in ('[', ']', '{', '}'))
    ]

    for candidate in analysis.get('top_candidates', []):
        if candidate.get('suggested_action') not in accepted_actions:
            continue
        observed_text = (candidate.get('text') or '').strip()
        if not observed_text or observed_text in mapping or observed_text in blocked:
            continue

        matched_pairs: list[tuple[str, str]] = []
        normalized_observed = _normalize_runtime_alias_text(observed_text)
        exact_pair = normalized_mapping.get(normalized_observed)
        if exact_pair is not None:
            matched_pairs.append(exact_pair)
        else:
            for source_clean, translated_clean in eligible_sources:
                if _find_runtime_alias_match_index(observed_text, source_clean) >= 0:
                    matched_pairs.append((source_clean, translated_clean))
                if len(matched_pairs) > 1:
                    break

        if len(matched_pairs) != 1:
            if len(matched_pairs) > 1:
                blocked.add(observed_text)
                additions.pop(observed_text, None)
            continue

        source_text, translated_text = matched_pairs[0]
        alias_value = _build_runtime_observed_alias(observed_text, source_text, translated_text)
        if not alias_value or alias_value == observed_text:
            continue

        existing = additions.get(observed_text)
        if existing is not None and existing != alias_value:
            blocked.add(observed_text)
            additions.pop(observed_text, None)
            continue
        additions[observed_text] = alias_value

    return additions


def analyze_runtime_miss_log(log_path: str) -> Dict[str, Any]:
    from src.core.runtime_coverage import load_runtime_miss_log, score_runtime_miss_entries, summarize_runtime_miss_scores
    entries = load_runtime_miss_log(log_path)
    scored = score_runtime_miss_entries(entries)
    summary = summarize_runtime_miss_scores(entries)
    return {
        'summary': summary,
        'top_candidates': [
            {
                'text': item.text,
                'score': item.score,
                'confidence': item.confidence,
                'suggested_action': item.suggested_action,
                'risk': item.risk,
                'reasons': item.reasons,
                'entry': item.entry,
            }
            for item in scored[:50]
        ],
    }


def write_translation_reports(lang_dir: str, target_language: str, diagnostic_report,
                                translation_guard_counts, translation_guard_events,
                                translation_guard_sample_limit, log_emit, config) -> Optional[str]:
    from src.utils.encoding import save_text_safely

    diag_dir = get_diagnostics_dir(lang_dir, target_language)
    diag_path = os.path.join(diag_dir, f'diagnostic_{target_language}.json')
    diagnostic_report.write(diag_path)
    log_emit('info', config.get_log_text('log_diagnostic_written', path=diag_path))

    report_path = os.path.join(diag_dir, 'translation_blocked_or_fallback.json')
    payload = {
        'generated_at': int(time.time()),
        'counts': dict(translation_guard_counts),
        'sample_limit': translation_guard_sample_limit,
        'samples': translation_guard_events,
    }
    from src.utils.encoding import save_json_safely
    save_json_safely(Path(report_path), payload, indent=2)

    # Clean up legacy diagnostics directory inside tl/<lang>/ if present
    legacy_diag_dir = os.path.join(lang_dir, 'diagnostics')
    if os.path.isdir(legacy_diag_dir):
        try:
            import shutil
            shutil.rmtree(legacy_diag_dir)
        except Exception:
            pass

    return diag_path


def emit_coverage_warning_summary(diagnostic_report, config, log_emit, last_diagnostic_path: Optional[str] = None) -> None:
    warnings = getattr(diagnostic_report, 'coverage_warnings', [])
    if not warnings:
        return

    for warning in warnings[:3]:
        text_key = COVERAGE_WARNING_UI_KEYS.get(warning.get('code', ''), '')
        default_text = warning.get('code', 'warning')
        localized = config.get_ui_text(text_key, default_text).format(count=warning.get('count', 0))
        log_emit('warning', f"\u26a0\ufe0f {localized}")

    if last_diagnostic_path:
        report_line = config.get_ui_text('coverage_warning_report_path', 'Diagnostics report: {path}').format(path=last_diagnostic_path)
        log_emit('warning', report_line)


def manage_runtime_hook(project_path: str, target_language: str, config, log_emit) -> None:
    """Manages the runtime translation hook script based on settings."""
    from src.core.runtime_hook_template import render_runtime_hook
    from src.utils.encoding import save_text_safely

    if not project_path:
        return

    try:
        game_dir = Path(project_path) / "game"
        if not game_dir.exists():
            return

        hook_filename = "zzz_linguanova_runtime.rpy"
        hook_path = game_dir / hook_filename

        legacy_hook_files = (
            *game_dir.glob("*_linguanova_runtime.rpy"),
            *game_dir.glob("*_linguanova_runtime.rpyc"),
        )
        for old in legacy_hook_files:
            if old.name not in {hook_filename, hook_filename + "c"}:
                old.unlink(missing_ok=True)

        should_exist = _is_runtime_hook_enabled(config)

        target_lang = target_language or getattr(config.translation_settings, 'target_language', 'turkish') or 'turkish'
        reverse_lang_map = {v.lower(): k for k, v in RENPY_TO_API_LANG.items()}
        renpy_lang = reverse_lang_map.get(target_lang.lower(), target_lang)

        use_native = getattr(config.translation_settings, 'output_mode', 'strings') == 'native'

        if use_native:
            if hook_path.exists():
                os.remove(hook_path)
            hook_pyc_rm = game_dir / (hook_filename + "c")
            if hook_pyc_rm.exists():
                try:
                    os.remove(hook_pyc_rm)
                except Exception:
                    logger.debug("Failed to remove .rpyc hook file (rm variant)")
            log_emit('info', config.get_ui_text("log_hook_removed").replace("{filename}", hook_filename))
        elif should_exist:
            content = render_runtime_hook(
                renpy_lang,
                runtime_string_diagnostics=getattr(
                    config.translation_settings,
                    "runtime_string_diagnostics",
                    False,
                ),
            )
            save_text_safely(hook_path, content, encoding="utf-8")
            hook_pyc_std = game_dir / (hook_filename + "c")
            if hook_pyc_std.exists():
                try:
                    os.remove(hook_pyc_std)
                except Exception:
                    logger.debug("Failed to remove .rpyc hook file (std variant)")
            log_emit('info', config.get_ui_text("log_hook_installed").replace("{filename}", hook_filename))
        else:
            if hook_path.exists():
                os.remove(hook_path)
            hook_pyc_rm = game_dir / (hook_filename + "c")
            if hook_pyc_rm.exists():
                try:
                    os.remove(hook_pyc_rm)
                except Exception:
                    logger.debug("Failed to remove .rpyc hook file (duplicate rm)")
            log_emit('info', config.get_ui_text("log_hook_removed").replace("{filename}", hook_filename))

    except Exception as e:
        logger.warning(f"Failed to manage runtime hook: {e}")


def remove_language_init_files(game_dir: str) -> int:
    """Delete LinguaNova's zzz_<lang>_language.rpy(.rpyc) files; returns how many."""
    from src.core.constants import is_linguanova_generated_script

    removed = 0
    for path in Path(game_dir).glob("zzz_*_language.rpy*"):
        if is_linguanova_generated_script(path.name):
            try:
                path.unlink()
                removed += 1
            except OSError:
                logger.debug("Could not remove %s", path)
    return removed


def list_tl_languages(game_dir: str) -> list:
    """Script-bearing language folders that the shared picker can activate."""
    from src.core.language_menu_template import installed_language_folders
    return installed_language_folders(game_dir)



# ---------------------------------------------------------------------------
# Native language-menu integration
# ---------------------------------------------------------------------------

LANGUAGE_MENU_FILE = "zzz_linguanova_language_menu.rpy"

_SCREEN_HEADER_RE = re.compile(
    r"^(?P<indent>[ \t]*)screen\s+(?P<name>[A-Za-z_]\w*)\b.*:\s*(?:#.*)?$"
)
_LANGUAGE_ACTION_RE = re.compile(
    r"\bLanguage\s*\(\s*(?P<arg>None|[\"'][^\"']*[\"']|[A-Za-z_]\w*)\s*\)"
)
_TEXTBUTTON_RE = re.compile(r"^(?P<indent>[ \t]*)textbutton\b")
_FOR_PAIR_RE = re.compile(
    r"^(?P<indent>[ \t]*)for\s+(?P<a>[A-Za-z_]\w*)\s*,\s*(?P<b>[A-Za-z_]\w*)"
    r"\s+in\s+(?P<var>[A-Za-z_]\w*)(?P<items>\.items\(\))?\s*:\s*(?:#.*)?$"
)


def remove_language_menu_files(game_dir: str) -> int:
    """Remove only LinguaNova's generated native-menu helper."""
    removed = 0
    root = Path(game_dir)
    for name in (LANGUAGE_MENU_FILE, LANGUAGE_MENU_FILE + "c"):
        path = root / name
        if path.exists():
            try:
                path.unlink()
                removed += 1
            except OSError:
                logger.debug("Could not remove %s", path)
    return removed


def remove_all_language_integration_files(game_dir: str) -> int:
    """Remove the new menu helper and all legacy forced-language files."""
    return remove_language_menu_files(game_dir) + remove_language_init_files(game_dir)


def _indent_width(line: str) -> int:
    prefix = line[: len(line) - len(line.lstrip(" \t"))]
    return sum(4 if ch == "\t" else 1 for ch in prefix)


def _read_rpy_text(path: Path) -> Optional[str]:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def _iter_real_rpy_sources(game_dir: str) -> List[Tuple[str, str]]:
    from src.core.constants import is_linguanova_generated_script
    root = Path(game_dir)
    records: List[Tuple[str, str]] = []
    skip_dirs = {"tl", "cache", "__pycache__", ".git"}
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in skip_dirs]
        current_path = Path(current)
        try:
            rel_parts = [p.lower() for p in current_path.relative_to(root).parts]
        except ValueError:
            rel_parts = []
        if "tl" in rel_parts:
            continue
        for name in sorted(names, key=str.lower):
            if not name.lower().endswith(".rpy"):
                continue
            if is_linguanova_generated_script(name) or name.lower() == LANGUAGE_MENU_FILE.lower():
                continue
            path = current_path / name
            text = _read_rpy_text(path)
            if text:
                records.append((str(path), text))
    return records


def _decompiled_rpy_sources(game_dir: str) -> List[Tuple[str, str]]:
    """Use LinguaNova's existing unrpyc/rpycdec stack in a temporary folder."""
    from src.core.constants import is_linguanova_generated_script
    root = Path(game_dir)
    compiled: List[Path] = []
    skip_dirs = {"tl", "cache", "__pycache__", ".git"}
    for current, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in skip_dirs]
        current_path = Path(current)
        try:
            rel_parts = [p.lower() for p in current_path.relative_to(root).parts]
        except ValueError:
            rel_parts = []
        if "tl" in rel_parts:
            continue
        for name in sorted(names, key=str.lower):
            if not name.lower().endswith((".rpyc", ".rpymc")):
                continue
            if is_linguanova_generated_script(name):
                continue
            src = current_path / name
            if not src.with_suffix(".rpy").exists():
                compiled.append(src)
    if not compiled:
        return []
    try:
        from src.utils.unrpyc_adapter import UnrpycAdapter
        adapter = UnrpycAdapter()
        if not adapter.available:
            return []
        records: List[Tuple[str, str]] = []
        with adapter.decompile_to_temp(compiled, root) as (_tmp, generated):
            for path in generated:
                text = _read_rpy_text(Path(path))
                if text:
                    records.append((f"{path} [decompiled]", text))
        return records
    except Exception as exc:
        logger.debug("Language-menu decompile scan failed: %s", exc)
        return []


def _extract_screen_blocks(source: str, *, include_without_actions: bool = False) -> List[Dict[str, Any]]:
    lines = source.splitlines(keepends=True)
    result: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines):
        m = _SCREEN_HEADER_RE.match(lines[i].rstrip("\r\n"))
        if not m or _indent_width(lines[i]) != 0:
            i += 1
            continue
        start = i
        name = m.group("name")
        i += 1
        while i < len(lines):
            if lines[i].strip() and not lines[i].lstrip().startswith("#") and _indent_width(lines[i]) == 0:
                break
            i += 1
        block = "".join(lines[start:i])
        actions = list(_LANGUAGE_ACTION_RE.finditer(block))
        if actions or include_without_actions:
            result.append({"name": name, "text": block, "actions": actions, "count": len(actions)})
    return result


def _literal_language_arg(arg: str) -> Optional[str]:
    value = (arg or "").strip()
    if value == "None":
        return None
    if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
        return value[1:-1]
    return ""


def _replace_textbutton_label(statement: str, display_name: str) -> Optional[str]:
    pattern = re.compile(
        r"(\btextbutton\s+(?:_\(\s*)?)(?P<q>[\"'])(?P<label>.*?)(?P=q)",
        re.S,
    )
    match = pattern.search(statement)
    if not match:
        return None
    quote = match.group("q")
    escaped = display_name.replace("\\", "\\\\").replace(quote, "\\" + quote)
    return statement[:match.start("label")] + escaped + statement[match.end("label"):]


def _patch_direct_language_buttons(screen_text: str, target_code: str, display_name: str) -> Optional[str]:
    """Clone one native textbutton as a sibling in the same original container."""
    lines = screen_text.splitlines(keepends=True)
    statements: List[Dict[str, Any]] = []
    for idx, line in enumerate(lines):
        if not _TEXTBUTTON_RE.match(line.rstrip("\r\n")):
            continue
        indent = _indent_width(line)
        is_block = line.rstrip().split("#", 1)[0].rstrip().endswith(":")
        end = idx + 1
        if is_block:
            while end < len(lines):
                if lines[end].strip() and not lines[end].lstrip().startswith("#") and _indent_width(lines[end]) <= indent:
                    break
                end += 1
        statement = "".join(lines[idx:end])
        literal = []
        for lm in _LANGUAGE_ACTION_RE.finditer(statement):
            parsed = _literal_language_arg(lm.group("arg"))
            if parsed != "":
                literal.append(parsed)
        if not literal:
            continue
        parent = -1
        for back in range(idx - 1, -1, -1):
            if not lines[back].strip():
                continue
            if _indent_width(lines[back]) < indent and lines[back].rstrip().split("#", 1)[0].rstrip().endswith(":"):
                parent = back
                break
        statements.append({
            "start": idx, "end": end, "indent": indent, "parent": parent,
            "text": statement, "language": literal[0],
        })

    groups: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for st in statements:
        groups.setdefault((st["parent"], st["indent"]), []).append(st)
    # A game with only its original Language(None) button is already a safe
    # native insertion point: clone that radio/textbutton as a sibling.
    viable = [group for group in groups.values() if group]
    if not viable:
        return None
    group = max(viable, key=len)
    template = next((st for st in reversed(group) if st["language"] not in (None, "")), group[-1])
    clone = template["text"]
    old_code = template["language"]
    if old_code:
        exact = re.compile(r"(?P<q>[\"'])" + re.escape(old_code) + r"(?P=q)")
        clone = exact.sub(lambda m: m.group("q") + target_code + m.group("q"), clone)

    clone = _LANGUAGE_ACTION_RE.sub(
        lambda m: f'Language("{target_code}")' if _literal_language_arg(m.group("arg")) != "" else m.group(0),
        clone,
        count=1,
    )
    if old_code is None:
        clone = re.sub(
            r"(_preferences\.language\s*)(?:is|==)\s*None\b",
            lambda match: match.group(1) + "== " + repr(target_code),
            clone,
        )
    clone = _replace_textbutton_label(clone, display_name)
    if not clone:
        return None

    insertion = max(st["end"] for st in group)
    original_line = lines[template["start"]]
    indent_text = original_line[:len(original_line) - len(original_line.lstrip(" \t"))]
    marker = f'{indent_text}# LinguaNova: {display_name} -> Language("{target_code}")\n'
    if not clone.endswith(("\n", "\r")):
        clone += "\n"
    return "".join(lines[:insertion]) + marker + clone + "".join(lines[insertion:])


def _dynamic_language_data_patch(screen_text: str, target_code: str, display_name: str) -> Optional[str]:
    """Extend simple 2-column list/tuple or dict selectors instead of replacing the screen."""
    lines = screen_text.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        m = _FOR_PAIR_RE.match(line.rstrip("\r\n"))
        if not m:
            continue
        indent = _indent_width(line)
        end = idx + 1
        while end < len(lines):
            if lines[end].strip() and not lines[end].lstrip().startswith("#") and _indent_width(lines[end]) <= indent:
                break
            end += 1
        body = "".join(lines[idx + 1:end])
        a, b, var = m.group("a"), m.group("b"), m.group("var")
        action = re.search(r"\bLanguage\s*\(\s*(" + re.escape(a) + "|" + re.escape(b) + r")\s*\)", body)
        if not action:
            continue
        code_var = action.group(1)

        if m.group("items"):
            if code_var == a:
                return (
                    'init 900 python:\n'
                    '    import builtins as _ln_menu_types\n'
                    "    # LinguaNova: extend the game's own dictionary-driven language selector.\n"
                    '    try:\n'
                    f'        _ln_menu_data = globals().get("{var}", None)\n'
                    '        if isinstance(_ln_menu_data, _ln_menu_types.dict):\n'
                    f'            if "{target_code}" not in _ln_menu_data:\n'
                    f'                _ln_menu_data["{target_code}"] = {display_name!r}\n'
                    '    except Exception:\n'
                    '        pass\n'
                )
            return (
                'init 900 python:\n'
                '    import builtins as _ln_menu_types\n'
                "    # LinguaNova: extend the game's own dictionary-driven language selector.\n"
                '    try:\n'
                f'        _ln_menu_data = globals().get("{var}", None)\n'
                '        if isinstance(_ln_menu_data, _ln_menu_types.dict):\n'
                f'            if "{target_code}" not in [str(v) for v in _ln_menu_data.values()]:\n'
                f'                _ln_menu_data[{display_name!r}] = "{target_code}"\n'
                '    except Exception:\n'
                '        pass\n'
            )

        code_index = 0 if code_var == a else 1
        label_index = 1 - code_index
        return (
            'init 900 python:\n'
            '    import builtins as _ln_menu_types\n'
            "    # LinguaNova: extend the game's own two-column list/tuple selector.\n"
            '    try:\n'
            f'        _ln_menu_data = globals().get("{var}", None)\n'
            '        if isinstance(_ln_menu_data, (_ln_menu_types.list, _ln_menu_types.tuple)):\n'
            '            _ln_exists = False\n'
            '            _ln_template = None\n'
            '            for _ln_item in _ln_menu_data:\n'
            '                if isinstance(_ln_item, (_ln_menu_types.list, _ln_menu_types.tuple)) and len(_ln_item) == 2:\n'
            '                    if _ln_template is None:\n'
            '                        _ln_template = _ln_item\n'
            '                    try:\n'
            f'                        if str(_ln_item[{code_index}]) == "{target_code}":\n'
            '                            _ln_exists = True\n'
            '                            break\n'
            '                    except Exception:\n'
            '                        pass\n'
            '            if not _ln_exists and _ln_template is not None:\n'
            '                _ln_new = list(_ln_template)\n'
            f'                _ln_new[{code_index}] = "{target_code}"\n'
            f'                _ln_new[{label_index}] = {display_name!r}\n'
            '                if isinstance(_ln_template, _ln_menu_types.tuple):\n'
            '                    _ln_new = tuple(_ln_new)\n'
            '                if isinstance(_ln_menu_data, _ln_menu_types.list):\n'
            '                    _ln_menu_data.append(_ln_new)\n'
            '                else:\n'
            f'                    globals()["{var}"] = _ln_menu_data + (_ln_new,)\n'
            '    except Exception:\n'
            '        pass\n'
        )
    return None


def _screen_priority(name: str) -> int:
    lowered = (name or "").lower()
    score = 0
    for needle, weight in (
        ("language", 60), ("lang", 45), ("preferences", 40),
        ("settings", 35), ("options", 30), ("config", 20),
    ):
        if needle in lowered:
            score += weight
    return score


def _analyze_language_menu_sources(records: List[Tuple[str, str]], target_code: str, display_name: str) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for source_path, source in records:
        for screen in _extract_screen_blocks(source):
            # Some games already enumerate renpy.known_languages() and have a
            # single literal button for Original. Their own loop lists every
            # new TL automatically; cloning Original would duplicate choices.
            if (re.search(r"\brenpy\.known_languages\s*\(", screen["text"])
                    and any(_literal_language_arg(action.group("arg")) == ""
                            for action in screen["actions"])):
                return {"status": "already_present", "screen": screen["name"],
                        "source": source_path, "method": "known_languages"}
            # A data-driven selector ("for label, code in languages:" with ONE
            # Language(code) action) has a single action in the screen text;
            # requiring two skipped it and the game was reported as having no
            # selector (pre-existing test failure, fixed 2026-10-18).
            existing = []
            for action in screen["actions"]:
                parsed = _literal_language_arg(action.group("arg"))
                if parsed not in ("", None):
                    existing.append(parsed)
            if any(code.lower() == target_code.lower() for code in existing):
                return {"status": "already_present", "screen": screen["name"], "source": source_path, "method": "existing"}

            patched = _patch_direct_language_buttons(screen["text"], target_code, display_name)
            dynamic = None if patched else _dynamic_language_data_patch(screen["text"], target_code, display_name)
            if patched or dynamic:
                candidates.append({
                    "status": "candidate",
                    "screen": screen["name"],
                    "source": source_path,
                    "method": "screen_override" if patched else "data_extension",
                    "payload": patched or dynamic,
                    "score": screen["count"] * 10 + _screen_priority(screen["name"]),
                })
    return max(candidates, key=lambda item: item["score"]) if candidates else {"status": "not_found"}


def _resolve_language_folder(game_dir: str, target_language: str, config, lang_map=None, exact: bool = False) -> str:
    lang_map_val = lang_map if lang_map is not None else RENPY_TO_API_LANG
    value = (target_language or "").strip()
    if not value:
        try:
            value = str(config.translation_settings.target_language or "")
        except Exception:
            value = ""
    if not exact and value:
        reverse_map = {v.lower(): k for k, v in lang_map_val.items()}
        value = reverse_map.get(value.lower(), value)
    tl_root = Path(game_dir) / "tl"
    if tl_root.is_dir() and value:
        actual = next((p.name for p in tl_root.iterdir() if p.is_dir() and p.name.lower() == value.lower()), None)
        if actual:
            return actual
    return value


def _native_language_name(config, target_code: str) -> str:
    try:
        for item in config.get_all_languages():
            if (
                str(item.get("renpy", "")).lower() == target_code.lower()
                or str(item.get("api", "")).lower() == target_code.lower()
            ):
                return str(item.get("native") or item.get("english") or target_code)
    except Exception:
        pass
    return target_code.replace("_", " ").replace("-", " ").title()


def _fallback_language_picker(target_code: str, display_name: str, labels: Dict[str, str]) -> str:
    """Compatibility entry point for the shared, scrollable in-game picker."""
    from src.core.language_menu_template import render_language_picker
    return render_language_picker(labels)


def _tl_language_labels(game_dir: str, config, target_code: str, display_name: str) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for code in list_tl_languages(game_dir):
        labels[code] = _native_language_name(config, code)
    labels[target_code] = display_name
    return labels


def _multilingual_native_menu(records, labels):
    """Extend immutable game sources for ALL installed languages in one helper.

    Each successive clone is applied to the in-memory source. Generating a
    second target therefore retains the first target without reading a generated
    screen as if it belonged to the developer. Original .rpy files stay intact.
    """
    working = list(records)
    screens = {}
    data_extensions = []
    integrated = []
    for code, name in sorted(labels.items()):
        result = _analyze_language_menu_sources(working, code, name)
        if result.get("status") == "already_present":
            integrated.append(code)
        elif result.get("status") == "candidate":
            if result["method"] == "data_extension":
                data_extensions.append(result["payload"])
                integrated.append(code)
                continue
            for index, (source_path, source) in enumerate(working):
                if source_path != result["source"]:
                    continue
                screen = next((item for item in _extract_screen_blocks(source)
                               if item["name"] == result["screen"]), None)
                if screen is None:
                    break
                working[index] = (source_path, source.replace(screen["text"], result["payload"], 1))
                screens[(source_path, result["screen"])] = result["payload"]
                integrated.append(code)
                break
    if not integrated:
        # Standard games often have no language control at all. Their normal
        # Preferences content is an identifiable insertion point, so add the
        # radio group there instead of placing a separate menu over the game.
        for source_path, source in records:
            inserted = _preferences_language_section(source)
            if inserted is not None:
                screen_name, payload = inserted
                screens[(source_path, screen_name)] = payload
                integrated = list(labels)
                break
    parts = []
    if screens:
        parts.append("init offset = 900\n\n" + "\n\n".join(screens.values()) + "\ninit offset = 0\n")
    parts.extend(data_extensions)
    return "\n\n".join(parts), integrated


def _preferences_language_section(source):
    """Add the chooser to a recognisable native Preferences content container.

    Prefer the row of native radio/check columns used by Ren'Py's standard GUI.
    Otherwise use a content vbox inside game_menu/viewport. Custom layouts that
    cannot be identified still get the working Shift+L fallback.
    """
    for screen in _extract_screen_blocks(source, include_without_actions=True):
        if screen["name"].lower() not in {"preferences", "settings", "options"}:
            continue
        if screen["actions"]:
            continue
        lines = screen["text"].splitlines(keepends=True)
        candidates = []
        for index, line in enumerate(lines):
            match = re.match(r"^([ \t]*)(hbox|vbox)\s*:\s*(?:#.*)?$", line.rstrip("\r\n"))
            if not match:
                continue
            indent = _indent_width(line)
            end = index + 1
            while end < len(lines) and (not lines[end].strip() or lines[end].lstrip().startswith("#") or _indent_width(lines[end]) > indent):
                end += 1
            body = "".join(lines[index + 1:end])
            radio_row = match.group(2) == "hbox" and re.search(
                r'style_prefix\s+[\"\'](?:radio|check)[\"\']', body
            )
            content_vbox = match.group(2) == "vbox" and re.search(
                r"\buse\s+game_menu\b|\bviewport\s*:", screen["text"][:sum(map(len, lines[:index]))]
            )
            if radio_row or content_vbox:
                score = (1000 if radio_row else 100) - indent
                candidates.append((score, index, end, match.group(1)))
        if not candidates:
            continue
        _score, index, end, indent_text = max(candidates)
        addition = indent_text + '    use lntl_language_preferences\n'
        before = "".join(lines[:end])
        if not before.endswith("\n"):
            before += "\n"
        return screen["name"], before + addition + "".join(lines[end:])
    return None


def create_language_menu_integration(
    game_dir: str,
    target_language: str,
    config,
    log_emit,
    lang_map=None,
    exact_language_folder: bool = False,
) -> Dict[str, Any]:
    """Publish one persistent, hot-switchable selector for every installed TL."""
    from src.utils.encoding import save_text_safely
    from src.core.language_menu_template import install_resource_filter, render_language_picker

    root = Path(game_dir)
    target_code = _resolve_language_folder(
        game_dir, target_language, config, lang_map, exact=exact_language_folder
    ).strip()
    if not target_code or not target_code.isidentifier() or target_code.casefold() == "none":
        return {"status": "invalid_language"}

    tl_dir = root / "tl" / target_code
    if not tl_dir.is_dir():
        return {"status": "missing_tl", "language": target_code}

    try:
        resource_filter = install_resource_filter(game_dir)
    except Exception as exc:
        log_emit("error", config.get_ui_text(
            "pipeline_lang_menu_failed", "Could not create the language selector: {error}"
        ).replace("{error}", str(exc)))
        return {"status": "error", "error": str(exc)}

    display_name = _native_language_name(config, target_code)
    labels = _tl_language_labels(game_dir, config, target_code, display_name)
    records = _iter_real_rpy_sources(game_dir)
    if _analyze_language_menu_sources(records, target_code, display_name).get("status") == "not_found":
        records += _decompiled_rpy_sources(game_dir)

    native_payload, native_languages = _multilingual_native_menu(records, labels)
    native_complete = all(code in native_languages for code in labels)
    status = "integrated" if native_payload else (
        "already_present" if native_complete else "fallback_picker"
    )
    helper = root / LANGUAGE_MENU_FILE
    header = (
        "# SPDX-License-Identifier: GPL-3.0-or-later\n"
        "# LinguaNova - Shared multilingual language selector\n"
        "# Generated helper; original game scripts are preserved.\n"
        "# Shift+L opens the chooser during gameplay and in menus.\n"
        "# Original uses Ren'Py's Language(None); nothing is forced at startup.\n"
        "# Languages: " + ", ".join(sorted(labels)) + "\n\n"
    )
    content = header + native_payload + "\n\n" + render_language_picker(labels, show_button=not native_complete)
    # Keep the working selector until its replacement is safely on disk.
    # save_text_safely returns False for Windows locks; it need not raise.
    try:
        changed = _read_rpy_text(helper) != content
        if changed and not save_text_safely(helper, content, encoding="utf-8-sig", newline="\n"):
            raise OSError("Could not write the language selector: " + str(helper))
        if not helper.is_file() or _read_rpy_text(helper) != content:
            raise OSError("Language selector verification failed: " + str(helper))
        if changed:
            Path(str(helper) + "c").unlink(missing_ok=True)
    except Exception as exc:
        log_emit("error", config.get_ui_text(
            "pipeline_lang_menu_failed",
            "Could not create the language selector: {error}"
        ).replace("{error}", str(exc)))
        return {"status": "error", "error": str(exc), "output": str(helper)}

    if status == "fallback_picker":
        key, default = "pipeline_lang_menu_fallback", (
            "A shared language selector was created. Use Shift+L during gameplay; "
            "the Language button is available in the game's menus."
        )
    elif status == "already_present":
        key, default = "pipeline_lang_menu_existing", (
            "The installed languages are already in the game's selector. "
            "Shift+L also opens the shared chooser during gameplay."
        )
    else:
        key, default = "pipeline_lang_menu_integrated", (
            "The game's language selector now includes all installed translations. "
            "Shift+L opens the shared chooser during gameplay."
        )
    log_emit("info", config.get_ui_text(key, default).replace("{lang}", display_name).replace("{screen}", ""))
    log_emit("info", config.get_ui_text(
        "pipeline_lang_menu_saved",
        "Language selector verified: {path} | installed languages: {count} | Shift+L"
    ).replace("{path}", str(helper)).replace("{count}", str(len(labels))))
    return {
        "status": status, "language": target_code, "display_name": display_name,
        "output": str(helper), "languages": sorted(labels),
        "resource_filter": str(resource_filter),
        "native_languages": native_languages, "hotkey": "Shift+L", "changed": changed,
    }


def create_language_init_file(
    game_dir: str,
    target_language: str,
    config,
    log_emit,
    lang_map=None,
    force: bool = False,
) -> Dict[str, Any]:
    """Compatibility wrapper: old forcing removed, native-menu integration only."""
    removed_legacy = remove_language_init_files(game_dir)
    ts = getattr(config, "translation_settings", None)
    enabled = True if force else (
        ts is None or getattr(ts, "activate_language_on_launch", True)
    )
    if not enabled:
        # Resource protection is required even when adding a menu is disabled.
        # It never changes font files or the game's own language preference.
        from src.core.language_menu_template import install_resource_filter
        try:
            resource_filter = install_resource_filter(game_dir)
        except Exception as exc:
            log_emit("error", config.get_ui_text(
                "pipeline_lang_menu_failed", "Could not create the language selector: {error}"
            ).replace("{error}", str(exc)))
            return {"status": "error", "error": str(exc)}
        removed_menu = remove_language_menu_files(game_dir)
        if removed_legacy or removed_menu:
            log_emit("info", config.get_ui_text(
                "log_language_init_removed",
                "Language-menu integration is disabled; LinguaNova helper files were removed from game/."
            ))
        return {"status": "disabled", "resource_filter": str(resource_filter)}

    return create_language_menu_integration(
        game_dir, target_language, config, log_emit,
        lang_map=lang_map, exact_language_folder=force,
    )

def write_atomic_segments_rpy(tl_dir: str, renpy_lang: str) -> None:
    """DEPRECATED (v2.7.1 hotfix) — Bu metod artık çağrılmıyor."""
    logger.debug("_write_atomic_segments_rpy is deprecated, skipping")
    return


def _extract_raw_mapping(
    tl_files: List[Any],
    extra_translations: Optional[Dict[str, str]] = None,
    logger_obj: Optional[logging.Logger] = None,
) -> Tuple[Dict[str, str], int, Dict[str, int], List[Dict[str, Any]]]:
    """Extracts raw mappings from tl_files and extra_translations, filtering corruptions."""
    mapping: Dict[str, str] = {}
    skipped_corrupt = 0
    skipped_reason_counts = {
        'separator_remnant': 0, 'placeholder_remnant': 0, 'html_leakage': 0,
        'length_inflation': 0, 'placeholder_set_mismatch': 0,
        'renpy_tag_set_mismatch': 0, 'renpy_tag_order_invalid': 0, 'replacement_char': 0,
        'printf_set_mismatch': 0, 'duplicate_key_conflict': 0,
        'case_insensitive_conflict': 0,
    }
    skipped_samples: List[Dict[str, Any]] = []
    mapping_sources: Dict[str, List[dict]] = {}
    active_logger = logger_obj or logger

    def _mark_skipped(reason: str, original: str, translated: str) -> None:
        nonlocal skipped_corrupt
        skipped_corrupt += 1
        if reason in skipped_reason_counts:
            skipped_reason_counts[reason] += 1
        if len(skipped_samples) < 200:
            sample: Dict[str, Any] = {'reason': reason, 'original': original, 'translated': translated}
            if reason == 'duplicate_key_conflict' and original in mapping:
                sample['existing_translation'] = mapping[original]
                sample['sources'] = mapping_sources.get(original, [])
            skipped_samples.append(sample)

    def _try_add(original: str, translated: str, source_file: Optional[str] = None, line_num: Optional[int] = None) -> None:
        orig = (original or '').strip()
        trans = (translated or '').strip()
        if not orig or not trans or orig == trans or TRANSLATION_ID_KEY_RE.fullmatch(orig):
            return
        trans = normalize_outer_color_wrapper(orig, trans)
        if orig == trans:
            return
        reason = classify_translation_corruption(orig, trans)
        if reason is not None:
            _mark_skipped(reason, orig, trans)
            active_logger.debug("strings.json: Skipping %s in translation of: %s", reason, orig[:40])
            return
        if orig in mapping:
            if mapping[orig] != trans:
                _mark_skipped('duplicate_key_conflict', orig, trans)
                active_logger.debug("strings.json: Duplicate key conflict: %s", orig[:40])
            return
        mapping[orig] = trans
        if source_file and len(skipped_samples) < 200:
            mapping_sources.setdefault(orig, []).append({'file': source_file, 'line': line_num})

    for tfile in tl_files:
        s_file = os.path.basename(tfile.file_path) if getattr(tfile, 'file_path', None) else None
        for entry in getattr(tfile, 'entries', []):
            if entry.original_text and entry.translated_text:
                _try_add(entry.original_text, entry.translated_text, s_file, getattr(entry, 'line_number', None))

    if extra_translations:
        for orig, trans in extra_translations.items():
            _try_add(orig, trans)

    return mapping, skipped_corrupt, skipped_reason_counts, skipped_samples


def _expand_delimiter_segments(mapping: Dict[str, str], logger_obj: Optional[logging.Logger] = None) -> None:
    """Splits <A|B|C> and bare pipe delimiter groups into individual segments."""
    try:
        from src.core.syntax_guard import split_angle_pipe_groups, split_delimited_text
        _seg_additions: Dict[str, str] = {}
        _seg_count = 0
        active_logger = logger_obj or logger

        for m_orig, m_trans in mapping.items():
            orig_split = split_angle_pipe_groups(m_orig)
            if orig_split is not None:
                trans_split = split_angle_pipe_groups(m_trans)
                if trans_split is not None:
                    _, orig_groups = orig_split
                    _, trans_groups = trans_split
                    for g_idx in range(min(len(orig_groups), len(trans_groups))):
                        o_segs = orig_groups[g_idx]
                        t_segs = trans_groups[g_idx]
                        for s_idx in range(min(len(o_segs), len(t_segs))):
                            o_s = o_segs[s_idx].strip()
                            t_s = t_segs[s_idx].strip()
                            if o_s and t_s and o_s != t_s and o_s not in mapping and o_s not in _seg_additions:
                                _seg_additions[o_s] = t_s
                                _seg_count += 1
                continue
            if '|' not in m_orig:
                continue
            orig_delim = split_delimited_text(m_orig)
            if orig_delim is None:
                if '|' in m_orig and '|' in m_trans:
                    o_parts = m_orig.split('|')
                    t_parts = m_trans.split('|')
                    if 2 <= len(o_parts) == len(t_parts) <= 6:
                        if all(sum(1 for ch in _p.strip() if ch.isalpha()) >= 2 for _p in o_parts):
                            for o_s, t_s in zip(o_parts, t_parts):
                                o_s, t_s = o_s.strip(), t_s.strip()
                                if o_s and t_s and o_s != t_s and o_s not in mapping and o_s not in _seg_additions:
                                    _seg_additions[o_s] = t_s
                                    _seg_count += 1
                continue
            o_segs, _, _, _ = orig_delim
            trans_delim = split_delimited_text(m_trans)
            t_segs = trans_delim[0] if trans_delim is not None else (m_trans.split('|') if '|' in m_trans else [])
            for s_idx in range(min(len(o_segs), len(t_segs))):
                o_s = o_segs[s_idx].strip()
                t_s = t_segs[s_idx].strip()
                if o_s and t_s and o_s != t_s and o_s not in mapping and o_s not in _seg_additions:
                    _seg_additions[o_s] = t_s
                    _seg_count += 1
        if _seg_additions:
            mapping.update(_seg_additions)
            active_logger.info(f"strings.json: {_seg_count} individual segments extracted from delimiter groups")
    except Exception as e:
        (logger_obj or logger).debug(f"strings.json segment splitting skipped: {e}")


def _expand_tag_stripped_variants(mapping: Dict[str, str], logger_obj: Optional[logging.Logger] = None) -> None:
    """Strips Ren'Py display tags to provide plain-text fallback entries for replace_text."""
    try:
        active_logger = logger_obj or logger
        _tag_stripped_additions: Dict[str, str] = {}
        _tag_strip_count = 0
        for m_orig, m_trans in mapping.items():
            if not RENPY_DISPLAY_TAG_RE.search(m_orig):
                continue
            stripped_orig = RENPY_DISPLAY_TAG_RE.sub('', m_orig).strip()
            stripped_trans = RENPY_DISPLAY_TAG_RE.sub('', m_trans).strip()
            if (stripped_orig and stripped_trans and stripped_orig != stripped_trans
                    and len(stripped_orig) >= 2 and any(c.isalpha() for c in stripped_orig)
                    and stripped_orig not in mapping
                    and stripped_orig not in _tag_stripped_additions):
                _tag_stripped_additions[stripped_orig] = stripped_trans
                _tag_strip_count += 1
        if _tag_stripped_additions:
            mapping.update(_tag_stripped_additions)
            active_logger.info(f"strings.json: {_tag_strip_count} tag-stripped entries added for replace_text coverage")
    except Exception as e:
        (logger_obj or logger).debug(f"strings.json tag-stripping skipped: {e}")


def _expand_synthesized_variants(
    mapping: Dict[str, str],
    is_aggressive: bool = False,
    record_guard_event: Optional[Callable[..., None]] = None,
    diagnostic_report: Optional[Any] = None,
    logger_obj: Optional[logging.Logger] = None,
) -> None:
    """Synthesizes visible text, hotkey, angle-bracket, and fragment variants for runtime coverage."""
    active_logger = logger_obj or logger
    synthesis_pipeline = [
        (synthesize_hotkey_visible_variants, 'visible_hotkey_variant'),
        (synthesize_angle_wrapper_variants, 'angle_wrapper_variant'),
        (synthesize_visible_text_variants, 'visible_text_variant'),
        (lambda m: synthesize_visible_fragment_variants(m, is_aggressive), 'visible_fragment_variant'),
    ]
    for synth_fn, detail_name in synthesis_pipeline:
        try:
            additions = synth_fn(mapping)
            if additions:
                for key, value in additions.items():
                    if key in mapping:
                        continue
                    mapping[key] = value
                    if record_guard_event:
                        record_guard_event(
                            category='recovered_by_synthesized_variant',
                            file_path='strings.json', translation_id=key,
                            original_text=key, translated_text=value,
                            detail=detail_name,
                        )
                    if diagnostic_report and hasattr(diagnostic_report, 'mark_recovered'):
                        try:
                            diagnostic_report.mark_recovered(
                                'strings.json', key, 'synthesized_variant',
                                original_text=key, translated_text=value,
                            )
                        except Exception:
                            active_logger.debug("diagnostic mark_written failed for key=%s", key)
                if diagnostic_report and hasattr(diagnostic_report, 'record_alias_kind'):
                    diagnostic_report.record_alias_kind(detail_name, len(additions))
                active_logger.info(f"strings.json: {len(additions)} {detail_name} synthesized for runtime coverage")
        except Exception as e:
            active_logger.debug(f"strings.json {detail_name} synthesis skipped: {e}")


def _expand_runtime_observed_variants(
    mapping: Dict[str, str],
    lang_dir: str,
    is_aggressive: bool = False,
    record_guard_event: Optional[Callable[..., None]] = None,
    diagnostic_report: Optional[Any] = None,
    logger_obj: Optional[logging.Logger] = None,
) -> None:
    """Synthesizes aliases from runtime missed string logs."""
    active_logger = logger_obj or logger
    try:
        runtime_observed_additions = synthesize_runtime_observed_variants(mapping, lang_dir, is_aggressive)
        if runtime_observed_additions:
            for key, value in runtime_observed_additions.items():
                if key in mapping:
                    continue
                mapping[key] = value
                if record_guard_event:
                    record_guard_event(
                        category='recovered_by_synthesized_variant',
                        file_path='strings.json', translation_id=key,
                        original_text=key, translated_text=value,
                        detail='runtime_observed_variant',
                    )
                if diagnostic_report and hasattr(diagnostic_report, 'mark_recovered'):
                    try:
                        diagnostic_report.mark_recovered(
                            'strings.json', key, 'synthesized_variant',
                            original_text=key, translated_text=value,
                        )
                    except Exception:
                        active_logger.debug("diagnostic mark_written failed for key=%s", key)
            if diagnostic_report and hasattr(diagnostic_report, 'record_alias_kind'):
                diagnostic_report.record_alias_kind('runtime_observed_variant', len(runtime_observed_additions))
            active_logger.info(f"strings.json: {len(runtime_observed_additions)} runtime-observed aliases synthesized from missed-string diagnostics")
    except Exception as e:
        active_logger.debug(f"strings.json runtime-observed synthesis skipped: {e}")


def _write_skipped_corruption_report(
    lang_dir: str,
    skipped_corrupt: int,
    skipped_reason_counts: Dict[str, int],
    skipped_samples: List[Dict[str, Any]],
    logger_obj: Optional[logging.Logger] = None,
) -> None:
    """Writes diagnostic report for skipped corruptions if any occurred."""
    active_logger = logger_obj or logger
    if skipped_corrupt <= 0:
        return
    active_logger.warning(f"strings.json: Skipped {skipped_corrupt} potentially corrupted translation(s)")
    reason_summary = ', '.join(f"{name}={count}" for name, count in skipped_reason_counts.items() if count > 0)
    if reason_summary:
        active_logger.info(f"strings.json: Corruption reasons -> {reason_summary}")
    try:
        from src.utils.encoding import save_text_safely
        diag_dir = get_diagnostics_dir(lang_dir)
        report_path = os.path.join(diag_dir, 'strings_json_skipped_corruptions.json')
        payload = {
            'generated_at': int(time.time()),
            'total_skipped': skipped_corrupt,
            'reason_counts': skipped_reason_counts,
            'sample_limit': 100,
            'samples': skipped_samples,
        }
        from src.utils.encoding import save_json_safely
        save_json_safely(Path(report_path), payload, indent=2)
        active_logger.info(f"strings.json: Wrote skipped-corruption report -> {report_path}")
    except Exception as report_exc:
        active_logger.debug(f"strings.json: Failed to write skipped-corruption report: {report_exc}")


def _save_strings_json(
    mapping: Dict[str, str],
    lang_dir: str,
    log_emit: Optional[Callable[[str, str], None]] = None,
    config: Optional[Any] = None,
) -> int:
    """Saves the final strings.json file with static and dynamic entries."""
    from src.utils.encoding import save_json_safely
    dynamic_entries: Dict[str, str] = {}
    try:
        from src.core.exporter import _has_dynamic_variables
        dynamic_entries = {k: v for k, v in mapping.items() if _has_dynamic_variables(k)}
    except Exception:
        dynamic_entries = {}
    payload = {"translations": mapping, "dynamic": dynamic_entries}
    json_path = os.path.join(lang_dir, "strings.json")
    save_json_safely(Path(json_path), payload, indent=2)
    if log_emit and config and hasattr(config, 'get_log_text'):
        dyn_msg = f" ({len(dynamic_entries)} dynamic)" if dynamic_entries else ""
        log_msg = config.get_log_text('log_strings_json_generated', count=len(mapping)) + dyn_msg
        log_emit('info', log_msg)
    return len(mapping)


def generate_strings_json(
    tl_files: List[Any],
    lang_dir: str,
    extra_translations: Optional[Dict[str, str]] = None,
    *,
    is_aggressive: bool = False,
    record_guard_event: Optional[Callable[..., None]] = None,
    diagnostic_report: Optional[Any] = None,
    log_emit: Optional[Callable[[str, str], None]] = None,
    config: Optional[Any] = None,
    logger_override: Optional[logging.Logger] = None,
) -> Optional[int]:
    """Coordinates the generation, synthesis, and saving of strings.json."""
    active_logger = logger_override or logger
    ts = getattr(config, 'translation_settings', None) if config else None
    output_mode = getattr(ts, 'output_mode', 'strings') if ts else 'strings'
    if output_mode == 'native':
        # Native TLID mode generates native .rpy translation blocks and deletes the runtime hook.
        # strings.json is completely unneeded by Ren'Py and causes severe lag on Ren'Py 7.
        # Clean up any stale strings.json from lang_dir to keep tl/<lang> clean.
        stale_json = os.path.join(lang_dir, "strings.json")
        if os.path.exists(stale_json):
            try:
                os.remove(stale_json)
                if log_emit and config and hasattr(config, 'get_log_text'):
                    log_emit('info', config.get_log_text('log_stale_strings_json_removed', 'Removed unneeded strings.json for Native TLID mode'))
            except Exception as ex:
                active_logger.debug(f"Failed to remove stale strings.json: {ex}")
        return 0

    try:
        mapping, skipped_corrupt, skipped_counts, skipped_samples = _extract_raw_mapping(
            tl_files, extra_translations, active_logger
        )
        _expand_delimiter_segments(mapping, active_logger)
        _expand_tag_stripped_variants(mapping, active_logger)
        _expand_synthesized_variants(mapping, is_aggressive, record_guard_event, diagnostic_report, active_logger)
        _expand_runtime_observed_variants(mapping, lang_dir, is_aggressive, record_guard_event, diagnostic_report, active_logger)
        _write_skipped_corruption_report(lang_dir, skipped_corrupt, skipped_counts, skipped_samples, active_logger)
        if mapping:
            return _save_strings_json(mapping, lang_dir, log_emit, config)
        return 0
    except Exception as e:
        active_logger.warning(f"Failed to generate strings.json: {e}")
        return None
