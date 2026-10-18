# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — per-engine language codes and documented capabilities for MOD requests.
"""Engine adapters used only by MOD (the main translators are not modified).

Findings (2026-10-17) in the main translators that would make MOD answer in the
wrong language, compensated here by sending codes the main mapping passes through:

* DeepL ``_map_lang``: ``zh-TW`` → ``ZH`` (DeepL answers in Simplified Chinese),
  ``no`` → ``NO`` (DeepL expects ``NB``), ``ku`` → ``KU`` (DeepL uses ``KMR``).
  MOD sends ``ZH-HANT`` / ``ZH-HANS`` / ``NB`` / ``KMR`` which ``_map_lang`` upper-cases unchanged.
* OpenAI / Gemini prompts name the language through a 24-entry table and fall back
  to the raw code ("sw", "ceb"…). MOD sends the English language name for the
  others so the prompt reads "Swahili" instead of "sw".

DeepL's lists come from https://developers.deepl.com/docs/getting-started/supported-languages
(consulted 2026-10-17). Other engines have no machine-checkable list in this
build; their support is reported as "unverified" and is enforced at run time by
MOD's answer validation.
"""
from __future__ import annotations

from typing import Optional, Tuple

from .languages import ModLanguage

DEEPL_DOC_SOURCE = frozenset((
    "ACE AF SQ AR AN HY AS AY AZ BA EU BE BN BHO BS BR BG MY YUE CA CEB ZH HR CS DA PRS NL EN EO ET "
    "FI FR GL KA DE EL GN GU HT HA HE HI HU IS IG ID GA IT JA JV PAM KK GOM KO KMR CKB KY LA LV LN LT "
    "LMO LB MK MAI MG MS ML MT MI MR MN NE NB OC OM PAG PS FA PL PT PA QU RO RU SA SR ST SCN SK SL ES "
    "SU SW SV TL TG TA TT TE TH TS TN TR TK UK UR UZ VI CY WO XH YI ZU"
).split())
DEEPL_DOC_TARGET = DEEPL_DOC_SOURCE | frozenset(
    "ZH-HANS ZH-HANT EN-US EN-GB FR-CA FR-FR DE-DE DE-CH PT-BR PT-PT ES-ES ES-419".split()
)
DEEPL_DOC_DATE = "2026-10-17"

_DEEPL_TARGET_OVERRIDES = {"zh-CN": "ZH-HANS", "zh-TW": "ZH-HANT", "no": "NB", "ku": "KMR"}
_DEEPL_SOURCE_OVERRIDES = {"zh-CN": "ZH", "zh-TW": "ZH", "no": "NB", "ku": "KMR"}

# Codes that the AI prompt table already names (src/core/ai_translator._SUPPORTED_LANGUAGES).
_AI_NAMED_CODES = frozenset(
    "en tr de fr es it pt ru zh ja ko ar pl nl sv no da fi hu cs ro uk vi th".split()
)


def _engine_key(engine) -> str:
    return str(getattr(engine, "value", engine) or "").lower()


def _deepl_code(lang: ModLanguage, role: str) -> str:
    overrides = _DEEPL_TARGET_OVERRIDES if role == "target" else _DEEPL_SOURCE_OVERRIDES
    if lang.api in overrides:
        return overrides[lang.api]
    if role == "target" and lang.api == "en":
        return "EN-US"
    if role == "target" and lang.api == "pt":
        return "PT-PT"
    return lang.api.upper()


def request_code(engine, lang: Optional[ModLanguage], role: str) -> str:
    """Code placed in TranslationRequest.source_lang/target_lang for ``engine``."""
    if lang is None:
        return "auto"
    key = _engine_key(engine)
    if key == "deepl":
        return _deepl_code(lang, role)
    if key in ("openai", "gemini") and lang.api not in _AI_NAMED_CODES:
        return lang.english
    return lang.api


def support(engine, lang: Optional[ModLanguage], role: str) -> Tuple[str, str]:
    """Return (status, detail): documented | unsupported | unverified."""
    if lang is None:
        return "documented", "auto-detect"
    key = _engine_key(engine)
    if key == "deepl":
        code = _deepl_code(lang, role)
        allowed = DEEPL_DOC_TARGET if role == "target" else DEEPL_DOC_SOURCE
        if code in allowed:
            return "documented", f"DeepL {code} (docs {DEEPL_DOC_DATE})"
        return "unsupported", f"DeepL does not list {code} as a {role} language (docs {DEEPL_DOC_DATE})"
    if key == "pseudo":
        return "unsupported", "Pseudo-localization is a test engine, not a translator"
    return "unverified", "no machine-checkable list for this engine; answers are validated at run time"
