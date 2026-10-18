# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — strict token protection for MOD-only translations.
from __future__ import annotations

from collections import Counter
import re
from typing import Dict, List, Tuple

from src.core.tag_structure import introduces_replacement_char, tag_structure_regression

# Ren'Py interpolation, text tags, %-formatting and str.format-style fields.
_TOKEN_RE = re.compile(
    r"(\[[^\[\]\n]+\]|"
    r"\{\{|\}\}|"
    r"\{/?[A-Za-z][^{}\n]*\}|"
    r"%\([A-Za-z_][A-Za-z0-9_]*\)[#0\- +]?(?:\d+|\*)?(?:\.\d+)?[diouxXeEfFgGcrs%]|"
    r"(?<!%)%(?:[#0\- +]?(?:\d+|\*)?(?:\.\d+)?[diouxXeEfFgGcrs%])|"
    r"\{[A-Za-z_][A-Za-z0-9_.!:\[\]-]*\})"
)
_SENTINEL_RE = re.compile(r"__LNMOD_TOKEN_(\d+)__")
_JUNK_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\Z")


def extract_tokens(text: str) -> List[str]:
    return [m.group(0) for m in _TOKEN_RE.finditer(text or "")]


def is_junk(text: str) -> bool:
    """Reject empty UI noise, isolated letters and standalone color literals."""
    value = (text or "").strip()
    if not value or _JUNK_COLOR_RE.fullmatch(value):
        return True
    if len(value) == 1 and value.isalpha():
        return True
    if not any(char.isalnum() for char in value):
        return True
    return False


def preserve_edge_whitespace(source: str, translated: str) -> str:
    """Use the source's exact leading/trailing whitespace around translated text."""
    prefix = source[:len(source) - len(source.lstrip())]
    suffix = source[len(source.rstrip()):]
    return prefix + translated.strip() + suffix


def protect_mod_text(text: str) -> Tuple[str, Dict[str, str]]:
    mapping: Dict[str, str] = {}
    index = 0

    def repl(match: re.Match) -> str:
        nonlocal index
        key = f"__LNMOD_TOKEN_{index}__"
        mapping[key] = match.group(0)
        index += 1
        return key

    return _TOKEN_RE.sub(repl, text), mapping


def restore_mod_text(text: str, mapping: Dict[str, str]) -> str:
    restored = text
    for key, value in mapping.items():
        restored = restored.replace(key, value)
    return restored


def structure_problem(source: str, translated: str) -> str:
    """Reason why ``translated`` cannot replace ``source`` in Ren'Py, or "".

    * ``structure_changed``: variables/tags/format fields differ as a set.
    * ``tag_order_invalid``: same tags, but closed before being opened or
      crossed ("{/i} ... {i}") — Ren'Py raises "closes a text tag that isn't
      open" when such a string is displayed (audit case 01, 2026-10-18).
    * ``replacement_char``: U+FFFD (undecodable bytes) not present in the source.
    """
    if Counter(extract_tokens(source)) != Counter(extract_tokens(translated)):
        return "structure_changed"
    if tag_structure_regression(source, translated) is not None:
        return "tag_order_invalid"
    if introduces_replacement_char(source, translated):
        return "replacement_char"
    return ""


def validate_mod_translation(source: str, translated: str) -> bool:
    """Fail closed when variables/tags/format fields differ in any way."""
    if is_junk(source) or is_junk(translated):
        return False
    return not structure_problem(source, translated)
