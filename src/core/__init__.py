# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Core package for LinguaNova.

Historically this module imported the parser, every translator, proxy support
and output formatting eagerly.  That meant importing an unrelated submodule
could fail because of a missing dependency used by another subsystem.  Public
exports are kept backward compatible, but are now resolved lazily.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "RenPyParser": (".parser", "RenPyParser"),
    "TranslationEngine": (".translator", "TranslationEngine"),
    "TranslationRequest": (".translator", "TranslationRequest"),
    "TranslationResult": (".translator", "TranslationResult"),
    "BaseTranslator": (".translator", "BaseTranslator"),
    "GoogleTranslator": (".translator", "GoogleTranslator"),
    "DeepLTranslator": (".translator", "DeepLTranslator"),
    "LibreTranslateTranslator": (".translator", "LibreTranslateTranslator"),
    "BingTranslator": (".translator", "BingTranslator"),
    "PseudoTranslator": (".translator", "PseudoTranslator"),
    "TranslationManager": (".translator", "TranslationManager"),
    "ProxyManager": (".proxy_manager", "ProxyManager"),
    "ProxyInfo": (".proxy_manager", "ProxyInfo"),
    "RenPyOutputFormatter": (".output_formatter", "RenPyOutputFormatter"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value
