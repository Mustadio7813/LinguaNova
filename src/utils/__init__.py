# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Utils module for LinguaNova
===============================
"""

from .config import ConfigManager, TranslationSettings, ApiKeys, AppSettings, ProxySettings, Language

__all__ = [
    'ConfigManager', 'TranslationSettings', 'ApiKeys', 'AppSettings', 'ProxySettings', 'Language'
]
