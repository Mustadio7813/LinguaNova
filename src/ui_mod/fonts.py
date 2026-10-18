# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — keep the game's fonts unless they cannot draw the language.
"""Font plan for one MOD language.

Every game font (visible or inside .rpa) is checked with fontTools against the
characters actually used by the translations. Only fonts that miss characters
are mapped (``config.font_replacement_map`` at runtime) to a font that has them;
the others keep the game's look. Replacement fonts are stored in
``game/linguanova_mod_fonts/`` — outside ``tl/`` so Ren'Py does not take the
folder for a language.
"""
from __future__ import annotations

import io
import json
import logging
import unicodedata
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Set, Tuple

from .languages import ModLanguage, char_script

logger = logging.getLogger("LinguaNova")

FONT_DIR = "linguanova_mod_fonts"
_INDEX = "index.json"
# Ren'Py's default font (DejaVu Sans) covers these writing systems.
_DEJAVU_SCRIPTS = {"LATIN", "GREEK", "CYRILLIC", "ARABIC", "HEBREW", "ARMENIAN", "GEORGIAN"}
_RENPY_DEFAULT_FONTS = ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
# Allow a few exotic punctuation marks to be missing before replacing a font.
_MAX_MISSING = 0

FontFetcher = Callable[[str, Path], Tuple[bool, str]]


def needed_characters(texts: Iterable[str]) -> Set[str]:
    """Letters and combining marks the translations need (punctuation is ignored)."""
    out: Set[str] = set()
    for text in texts:
        for char in text or "":
            if unicodedata.category(char)[0] in ("L", "M"):
                out.add(char)
    return out


def font_codepoints(data: bytes) -> Optional[Set[int]]:
    try:
        from fontTools.ttLib import TTCollection, TTFont
    except Exception as exc:  # fontTools missing
        logger.warning("[#MOD] fontTools unavailable, font check skipped: %s", exc)
        return None
    try:
        if data[:4] == b"ttcf":
            font = TTCollection(io.BytesIO(data)).fonts[0]
        else:
            font = TTFont(io.BytesIO(data), lazy=True)
        cmap = font.getBestCmap() or {}
        return set(cmap)
    except Exception as exc:
        logger.debug("[#MOD] unreadable font: %s", exc)
        return None


def default_fetcher(family: str, target_dir: Path) -> Tuple[bool, str]:
    """Download a Google Fonts family through LinguaNova's existing font tool."""
    from src.tools.font_injector import _download_font
    return _download_font(family, target_dir)


def _candidates(language: ModLanguage):
    try:
        from src.tools.lang_scripts import font_candidates
        families = [family for family, _rtl in font_candidates(language.api)[0]]
    except Exception:
        families = []
    return families or ["Noto Sans"]


def _load_index(font_dir: Path) -> Dict[str, str]:
    try:
        data = json.loads((font_dir / _INDEX).read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}
    except Exception:
        return {}


def plan_fonts(
    game_dir: Path,
    game_fonts: Dict[str, bytes],
    language: ModLanguage,
    translations: Iterable[str],
    fetcher: Optional[FontFetcher] = None,
) -> Tuple[Dict[str, str], Dict[str, object]]:
    """Return ({game font: replacement font}, info for the report)."""
    needed = needed_characters(translations)
    info: Dict[str, object] = {"status": "ok", "replaced": [], "font": "", "missing_characters": 0}
    if not needed:
        return {}, info
    to_replace = []
    unreadable = []
    for rel, data in sorted(game_fonts.items()):
        cps = font_codepoints(data)
        if cps is None:
            unreadable.append(rel)
            continue
        missing = [c for c in needed if ord(c) not in cps]
        if len(missing) > _MAX_MISSING:
            to_replace.append(rel)
    scripts = {char_script(c) for c in needed if char_script(c)}
    if not game_fonts or scripts - _DEJAVU_SCRIPTS:
        # Text drawn with Ren'Py's built-in default font.
        if scripts - _DEJAVU_SCRIPTS:
            to_replace.extend(_RENPY_DEFAULT_FONTS)
    if unreadable and scripts - {"LATIN"}:
        to_replace.extend(unreadable)
    info["unreadable_fonts"] = unreadable
    if not to_replace:
        return {}, info

    font_dir = game_dir / FONT_DIR
    font_dir.mkdir(parents=True, exist_ok=True)
    index = _load_index(font_dir)
    fetch = fetcher or default_fetcher
    chosen = ""
    for family in _candidates(language):
        filename = index.get(family, "")
        if not filename or not (font_dir / filename).is_file():
            try:
                ok, filename = fetch(family, font_dir)
            except Exception as exc:
                logger.warning("[#MOD] font download failed (%s): %s", family, exc)
                ok, filename = False, ""
            if not ok or not filename:
                continue
            index[family] = filename
        cps = font_codepoints((font_dir / filename).read_bytes())
        if cps is None:
            continue
        missing = [c for c in needed if ord(c) not in cps]
        if len(missing) <= _MAX_MISSING:
            chosen = filename
            info["font"] = family
            break
        info["missing_characters"] = len(missing)
    try:
        (font_dir / _INDEX).write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
    if not chosen:
        info["status"] = "missing"
        info["replaced"] = sorted(set(to_replace))
        return {}, info
    plan: Dict[str, str] = {}
    for rel in to_replace:
        plan[rel] = f"{FONT_DIR}/{chosen}"
        base = rel.rsplit("/", 1)[-1]
        plan.setdefault(base, f"{FONT_DIR}/{chosen}")
    info["replaced"] = sorted(set(to_replace))
    return plan, info
