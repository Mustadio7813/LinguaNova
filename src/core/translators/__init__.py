# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Translators package for LinguaNova.
"""
from .base import (
    BaseTranslator,
    TranslationEngine,
    TranslationRequest,
    TranslationResult,
)
from .router import (
    _FamilyHealth,
    EndpointRouter,
)
from .google import GoogleTranslator
from .services import (
    PseudoTranslator,
    DeepLTranslator,
    LibreTranslateTranslator,
    BingTranslator,
)
from .manager import TranslationManager

__all__ = [
    "BaseTranslator",
    "TranslationEngine",
    "TranslationRequest",
    "TranslationResult",
    "_FamilyHealth",
    "EndpointRouter",
    "GoogleTranslator",
    "PseudoTranslator",
    "DeepLTranslator",
    "LibreTranslateTranslator",
    "BingTranslator",
    "TranslationManager",
]
