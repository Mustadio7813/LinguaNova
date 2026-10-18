# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
LinguaNova Translation Subsystem Facade.

This module provides 100% backward-compatible re-exports for the modularized
translators under ``src.core.translators``.
"""
from __future__ import annotations

# Syntax guard re-exports (for legacy imports in tests / parser)
from .syntax_guard import (
    protect_renpy_syntax,
    restore_renpy_syntax,
    validate_translation_integrity,
    inject_missing_placeholders,
    protect_renpy_syntax_html,
    restore_renpy_syntax_html,
)

# Constants & Exceptions re-exports
from src.core.constants import (
    GOOGLE_ENDPOINTS,
    GOOGLE_BROWSER_HEADERS,
    GOOGLE_CLIENTS5_ENDPOINT,
    GOOGLE_BATCHEXECUTE_ENDPOINT,
    LINGVA_INSTANCES,
    USER_AGENTS,
    MIRROR_MAX_FAILURES,
    MIRROR_BAN_TIME,
    RATE_LIMIT_CIRCUIT_BREAKER_THRESHOLD,
    RATE_LIMIT_LONG_COOLDOWN,
    RATE_LIMIT_PRIMARY_PROBE_INTERVAL,
)
from src.core.exceptions import (
    RateLimitError,
    QuotaExceededError,
    NetworkConnectionError,
)
from src.utils.config import get_effective_batch_size

# Core translator classes re-exports
from src.core.translators import (
    BaseTranslator,
    TranslationEngine,
    TranslationRequest,
    TranslationResult,
    _FamilyHealth,
    EndpointRouter,
    GoogleTranslator,
    PseudoTranslator,
    DeepLTranslator,
    LibreTranslateTranslator,
    BingTranslator,
    TranslationManager,
)

__all__ = [
    # Base
    "BaseTranslator",
    "TranslationEngine",
    "TranslationRequest",
    "TranslationResult",
    # Router
    "_FamilyHealth",
    "EndpointRouter",
    # Google
    "GoogleTranslator",
    # Services
    "PseudoTranslator",
    "DeepLTranslator",
    "LibreTranslateTranslator",
    "BingTranslator",
    # Manager
    "TranslationManager",
    # Syntax guard
    "protect_renpy_syntax",
    "restore_renpy_syntax",
    "validate_translation_integrity",
    "inject_missing_placeholders",
    "protect_renpy_syntax_html",
    "restore_renpy_syntax_html",
    # Constants
    "GOOGLE_ENDPOINTS",
    "GOOGLE_BROWSER_HEADERS",
    "GOOGLE_CLIENTS5_ENDPOINT",
    "GOOGLE_BATCHEXECUTE_ENDPOINT",
    "LINGVA_INSTANCES",
    "USER_AGENTS",
    "MIRROR_MAX_FAILURES",
    "MIRROR_BAN_TIME",
    "RATE_LIMIT_CIRCUIT_BREAKER_THRESHOLD",
    "RATE_LIMIT_LONG_COOLDOWN",
    "RATE_LIMIT_PRIMARY_PROBE_INTERVAL",
    # Exceptions
    "RateLimitError",
    "QuotaExceededError",
    "NetworkConnectionError",
    "get_effective_batch_size",
]
