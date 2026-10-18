# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: added 2026-10-18 (interface languages created by the user).
"""Create a draft interface language by machine-translating ``locales/en.json``.

The result is written to ``<data dir>/locales/<code>.json``, which
``ConfigManager._load_user_language_files`` loads at start-up. It is a draft:
keys the engine could not translate are left out, so they show in English.

Placeholders are never sent to the engine. Each text is split into the parts
that must stay as they are (``{name}``, ``%s``, ``%(name)s``, ``{{``, ``<b>``,
``\\n``…) and the plain-text parts between them; only the plain-text parts are
translated and the text is put back together, so no placeholder can be lost
or renamed by the engine.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

PROTECTED = re.compile(
    r"(\{\{|\}\}"            # literal braces
    r"|\{[^{}\s]*\}"         # {name}, {0}, {}
    r"|%\([A-Za-z_]+\)[sdif]"  # %(name)s
    r"|%[sdif%]"             # %s %d
    r"|<[^<>]+>"             # HTML-like tags
    r"|\r?\n|\t"             # line breaks / tabs
    r"|https?://\S+)"        # URLs
)
LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def split_protected(text: str) -> List[Tuple[bool, str]]:
    """[(translatable, piece), ...] — joining the pieces gives ``text`` back."""
    parts: List[Tuple[bool, str]] = []
    pos = 0
    for match in PROTECTED.finditer(text):
        if match.start() > pos:
            parts.append((True, text[pos:match.start()]))
        parts.append((False, match.group(0)))
        pos = match.end()
    if pos < len(text):
        parts.append((True, text[pos:]))
    # Pieces without letters (spaces, punctuation, emoji) are kept as they are.
    return [(t and bool(LETTER.search(p)), p) for t, p in parts]


def _edges(piece: str) -> Tuple[str, str, str]:
    """Split leading/trailing spaces and symbols (emoji, arrows) off a piece."""
    lead = len(piece) - len(piece.lstrip())
    trail = len(piece) - len(piece.rstrip())
    core = piece.strip()
    m = re.match(r"^([^\w\"'¿¡(]+)", core, re.UNICODE)
    prefix = m.group(1) if m else ""
    core = core[len(prefix):]
    return piece[:lead] + prefix, core, piece[len(piece) - trail:] if trail else ""


def iter_strings(data: dict, prefix: str = "") -> Iterable[Tuple[str, str]]:
    for key, value in data.items():
        if key.startswith("_"):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from iter_strings(value, path)
        elif isinstance(value, str) and value.strip():
            yield path, value


def _set_path(target: dict, path: str, value: str) -> None:
    keys = path.split(".")
    node = target
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def collect_segments(data: dict) -> List[str]:
    """Unique plain-text pieces to translate, in order of appearance."""
    seen: Dict[str, None] = {}
    for _path, text in iter_strings(data):
        for translatable, piece in split_protected(text):
            if translatable:
                _lead, core, _trail = _edges(piece)
                if core and LETTER.search(core):
                    seen.setdefault(core, None)
    return list(seen)


def rebuild(text: str, translations: Dict[str, str]) -> Optional[str]:
    """Translated text, or None when any piece has no translation."""
    out = []
    for translatable, piece in split_protected(text):
        if not translatable:
            out.append(piece)
            continue
        lead, core, trail = _edges(piece)
        if not core or not LETTER.search(core):
            out.append(piece)
            continue
        translated = translations.get(core)
        if not translated:
            return None
        out.append(lead + translated.strip() + trail)
    return "".join(out)


def build_language(source: dict, translations: Dict[str, str], code: str, name: str) -> Tuple[dict, int, int]:
    """Return (locale dict, translated keys, keys left in English)."""
    result: dict = {
        "_language_name": name,
        "_language_code": code,
        "_generated_by": "LinguaNova: machine translation draft of en.json. Review it before sharing.",
    }
    done = missing = 0
    for path, text in iter_strings(source):
        value = rebuild(text, translations)
        if value is None:
            missing += 1
            continue
        _set_path(result, path, value)
        done += 1
    return result, done, missing


def write_language(folder: Path, code: str, data: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{code}.json"
    if target.exists():
        backup = target.with_suffix(".json.bak")
        try:
            os.replace(target, backup)
        except OSError:
            pass
    fd, tmp = tempfile.mkstemp(dir=str(folder), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return target


def generate(source: dict, code: str, name: str, translate: Callable[[List[str]], Dict[str, str]],
             folder: Path, chunk: int = 40,
             progress: Optional[Callable[[int, int], None]] = None,
             should_stop: Optional[Callable[[], bool]] = None) -> Tuple[Path, int, int]:
    """Translate ``source`` with ``translate`` (list of texts -> {text: translation})."""
    segments = collect_segments(source)
    translations: Dict[str, str] = {}
    for start in range(0, len(segments), chunk):
        if should_stop and should_stop():
            break
        batch = segments[start:start + chunk]
        translations.update({k: v for k, v in translate(batch).items() if v})
        if progress:
            progress(min(start + chunk, len(segments)), len(segments))
    data, done, missing = build_language(source, translations, code, name)
    if done == 0:
        raise RuntimeError("the engine did not translate any text")
    return write_language(folder, code, data), done, missing
