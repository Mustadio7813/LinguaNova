# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — independent project scanner. Original game files are read-only.
from __future__ import annotations

import ast
import io
import logging
import os
import pickle
from pathlib import Path
import re
import tempfile
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .parser import ModInterfaceParser, ModTextCandidate
from .protect import is_junk

logger = logging.getLogger("LinguaNova")

_SKIP_DIRS = {"tl", "cache", "saves", "__pycache__"}
_SKIP_PREFIXES = ("linguanova_mod_", "trampa_", "zz_linguanova_", "zzz_linguanova_")
_TL_BLOCK_RE = re.compile(r"^\s*translate\s+(?P<language>[\w-]+)\s+strings\s*:\s*(?:#.*)?$", re.I)
_TL_ENTRY_RE = re.compile(r"^\s*(?P<kind>old|new)\s+(?P<literal>.+?)\s*(?:#.*)?$")
_SAFE_RPA_GLOBALS = {
    ("builtins", "dict"): dict, ("builtins", "list"): list,
    ("builtins", "tuple"): tuple, ("builtins", "set"): set,
    ("builtins", "frozenset"): frozenset, ("builtins", "str"): str,
    ("builtins", "bytes"): bytes, ("builtins", "bytearray"): bytearray,
    ("builtins", "int"): int, ("builtins", "float"): float,
    ("builtins", "bool"): bool,
    ("__builtin__", "dict"): dict, ("__builtin__", "list"): list,
    ("__builtin__", "tuple"): tuple, ("__builtin__", "str"): str,
    ("__builtin__", "unicode"): str, ("__builtin__", "bytes"): bytes,
    ("__builtin__", "int"): int, ("__builtin__", "long"): int,
    ("__builtin__", "float"): float, ("__builtin__", "bool"): bool,
}


class _SafeRpaUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        try:
            return _SAFE_RPA_GLOBALS[(module, name)]
        except KeyError as exc:
            raise pickle.UnpicklingError(f"disallowed RPA global: {module}.{name}") from exc


def _safe_rpa_loads(data: bytes):
    return _SafeRpaUnpickler(io.BytesIO(data)).load()


def _xor_rpa_index(data: bytes, key: int) -> bytes:
    try:
        from src.utils.rpa_parser import _archive_index_xor
    except ImportError:
        return data
    return _archive_index_xor(data, key)


def _read_rpa_index(file_obj, header: bytes) -> Tuple[Dict, int]:
    parts = header.decode("utf-8", errors="replace").strip().split()
    if len(parts) < 2:
        raise ValueError("unknown RPA header")
    offset = int(parts[1], 16)
    key = int(parts[2], 16) if len(parts) >= 3 else 0
    file_obj.seek(offset)
    raw = file_obj.read()
    attempts = [_xor_rpa_index(raw, key), raw] if key else [raw]
    for blob in attempts:
        for candidate in (zlib.decompress, lambda value: value):
            try:
                return _safe_rpa_loads(candidate(blob)), key
            except (ValueError, EOFError, pickle.UnpicklingError, zlib.error):
                continue
    raise ValueError("RPA index could not be decoded")


def read_script_members(rpa_path: Path) -> List[Tuple[str, bytes]]:
    """Read source script members only (.rpy/.rpym)."""
    return read_archive_members(rpa_path, (".rpy", ".rpym"))


_COMPILED_SUFFIXES = (".rpyc", ".rpymc")
_FONT_SUFFIXES = (".ttf", ".otf", ".ttc")


def read_archive_members(rpa_path: Path, suffixes: Tuple[str, ...], keep_case: bool = False) -> List[Tuple[str, bytes]]:
    """Read the members of an RPA archive whose names end with ``suffixes`` (read-only, in memory).

    ``keep_case`` keeps the member's real spelling (font paths must match what the game references).
    """
    out: List[Tuple[str, bytes]] = []
    with rpa_path.open("rb") as file_obj:
        index, key = _read_rpa_index(file_obj, file_obj.readline())
        for raw_name, chunks in index.items():
            name = raw_name.decode("utf-8", errors="replace") if isinstance(raw_name, bytes) else str(raw_name)
            normalized = name.replace("\\", "/") if keep_case else name.lower().replace("\\", "/")
            if not normalized.lower().endswith(suffixes) or not chunks:
                continue
            parts: List[bytes] = []
            for chunk in chunks:
                if len(chunk) < 2:
                    continue
                offset, length = int(chunk[0]) ^ key, int(chunk[1]) ^ key
                prefix = chunk[2] if len(chunk) > 2 else b""
                if isinstance(prefix, str):
                    prefix = prefix.encode("latin-1", errors="replace")
                file_obj.seek(offset)
                parts.append(prefix + file_obj.read(max(0, length - len(prefix))))
            if parts:
                out.append((normalized.lstrip("/"), b"".join(parts)))
    return out


@dataclass
class ModScanReport:
    candidates: List[ModTextCandidate] = field(default_factory=list)
    visible_rpy_files: int = 0
    decompiled_rpyc_files: int = 0
    archive_script_files: int = 0
    skipped_compiled_files: int = 0
    archives_scanned: int = 0
    parse_errors: List[str] = field(default_factory=list)
    # Fonts the game ships (visible or inside .rpa): name -> bytes. Used to
    # check whether the game's own fonts can draw the target language.
    font_files: Dict[str, bytes] = field(default_factory=dict)
    character_names: Set[str] = field(default_factory=set)

    def unique_texts(self) -> Dict[str, List[ModTextCandidate]]:
        out: Dict[str, List[ModTextCandidate]] = {}
        for candidate in self.candidates:
            out.setdefault(candidate.text, []).append(candidate)
        return out

    @property
    def unique_count(self) -> int:
        return len(self.unique_texts())


def resolve_game_dir(project_path: str) -> Path:
    p = Path(project_path).expanduser().resolve()
    if p.is_file():
        root = p.parent
    else:
        root = p
    if root.name.lower() == "game":
        return root
    for name in ("game", "Game"):
        candidate = root / name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Ren'Py game/ directory not found under: {root}")


def _iter_visible(root: Path, suffixes: Tuple[str, ...]) -> List[Path]:
    result: List[Path] = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in _SKIP_DIRS and not d.startswith(".")]
        for name in names:
            low = name.lower()
            if low.startswith(_SKIP_PREFIXES):
                continue
            if low.endswith(suffixes):
                result.append(Path(base) / name)
    return sorted(result)


def _decode_source(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def _language_names(language: str) -> Set[str]:
    """Folder names (casefolded) that hold ``language`` under game/tl/.

    Uses the central catalogue (all 135 languages); the former 10-entry table
    left every other language without aliases.
    """
    from .languages import folder_aliases

    code = (language or "").strip().lower().replace("-", "_")
    if not code:
        return set()
    names = {name.casefold() for name in folder_aliases(language)}
    names.add(code)
    return names


def read_existing_tl_translations(game_dir: Path, language: str) -> Dict[str, str]:
    """Read valid old/new string pairs recursively from the selected Ren'Py TL tree."""
    tl_root = game_dir / "tl"
    names = _language_names(language)
    if not tl_root.is_dir() or not names:
        return {}
    language_dirs = sorted(
        (path for path in tl_root.iterdir() if path.is_dir() and path.name.casefold() in names),
        key=lambda path: path.name.casefold(),
    )
    translations: Dict[str, str] = {}
    for language_dir in language_dirs:
        files = sorted((*language_dir.rglob("*.rpy"), *language_dir.rglob("*.rpym")))
        for path in files:
            if path.name.lower().startswith(_SKIP_PREFIXES):
                # Output of an earlier LinguaNova MOD build: not an independent
                # translation, so it must not be reused as "existing" (2026-10-17).
                continue
            try:
                lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            except OSError as exc:
                raise OSError(f"Could not read existing MOD TL file {path}: {exc}") from exc
            in_strings = False
            old_text: Optional[str] = None
            block_indent = -1
            for line in lines:
                block = _TL_BLOCK_RE.match(line)
                if block:
                    in_strings = block.group("language").casefold() in names
                    block_indent = len(line) - len(line.lstrip())
                    old_text = None
                    continue
                if not in_strings:
                    continue
                indent = len(line) - len(line.lstrip())
                if line.strip() and not line.lstrip().startswith("#") and indent <= block_indent:
                    in_strings = False
                    old_text = None
                    continue
                entry = _TL_ENTRY_RE.match(line)
                if not entry:
                    continue
                try:
                    value = ast.literal_eval(entry.group("literal"))
                except (SyntaxError, ValueError):
                    old_text = None
                    continue
                if not isinstance(value, str) or is_junk(value):
                    old_text = None
                    continue
                if entry.group("kind") == "old":
                    old_text = value
                elif old_text is not None:
                    translations.setdefault(old_text, value)
                    old_text = None
    # Dialogue translations ("# who \"orig\"" / "who \"translation\""): the MOD
    # reused only "translate strings" pairs, so a line the Translation flow had
    # already translated was sent to the engine again and could end up
    # pending in the MOD while the game showed the native translation (audit
    # case 04, 2026-10-18). Strings keep priority; every reused pair is still
    # validated by the caller.
    try:
        from src.core.tl_parser import TLParser
        parser = TLParser()
        for language_dir in language_dirs:
            for path in sorted(language_dir.rglob("*.rpy")):
                if path.name.lower().startswith(_SKIP_PREFIXES):
                    continue
                parsed = parser.parse_file(str(path))
                if parsed is None:
                    continue
                for item in parsed.entries:
                    if item.entry_type not in ("dialogue", "narrator"):
                        continue
                    src_text, dst_text = item.original_text, item.translated_text
                    if (src_text and dst_text and dst_text.strip()
                            and dst_text.strip() != src_text.strip() and not is_junk(dst_text)):
                        translations.setdefault(src_text, dst_text)
    except Exception as exc:  # never block MOD generation on an unreadable tl file
        logger.warning("[#MOD] dialogue translations in tl/ could not be read: %s", exc)
    return translations


def find_legacy_mod_tl_files(game_dir: Path, language: str) -> List[str]:
    """Script files under game/tl/<language>/ written by earlier LinguaNova MOD builds.

    Ren'Py loads them natively, so contaminated translations inside them keep
    showing in game even after the MOD is regenerated; they are reported so the
    user can move them out. MOD never edits or deletes them itself.
    """
    tl_root = game_dir / "tl"
    names = _language_names(language)
    if not tl_root.is_dir() or not names:
        return []
    found: List[str] = []
    for language_dir in sorted(p for p in tl_root.iterdir() if p.is_dir() and p.name.casefold() in names):
        for path in sorted((*language_dir.rglob("*.rpy"), *language_dir.rglob("*.rpym"))):
            if path.name.lower().startswith(_SKIP_PREFIXES):
                found.append(path.relative_to(game_dir).as_posix())
    return found


def resolve_tl_language_id(game_dir: Path, language: str) -> str:
    """Return the existing Ren'Py language directory or a safe target identifier."""
    tl_root = game_dir / "tl"
    names = _language_names(language)
    if tl_root.is_dir():
        preferred = (language or "").strip().casefold()
        matches = sorted(
            (path for path in tl_root.iterdir() if path.is_dir() and path.name.casefold() in names),
            # The folder spelled like the requested Ren'Py id wins over API-code folders.
            key=lambda path: (path.name.casefold() != preferred, path.name.casefold()),
        )
        if matches:
            # Keep the real spelling: Ren'Py language ids are case-sensitive.
            return matches[0].name
    identifier = re.sub(r"[^A-Za-z0-9_-]+", "_", (language or "").strip()).strip("_").lower()
    if not identifier:
        raise ValueError("A valid Ren'Py target language is required for MOD data output")
    return identifier


_CHARACTER_RE = re.compile(r"""Character\(\s*(?:_\(\s*)?(?P<q>['"])(?P<name>[^'"\[\]{}]{1,40})(?P=q)""")


def _character_names_in(text: str) -> Set[str]:
    """Literal speaker names from ``Character("Name", ...)`` (kept untranslated by MOD)."""
    return {m.group("name").strip() for m in _CHARACTER_RE.finditer(text or "") if m.group("name").strip()}


def _strings_in(obj, depth: int = 0, limit: List[int] = None):
    """Yield every str attribute reachable from an unpickled AST node (bounded)."""
    limit = limit if limit is not None else [20000]
    if depth > 12 or limit[0] <= 0:
        return
    limit[0] -= 1
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _strings_in(value, depth + 1, limit)
    elif isinstance(obj, (list, tuple, set)):
        for value in obj:
            yield from _strings_in(value, depth + 1, limit)
    elif hasattr(obj, "__dict__"):
        yield from _strings_in(vars(obj), depth + 1, limit)


class ModProjectScanner:
    def __init__(self) -> None:
        self.parser = ModInterfaceParser()

    def _read_compiled(self, orphans, report: "ModScanReport") -> None:
        try:
            from src.core.rpyc_reader import ASTTextExtractor, read_rpyc_file
        except Exception as exc:  # reader unavailable in this build
            report.skipped_compiled_files += len(orphans)
            report.parse_errors.append(f"RPYC reader unavailable: {exc}")
            return
        with tempfile.TemporaryDirectory(prefix="linguanova_mod_rpyc_") as tmp:
            for index, (rel, data, kind) in enumerate(orphans):
                if kind.startswith("rpyc:"):
                    path = Path(kind[5:])
                    kind = "rpyc"
                else:
                    path = Path(tmp) / f"{index}{Path(rel).suffix}"
                    path.write_bytes(data)
                try:
                    extracted = ASTTextExtractor(None).extract_from_file(path)
                    nodes = read_rpyc_file(path)
                except Exception as exc:
                    report.skipped_compiled_files += 1
                    report.parse_errors.append(f"{rel}: {exc}")
                    continue
                if not extracted and not nodes:
                    report.skipped_compiled_files += 1
                    report.parse_errors.append(f"{rel}: no readable AST")
                    continue
                report.decompiled_rpyc_files += 1
                for item in extracted:
                    text = getattr(item, "text", "")
                    if not isinstance(text, str) or not text.strip():
                        continue
                    report.candidates.append(ModTextCandidate(
                        text, rel, int(getattr(item, "line_number", 0) or 0), "__global_ui__", kind,
                        "high", "rpyc:" + str(getattr(item, "text_type", "") or "text"),
                    ))
                for value in _strings_in(nodes):
                    if "Character(" in value:
                        report.character_names.update(_character_names_in(value))

    def existing_tl_translations(self, project_path: str, language: str) -> Dict[str, str]:
        return read_existing_tl_translations(resolve_game_dir(project_path), language)

    def language_id(self, project_path: str, language: str) -> str:
        return resolve_tl_language_id(resolve_game_dir(project_path), language)

    def scan(self, project_path: str) -> ModScanReport:
        game_dir = resolve_game_dir(project_path)
        report = ModScanReport()
        logical_sources: Dict[str, Tuple[str, str, str]] = {}

        # 1) Visible .rpy/.rpym always win.
        for path in _iter_visible(game_dir, (".rpy", ".rpym")):
            try:
                rel = path.relative_to(game_dir).as_posix()
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                logical_sources[rel.lower()] = (rel, text, "rpy")
                report.visible_rpy_files += 1
            except Exception as exc:
                report.parse_errors.append(f"{path}: {exc}")

        # 2) RPA archives are inspected read-only, in memory. Source members fill
        #    missing sources; compiled members are kept for step 3.
        compiled: Dict[str, Tuple[str, bytes, str]] = {}
        for rpa in _iter_visible(game_dir, (".rpa",)):
            report.archives_scanned += 1
            try:
                for rel, data in read_archive_members(rpa, (".rpy", ".rpym") + _COMPILED_SUFFIXES + _FONT_SUFFIXES,
                                                     keep_case=True):
                    if rel.lower().endswith(_FONT_SUFFIXES):
                        report.font_files.setdefault(rel, data)
                        continue
                    if rel.lower().endswith(_COMPILED_SUFFIXES):
                        compiled.setdefault(rel[:-1].lower(), (rel, data, "rpa:rpyc"))
                        continue
                    if rel.lower() in logical_sources:
                        continue
                    logical_sources[rel.lower()] = (rel, _decode_source(data), "rpa:rpy")
                    report.archive_script_files += 1
            except Exception as exc:
                report.parse_errors.append(f"{rpa.name}: {exc}")

        # Visible compiled scripts and fonts.
        for path in _iter_visible(game_dir, _COMPILED_SUFFIXES):
            rel = path.relative_to(game_dir).as_posix()
            compiled[rel[:-1].lower()] = (rel, b"", "rpyc:" + str(path))
        for path in _iter_visible(game_dir, _FONT_SUFFIXES):
            rel = path.relative_to(game_dir).as_posix()
            if rel.lower().startswith(("linguanova_mod_fonts/", "tl/")):
                continue
            try:
                report.font_files.setdefault(rel, path.read_bytes())
            except OSError as exc:
                report.parse_errors.append(f"{rel}: {exc}")

        # 3) Parse the unified logical source view.
        for rel, text, kind in logical_sources.values():
            try:
                report.candidates.extend(self.parser.parse_text(text, rel, kind))
                report.character_names.update(_character_names_in(text))
            except Exception as exc:
                report.parse_errors.append(f"{rel}: {exc}")

        # 4) Compiled scripts WITHOUT source (games shipped as .rpyc / .rpa only):
        #    read their AST with LinguaNova's RPYC reader. Nothing is written to
        #    the game folder; archive members go through a private temp folder.
        orphans = [item for key, item in sorted(compiled.items()) if key not in logical_sources]
        if orphans:
            self._read_compiled(orphans, report)

        return report
