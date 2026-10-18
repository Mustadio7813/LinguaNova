# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — per-language glossary for consistent names and terms.
"""MOD glossary: ``game/tl/<language>/linguanova_mod_glossary.json``.

LinguaNova's main glossary is a single source→target dictionary with no
language; reusing it in a multilanguage MOD would put, e.g., Spanish terms into
Polish text. MOD therefore keeps one glossary per language. Character names
found in ``Character("Name")`` are seeded as "keep as is" so they never get
translated differently from line to line.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

GLOSSARY_FILE = "linguanova_mod_glossary.json"
GLOSSARY_SCHEMA = 1
_TOKEN = "__LNMOD_TERM_{}__"


def _pattern(term: str) -> re.Pattern:
    # Boundaries are letters/digits only: "_" must count as a boundary because
    # protected tags arrive as "__LNMOD_TOKEN_0__Anna__LNMOD_TOKEN_1__".
    flags = 0 if (len(term) <= 3 or term[:1].isupper()) else re.IGNORECASE
    return re.compile(r"(?<![^\W_])" + re.escape(term) + r"(?![^\W_])", flags)


def _sorted_terms(terms: Dict[str, str]) -> List[Tuple[str, str]]:
    return sorted(((k.strip(), v) for k, v in terms.items() if k and k.strip() and isinstance(v, str)),
                  key=lambda item: -len(item[0]))


def load_glossary(path: Path, seed_names: Iterable[str] = ()) -> Tuple[Dict[str, str], Dict[str, object], bool]:
    """Return (terms, payload_to_write, changed). Never drops the user's terms."""
    payload: Dict[str, object] = {}
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    terms = payload.get("terms") if isinstance(payload.get("terms"), dict) else {}
    terms = {k: v for k, v in terms.items() if isinstance(k, str) and isinstance(v, str)}
    changed = not path.is_file() or payload.get("schema") != GLOSSARY_SCHEMA
    for name in sorted(set(seed_names)):
        if name and name not in terms:
            terms[name] = name
            changed = True
    out = {
        "schema": GLOSSARY_SCHEMA,
        "help": "Términos que deben traducirse siempre igual: \"original\": \"traducción\". "
                "Un nombre igual en ambos lados no se traduce. Se aplica en la próxima generación.",
        "terms": dict(sorted(terms.items(), key=lambda kv: kv[0].casefold())),
    }
    return terms, out, changed


def exact_term(text: str, terms: Dict[str, str]) -> Optional[str]:
    stripped = text.strip()
    for source, target in terms.items():
        if source.strip() == stripped:
            prefix = text[:len(text) - len(text.lstrip())]
            suffix = text[len(text.rstrip()):]
            return prefix + target + suffix
    return None


def protect_terms(text: str, terms: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """Replace glossary terms by neutral tokens the engines leave alone."""
    mapping: Dict[str, str] = {}
    result = text
    for source, target in _sorted_terms(terms):
        pattern = _pattern(source)

        def repl(_match, _target=target):
            key = _TOKEN.format(len(mapping))
            mapping[key] = _target
            return key

        result = pattern.sub(repl, result)
    return result, mapping


def restore_terms(text: str, mapping: Dict[str, str]) -> str:
    """Put the glossary targets back (tolerates spaces engines add inside the token)."""
    return re.sub(r"__\s*LNMOD_TERM_(\d+)\s*__",
                  lambda m: mapping.get(f"__LNMOD_TERM_{m.group(1)}__", m.group(0)), text)


def leaked_term_tokens(text: str) -> bool:
    return "LNMOD_TERM_" in text


def consistent(source: str, translated: str, terms: Dict[str, str]) -> bool:
    """True when every glossary term in ``source`` appears as its target in ``translated``."""
    folded = translated.casefold()
    for term, target in _sorted_terms(terms):
        if _pattern(term).search(source) and target.casefold() not in folded:
            return False
    return True
