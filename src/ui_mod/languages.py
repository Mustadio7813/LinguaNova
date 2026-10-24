# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — single language contract for the isolated MOD subsystem.
"""Resolve the five supported MOD languages through the central language catalogue."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Dict, FrozenSet, List, Optional, Tuple

# Writing system expected for target text (catalogue API code -> script tag).
# Anything not listed is Latin. Tags are matched against Unicode character names.
_SCRIPT_BY_API: Dict[str, str] = {"ru": "CYRILLIC"}
_RTL_API = frozenset()
_UNSPACED_SCRIPTS = frozenset()

# Minimal offline fallback; used only if the central catalogue cannot be imported.
_FALLBACK_CATALOGUE: Tuple[Dict[str, str], ...] = (
    {"renpy": "english", "api": "en", "english": "English", "native": "English"},
    {"renpy": "spanish", "api": "es", "english": "Spanish", "native": "Español"},
    {"renpy": "portuguese", "api": "pt", "english": "Portuguese", "native": "Português"},
    {"renpy": "french", "api": "fr", "english": "French", "native": "Français"},
    {"renpy": "russian", "api": "ru", "english": "Russian", "native": "Русский"},
)


@dataclass(frozen=True)
class ModLanguage:
    renpy: str                 # Ren'Py tl/<folder> identifier (e.g. "polish")
    api: str                   # code sent to translation engines (e.g. "pl")
    english: str
    native: str
    script: str                # expected writing system of text in this language
    rtl: bool
    aliases: FrozenSet[str] = field(default_factory=frozenset)

    @property
    def unspaced(self) -> bool:
        return self.script in _UNSPACED_SCRIPTS


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\s\-]+", "_", text.strip().lower())


def _load_catalogue() -> List[Dict[str, str]]:
    try:
        from src.utils.config import ConfigManager
        # get_all_languages() only returns a literal list; calling it unbound
        # avoids ConfigManager.__init__ (config files, logging, migrations).
        items = ConfigManager.get_all_languages(None)  # type: ignore[arg-type]
        if isinstance(items, list) and items:
            return [dict(item) for item in items]
    except Exception:
        pass
    return [dict(item) for item in _FALLBACK_CATALOGUE]


class _Registry:
    def __init__(self) -> None:
        self.languages: List[ModLanguage] = []
        self.by_key: Dict[str, ModLanguage] = {}
        for item in _load_catalogue():
            api = str(item.get("api") or "").strip()
            renpy = str(item.get("renpy") or "").strip()
            if not api or not renpy:
                continue
            aliases = {
                renpy.lower(), api.lower(), _fold(renpy), _fold(api),
                _fold(item.get("english", "")), _fold(item.get("native", "")),
                api.lower().replace("-", "_"),
            }
            if "-" in api:
                aliases.add(api.split("-", 1)[0].lower())
            lang = ModLanguage(
                renpy=renpy, api=api, english=str(item.get("english") or renpy),
                native=str(item.get("native") or renpy),
                script=_SCRIPT_BY_API.get(api, "LATIN"), rtl=api in _RTL_API,
                aliases=frozenset(a for a in aliases if a),
            )
            self.languages.append(lang)
        # First pass: exact Ren'Py ids and API codes win over derived aliases.
        for lang in self.languages:
            self.by_key.setdefault(lang.renpy.lower(), lang)
            self.by_key.setdefault(lang.api.lower(), lang)
        for lang in self.languages:
            for alias in sorted(lang.aliases):
                self.by_key.setdefault(alias, lang)
_REGISTRY: Optional[_Registry] = None


def _registry() -> _Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _Registry()
    return _REGISTRY


def all_languages() -> List[ModLanguage]:
    return list(_registry().languages)


def resolve_language(value: Optional[str]) -> Optional[ModLanguage]:
    """Return the catalogue language for a Ren'Py id, API code or name; None for auto/unknown."""
    raw = str(value or "").strip()
    if not raw or raw.lower() == "auto":
        return None
    reg = _registry()
    for key in (raw.lower(), _fold(raw), raw.lower().replace("-", "_")):
        if key in reg.by_key:
            return reg.by_key[key]
    return None


def api_code(value: Optional[str]) -> str:
    """Engine code for a language value; 'auto' stays 'auto'.

    Unknown values raise ValueError instead of being forwarded verbatim: sending a
    Ren'Py folder name such as "polish" to an engine was a confirmed defect.
    """
    raw = str(value or "").strip()
    if not raw or raw.lower() == "auto":
        return "auto"
    lang = resolve_language(raw)
    if lang is None:
        raise ValueError(f"Unknown MOD language: {raw!r}")
    return lang.api


def folder_aliases(value: Optional[str]) -> List[str]:
    """Folder names that can hold this language under game/tl/ (case-insensitive)."""
    lang = resolve_language(value)
    if lang is None:
        raw = str(value or "").strip().lower()
        return [raw] if raw else []
    names = {lang.renpy.lower(), lang.api.lower(), lang.api.lower().replace("-", "_"), _fold(lang.english)}
    return sorted(n for n in names if n)


def char_script(char: str) -> Optional[str]:
    if not char.isalpha():
        return None
    try:
        name = unicodedata.name(char)
    except ValueError:
        return None
    if name.startswith(("HIRAGANA", "KATAKANA")):
        return "JAPANESE"
    if name.startswith("CJK"):
        return "HAN"
    for tag in ("LATIN", "CYRILLIC", "GREEK", "ARABIC", "HEBREW", "THAANA", "DEVANAGARI",
                "BENGALI", "GUJARATI", "GURMUKHI", "ORIYA", "TAMIL", "TELUGU", "KANNADA",
                "MALAYALAM", "SINHALA", "THAI", "LAO", "KHMER", "MYANMAR", "GEORGIAN",
                "ARMENIAN", "ETHIOPIC", "HANGUL", "MEETEI MAYEK"):
        if name.startswith(tag):
            return tag
    return "OTHER"


def script_matches(expected: str, actual: Optional[str]) -> bool:
    if actual is None:
        return False
    if expected == actual:
        return True
    # Japanese text legitimately mixes kana and kanji.
    return expected == "JAPANESE" and actual == "HAN"
