# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Custom exceptions for LinguaNova.
"""

from typing import Any, Dict, Optional


class LinguaNovaError(Exception):
    """Base exception for LinguaNova with optional error code and context data."""

    def __init__(
        self,
        message: str = "",
        code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        solution_hint: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = context or {}
        self.solution_hint = solution_hint

    def get_user_friendly_message(self) -> str:
        msg = self.message
        if self.solution_hint:
            msg += f" (Çözüm ipucu: {self.solution_hint})"
        return msg

    def __str__(self) -> str:
        parts = [self.message] if self.message else [self.__class__.__name__]
        if self.code is not None:
            parts.append(f"[code={self.code}]")
        if self.solution_hint:
            parts.append(f"[ipucu={self.solution_hint}]")
        if self.context:
            parts.append(str(self.context))
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r}, context={self.context!r})"


class ProxyError(LinguaNovaError):
    """Raised when proxy-related errors occur."""


class TranslationError(LinguaNovaError):
    """Raised when translation-related errors occur."""


class RateLimitError(TranslationError):
    """Raised when rate limits (HTTP 429) are exceeded."""

    def __init__(self, message: str = "Rate limit aşıldı (HTTP 429)", **kwargs) -> None:
        kwargs.setdefault("solution_hint", "Lütfen istek gecikmesini artırın veya proxy rotasyonunu etkinleştirin.")
        super().__init__(message=message, **kwargs)


class QuotaExceededError(TranslationError):
    """Raised when API quota or credit limit is reached."""

    def __init__(self, message: str = "API kotası tükendi", **kwargs) -> None:
        kwargs.setdefault("solution_hint", "API anahtarınızı ve sağlayıcı bakiyenizi kontrol edin.")
        super().__init__(message=message, **kwargs)


class NetworkConnectionError(TranslationError):
    """Raised when network connectivity issues occur during translation."""

    def __init__(self, message: str = "Ağ bağlantısı hatası", **kwargs) -> None:
        kwargs.setdefault("solution_hint", "İnternet bağlantınızı veya ayarlanmış proxy bağlantısını kontrol edin.")
        super().__init__(message=message, **kwargs)


class EngineUnavailableError(TranslationError):
    """Raised before a run when the selected engine cannot be reached or rejects the key."""


class ParseError(LinguaNovaError):
    """Raised when parsing-related errors occur."""


class ConfigError(LinguaNovaError):
    """Raised when configuration-related errors occur."""


class GuiError(LinguaNovaError):
    """Raised when GUI-related errors occur."""

