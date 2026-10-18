# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""Update checker for LinguaNova.

Fetches the latest release tag from GitHub and compares it to the current
application version. Uses the GitHub API first and falls back to the releases
HTML page if needed.

No update source is configured by default. To enable the checker, set
``UPDATE_REPO`` below to ``"owner/repository"`` or export the environment
variable ``LINGUANOVA_UPDATE_REPO`` with that value.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Optional, Tuple

import requests


# "owner/repository" of the GitHub project that publishes LinguaNova releases.
# Empty by default: the update check is then disabled.
UPDATE_REPO = ""

NOT_CONFIGURED = "update source not configured"


def get_update_repo() -> str:
    """Return the configured ``owner/repo`` (env var wins over the constant)."""
    repo = (os.environ.get("LINGUANOVA_UPDATE_REPO") or UPDATE_REPO or "").strip().strip("/")
    return repo if re.fullmatch(r"[\w.-]+/[\w.-]+", repo) else ""


def is_configured() -> bool:
    return bool(get_update_repo())


def _releases_url() -> str:
    repo = get_update_repo()
    return f"https://github.com/{repo}/releases" if repo else ""


def _api_url() -> str:
    repo = get_update_repo()
    return f"https://api.github.com/repos/{repo}/releases/latest" if repo else ""


@dataclass
class UpdateCheckResult:
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str
    error: Optional[str] = None


def _parse_version(version: str) -> Tuple[int, ...]:
    parts = re.findall(r"\d+", version or "")
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts)


def _is_newer(latest: str, current: str) -> bool:
    latest_parts = _parse_version(latest)
    current_parts = _parse_version(current)
    length = max(len(latest_parts), len(current_parts))
    latest_parts += (0,) * (length - len(latest_parts))
    current_parts += (0,) * (length - len(current_parts))
    return latest_parts > current_parts


def _fetch_latest_release(timeout: int = 10) -> Tuple[str, str]:
    if not is_configured():
        raise RuntimeError(NOT_CONFIGURED)
    releases_url = _releases_url()
    headers = {"User-Agent": "LinguaNova"}

    # Preferred: GitHub API
    try:
        response = requests.get(_api_url(), timeout=timeout, headers=headers)
        if response.status_code == 200:
            payload = response.json() or {}
            tag = (payload.get("tag_name") or payload.get("name") or "").strip()
            url = (payload.get("html_url") or releases_url).strip()
            if tag:
                return tag, url or releases_url
    except Exception:
        pass

    # Fallback: releases HTML page
    response = requests.get(releases_url, timeout=timeout, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}")

    match = re.search(r"/releases/tag/([^\"<>\s]+)", response.text)
    if not match:
        raise RuntimeError("Latest release tag not found on releases page")

    return match.group(1), releases_url


def check_for_updates(current_version: str, timeout: int = 10) -> UpdateCheckResult:
    try:
        latest_version, url = _fetch_latest_release(timeout=timeout)
    except Exception as exc:
        return UpdateCheckResult(
            current_version=current_version,
            latest_version="",
            update_available=False,
            release_url=_releases_url(),
            error=str(exc),
        )

    return UpdateCheckResult(
        current_version=current_version,
        latest_version=latest_version,
        update_available=_is_newer(latest_version, current_version),
        release_url=url or _releases_url(),
        error=None,
    )
