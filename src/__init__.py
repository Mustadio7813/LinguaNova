# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Top-level package for LinguaNova.

Keep package initialisation deliberately lightweight.  Importing ``src`` (or a
small module such as ``src.version``) must not import the complete translation
stack and all of its optional/third-party dependencies.  Heavy subpackages are
loaded lazily on first access.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .version import VERSION

__all__ = ["core", "utils", "VERSION"]


def __getattr__(name: str) -> Any:
    """Lazily expose the historical ``src.core`` and ``src.utils`` attributes."""
    if name in {"core", "utils"}:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
