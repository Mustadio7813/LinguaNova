# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: added 2026-10-18 (automatic update for the Windows installer).
"""Download, verify and launch a LinguaNova update.

Only the Windows *installed* build updates itself. Everything else (portable
folder, single-file EXE, Linux AppImage, macOS app, running from source) keeps
opening the release page, because a running program cannot replace its own
files safely without an installer.

Flow, used by ``AppBackend``:

1. ``plan_update(result)`` decides whether the release can be installed
   automatically: Windows installed build, an installer asset named
   ``LinguaNova_Setup_<version>.exe`` and a ``SHA256SUMS.txt`` asset.
2. ``download_update(plan, ...)`` downloads both files to
   ``%TEMP%\\LinguaNova_update`` with progress and cancellation, and verifies
   the installer's SHA-256 against ``SHA256SUMS.txt``. A file that does not
   match is deleted and never run.
3. ``launch_installer(path, install_dir)`` starts the installer silently in
   the folder where LinguaNova is installed now (``/DIR=``); the installer
   closes and reopens LinguaNova (``/LNUPDATE``).
4. ``cleanup_downloads()`` removes the downloaded installer on the next start.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

INSTALLER_PATTERN = re.compile(r"^LinguaNova_Setup_[0-9][0-9A-Za-z.\-]*\.exe$", re.IGNORECASE)
CHECKSUMS_NAME = "SHA256SUMS.txt"
INSTALL_MARKER = "linguanova_installed.json"
DOWNLOAD_DIR_NAME = "LinguaNova_update"
MAX_DOWNLOAD_BYTES = 1024 * 1024 * 1024  # 1 GB: far above a real installer
CHUNK = 1024 * 256


class UpdateError(RuntimeError):
    """An update step failed; the message is shown to the user."""


@dataclass
class UpdatePlan:
    installer_name: str
    installer_url: str
    installer_size: int
    checksums_url: str
    install_dir: Path


def current_install_dir() -> Optional[Path]:
    """Folder of the installed Windows build, or None when not installed."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return None
    app_dir = Path(sys.executable).resolve().parent
    if (app_dir / INSTALL_MARKER).is_file():
        return app_dir
    return None


def _allowed_download_url(url: str, repo: str) -> bool:
    prefix = f"https://github.com/{repo}/releases/download/"
    return bool(repo) and url.startswith(prefix)


def plan_update(assets: List[Dict], repo: str, install_dir: Optional[Path] = None) -> Optional[UpdatePlan]:
    """Return what to download, or None when only the release page applies."""
    install_dir = install_dir if install_dir is not None else current_install_dir()
    if install_dir is None:
        return None
    installer = next((a for a in assets if INSTALLER_PATTERN.match(a.get("name", ""))), None)
    sums = next((a for a in assets if a.get("name") == CHECKSUMS_NAME), None)
    if not installer or not sums:
        return None
    if not (_allowed_download_url(installer["url"], repo) and _allowed_download_url(sums["url"], repo)):
        return None
    return UpdatePlan(
        installer_name=installer["name"],
        installer_url=installer["url"],
        installer_size=int(installer.get("size") or 0),
        checksums_url=sums["url"],
        install_dir=install_dir,
    )


def download_dir() -> Path:
    return Path(tempfile.gettempdir()) / DOWNLOAD_DIR_NAME


def expected_sha256(checksums_text: str, file_name: str) -> Optional[str]:
    """Hash listed for ``file_name`` in a ``sha256sum``-style file."""
    for line in (checksums_text or "").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            name = parts[-1].lstrip("*")
            if name == file_name:
                return parts[0].lower()
    return None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, target: Path, progress: Callable[[int, int], None],
              cancel: threading.Event, timeout: int = 30) -> None:
    import requests

    part = target.with_name(target.name + ".part")
    headers = {"User-Agent": "LinguaNova"}
    with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
        if response.status_code != 200:
            raise UpdateError(f"HTTP {response.status_code}")
        total = int(response.headers.get("Content-Length") or 0)
        if total > MAX_DOWNLOAD_BYTES:
            raise UpdateError("download too large")
        done = 0
        with open(part, "wb") as fh:
            for block in response.iter_content(CHUNK):
                if cancel.is_set():
                    raise UpdateError("cancelled")
                if not block:
                    continue
                done += len(block)
                if done > MAX_DOWNLOAD_BYTES:
                    raise UpdateError("download too large")
                fh.write(block)
                progress(done, total)
    os.replace(part, target)


def download_update(plan: UpdatePlan, progress: Callable[[int, int], None],
                    cancel: Optional[threading.Event] = None) -> Path:
    """Download and verify the installer; return its path."""
    import requests

    cancel = cancel or threading.Event()
    folder = download_dir()
    folder.mkdir(parents=True, exist_ok=True)

    response = requests.get(plan.checksums_url, timeout=30, headers={"User-Agent": "LinguaNova"})
    if response.status_code != 200:
        raise UpdateError(f"{CHECKSUMS_NAME}: HTTP {response.status_code}")
    expected = expected_sha256(response.text, plan.installer_name)
    if not expected:
        raise UpdateError(f"{plan.installer_name} is not listed in {CHECKSUMS_NAME}")

    target = folder / plan.installer_name
    try:
        _download(plan.installer_url, target, progress, cancel)
    except Exception:
        for leftover in (target, target.with_name(target.name + ".part")):
            try:
                leftover.unlink()
            except OSError:
                pass
        raise

    actual = sha256_of(target)
    if actual != expected:
        try:
            target.unlink()
        except OSError:
            pass
        raise UpdateError("SHA-256 mismatch: the downloaded installer was deleted")
    return target


def installer_arguments(install_dir: Path) -> List[str]:
    return [
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/CLOSEAPPLICATIONS",
        f"/DIR={install_dir}",
        "/LNUPDATE",
    ]


def launch_installer(installer: Path, install_dir: Path) -> None:
    """Start the installer detached; the caller must quit LinguaNova next."""
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(
        [str(installer), *installer_arguments(install_dir)],
        cwd=str(installer.parent),
        creationflags=flags,
        close_fds=True,
    )


def cleanup_downloads() -> int:
    """Delete installers left from a previous update; returns how many."""
    folder = download_dir()
    removed = 0
    if not folder.is_dir():
        return 0
    for path in folder.iterdir():
        try:
            if path.is_file():
                path.unlink()
                removed += 1
        except OSError:
            continue
    try:
        folder.rmdir()
    except OSError:
        pass
    return removed
