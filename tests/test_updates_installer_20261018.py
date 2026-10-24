# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Automatic update, Windows installer and user interface languages (2026-10-18)."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from src.utils import auto_updater
from src.utils import ui_language_generator as gen

REPO = "Mustadio7813/LinguaNova"
BASE = f"https://github.com/{REPO}/releases/download/v1.1.1/"


def _assets(*names):
    return [{"name": n, "url": BASE + n, "size": 10} for n in names]


# ── auto_updater ─────────────────────────────────────────────────────────

def test_plan_needs_installer_checksums_and_an_installed_build(tmp_path):
    assets = _assets("LinguaNova_Setup_1.1.1.exe", "LinguaNova-Windows-x64.zip", "SHA256SUMS.txt")
    plan = auto_updater.plan_update(assets, REPO, install_dir=tmp_path)
    assert plan and plan.installer_name == "LinguaNova_Setup_1.1.1.exe" and plan.install_dir == tmp_path
    # Not installed (portable / source / other OS): only the release page.
    with mock.patch.object(auto_updater, "current_install_dir", return_value=None):
        assert auto_updater.plan_update(assets, REPO) is None
    # No checksums -> never install blindly.
    assert auto_updater.plan_update(_assets("LinguaNova_Setup_1.1.1.exe"), REPO, install_dir=tmp_path) is None
    # Files hosted anywhere else are refused.
    foreign = [{"name": "LinguaNova_Setup_1.1.1.exe", "url": "https://example.com/x.exe"},
               {"name": "SHA256SUMS.txt", "url": BASE + "SHA256SUMS.txt"}]
    assert auto_updater.plan_update(foreign, REPO, install_dir=tmp_path) is None


def test_installed_build_is_detected_by_the_installer_marker(tmp_path):
    exe = tmp_path / "LinguaNova.exe"
    exe.write_bytes(b"")
    with mock.patch.object(auto_updater.sys, "platform", "win32"), \
            mock.patch.object(auto_updater.sys, "frozen", True, create=True), \
            mock.patch.object(auto_updater.sys, "executable", str(exe)):
        assert auto_updater.current_install_dir() is None
        (tmp_path / auto_updater.INSTALL_MARKER).write_text("{}", encoding="utf-8")
        assert auto_updater.current_install_dir() == tmp_path.resolve()


def test_expected_sha256_reads_sha256sum_format():
    h = "a" * 64
    text = f"{'b' * 64}  LinguaNova-Windows-x64.zip\n{h} *LinguaNova_Setup_1.1.1.exe\n"
    assert auto_updater.expected_sha256(text, "LinguaNova_Setup_1.1.1.exe") == h
    assert auto_updater.expected_sha256(text, "missing.exe") is None


class _Resp:
    def __init__(self, body: bytes, status=200):
        self.status_code = status
        self._body = body
        self.text = body.decode("utf-8", "replace")
        self.headers = {"Content-Length": str(len(body))}

    def iter_content(self, size):
        for i in range(0, len(self._body), 3):
            yield self._body[i:i + 3]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_requests(installer: bytes, sums: str):
    def get(url, **kwargs):
        if url.endswith("SHA256SUMS.txt"):
            return _Resp(sums.encode())
        return _Resp(installer)
    return SimpleNamespace(get=get)


def test_download_is_verified_before_it_can_run(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_updater, "download_dir", lambda: tmp_path / "dl")
    payload = b"installer-bytes"
    good = hashlib.sha256(payload).hexdigest()
    plan = auto_updater.plan_update(_assets("LinguaNova_Setup_1.1.1.exe", "SHA256SUMS.txt"), REPO, install_dir=tmp_path)
    seen = []
    with mock.patch.dict("sys.modules", {"requests": _fake_requests(payload, f"{good}  LinguaNova_Setup_1.1.1.exe\n")}):
        path = auto_updater.download_update(plan, lambda d, t: seen.append((d, t)))
    assert path.read_bytes() == payload and seen[-1] == (len(payload), len(payload))

    # A tampered or damaged file is deleted and never returned.
    with mock.patch.dict("sys.modules", {"requests": _fake_requests(b"evil", f"{good}  LinguaNova_Setup_1.1.1.exe\n")}):
        with pytest.raises(auto_updater.UpdateError, match="SHA-256"):
            auto_updater.download_update(plan, lambda d, t: None)
    assert not (tmp_path / "dl" / "LinguaNova_Setup_1.1.1.exe").exists()

    # Not listed in SHA256SUMS.txt -> refused before downloading.
    with mock.patch.dict("sys.modules", {"requests": _fake_requests(payload, f"{good}  other.exe\n")}):
        with pytest.raises(auto_updater.UpdateError, match="not listed"):
            auto_updater.download_update(plan, lambda d, t: None)


def test_cancel_stops_the_download_and_leaves_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_updater, "download_dir", lambda: tmp_path / "dl")
    payload = b"x" * 30
    good = hashlib.sha256(payload).hexdigest()
    plan = auto_updater.plan_update(_assets("LinguaNova_Setup_1.1.1.exe", "SHA256SUMS.txt"), REPO, install_dir=tmp_path)
    cancel = threading.Event()
    cancel.set()
    with mock.patch.dict("sys.modules", {"requests": _fake_requests(payload, f"{good}  LinguaNova_Setup_1.1.1.exe\n")}):
        with pytest.raises(auto_updater.UpdateError, match="cancelled"):
            auto_updater.download_update(plan, lambda d, t: None, cancel)
    assert list((tmp_path / "dl").iterdir()) == []


def test_installer_runs_silently_in_the_current_folder_and_reopens(tmp_path):
    args = auto_updater.installer_arguments(Path("D:/LinguaNova"))
    assert "/VERYSILENT" in args and "/LNUPDATE" in args
    assert any(a.startswith("/DIR=") and "LinguaNova" in a for a in args)


def test_cleanup_removes_downloaded_installers(tmp_path, monkeypatch):
    folder = tmp_path / "LinguaNova_update"
    folder.mkdir()
    (folder / "LinguaNova_Setup_1.1.1.exe").write_bytes(b"x")
    monkeypatch.setattr(auto_updater, "download_dir", lambda: folder)
    assert auto_updater.cleanup_downloads() == 1
    assert not folder.exists()


def test_update_check_returns_release_assets():
    from src.utils import update_checker

    payload = {
        "tag_name": "v1.1.1",
        "html_url": "https://github.com/x/y/releases/tag/v1.1.1",
        "assets": [{"name": "SHA256SUMS.txt", "browser_download_url": BASE + "SHA256SUMS.txt", "size": 5}],
    }
    resp = SimpleNamespace(status_code=200, json=lambda: payload)
    with mock.patch.dict("os.environ", {"LINGUANOVA_UPDATE_REPO": "x/y"}), \
            mock.patch("requests.get", return_value=resp):
        result = update_checker.check_for_updates("1.1.0")
    assert result.update_available and result.assets[0]["name"] == "SHA256SUMS.txt"


# ── backend wiring ──────────────────────────────────────────────────────

def _backend_stub():
    events = []

    def sig(name):
        return SimpleNamespace(emit=lambda *a: events.append((name, a)))

    stub = SimpleNamespace(
        _version="1.1.0",
        config=SimpleNamespace(get_ui_text=lambda key, default: default),
        logger=mock.MagicMock(),
        _t=lambda key, default, **kw: default,
        _update_plan=None,
        _update_cancel=threading.Event(),
        _update_downloading=True,
    )
    for name in ("logMessage", "updateCheckFinished", "updateAvailable", "autoUpdateChanged",
                 "updateDownloadProgress", "updateDownloadFinished", "updateInstallerLaunched"):
        setattr(stub, name, sig(name))
    return stub, events


def test_backend_offers_automatic_update_only_with_a_plan(tmp_path):
    from src.backend.app_backend import AppBackend
    from src.utils.update_checker import UpdateCheckResult

    stub, events = _backend_stub()
    found = UpdateCheckResult("1.1.0", "v1.1.1", True, "url",
                              assets=_assets("LinguaNova_Setup_1.1.1.exe", "SHA256SUMS.txt"))
    with mock.patch("src.utils.update_checker.check_for_updates", return_value=found), \
            mock.patch("src.utils.update_checker.get_update_repo", return_value=REPO), \
            mock.patch.object(auto_updater, "current_install_dir", return_value=tmp_path):
        AppBackend._check_updates_thread(stub, manual=True)
    assert stub._update_plan is not None
    assert ("updateAvailable", ("1.1.0", "v1.1.1", "url")) in events


def test_backend_installs_then_quits_or_reports_the_failure(tmp_path):
    from src.backend.app_backend import AppBackend

    stub, events = _backend_stub()
    plan = auto_updater.UpdatePlan("LinguaNova_Setup_1.1.1.exe", BASE, 1, BASE, tmp_path)
    with mock.patch.object(auto_updater, "download_update", return_value=tmp_path / "s.exe"), \
            mock.patch.object(auto_updater, "launch_installer") as launch:
        AppBackend._auto_update_thread(stub, plan)
    launch.assert_called_once_with(tmp_path / "s.exe", tmp_path)
    assert ("updateInstallerLaunched", ()) in events and stub._update_downloading is False

    stub, events = _backend_stub()
    with mock.patch.object(auto_updater, "download_update", side_effect=auto_updater.UpdateError("SHA-256 mismatch")), \
            mock.patch.object(auto_updater, "launch_installer") as launch:
        AppBackend._auto_update_thread(stub, plan)
    launch.assert_not_called()
    finished = [a for n, a in events if n == "updateDownloadFinished"]
    assert finished and finished[0][0] is False and "SHA-256 mismatch" in finished[0][1]


# ── installer and release workflow ───────────────────────────────────────

ISS = Path("installer/LinguaNova.iss")


def _iss() -> str:
    return ISS.read_text(encoding="utf-8-sig")


def test_installer_is_per_user_on_an_internal_drive_folder():
    text = _iss()
    assert "PrivilegesRequired=lowest" in text
    assert "DisableDirPage=yes" in text and "UsePreviousAppDir=yes" in text
    assert ":\\LinguaNova'" in text                      # <drive>:\LinguaNova
    assert "DRIVE_FIXED = 3" in text and "InterfaceType = ''USB''" in text and "BusType = 7" in text
    assert "MinVersion=10.0" in text and "ArchitecturesAllowed=x64compatible" in text
    assert re.search(r"AppId=\{\{\{#MyAppIdGuid\}\}", text)


def test_installer_shortcuts_marker_and_update_restart():
    text = _iss()
    assert 'Name: "{autodesktop}\\{#MyAppName}"' in text and 'AppUserModelID: "{#MyAppUserModelID}"' in text
    assert '#define MyAppUserModelID "LinguaNova"' in text
    assert "SetCurrentProcessExplicitAppUserModelID(\"LinguaNova\")" in Path("run.py").read_text(encoding="utf-8")
    assert auto_updater.INSTALL_MARKER in text and '"installer_language"' in text
    assert "Check: IsAutoUpdate" in text and "/LNUPDATE" in text


def test_installer_has_nine_languages_with_every_custom_message():
    text = _iss()
    langs = re.findall(r'^Name: "([a-z]+)"; MessagesFile:', text, re.M)
    assert sorted(langs) == sorted(["english", "spanish", "german", "french", "japanese", "russian",
                                    "turkish", "chinesesimplified", "persian"])
    keys = {k for k in re.findall(r"^english\.(\w+)=", text, re.M)}
    assert {"DriveTitle", "DriveItem", "DriveNone", "TaskbarHint"} <= keys
    for lang in langs:
        assert {k for k in re.findall(rf"^{lang}\.(\w+)=", text, re.M)} == keys, lang
    for isl in ("ChineseSimplified.isl", "Farsi.isl"):
        assert (Path("installer/languages") / isl).is_file()
    # The installer language becomes the first interface language.
    for code in ("es", "de", "fr", "ja", "ru", "tr", "zh-CN", "fa"):
        assert f"Result := '{code}'" in text


def test_release_publishes_the_installer_and_its_checksum():
    wf = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "installer\\LinguaNova.iss" in wf and "LinguaNova_Setup_*.exe" in wf
    assert "sha256sum LinguaNova-* LinguaNova_Setup_*.exe > SHA256SUMS.txt" in wf
    assert auto_updater.INSTALLER_PATTERN.match("LinguaNova_Setup_1.1.0.exe")
    assert auto_updater.CHECKSUMS_NAME == "SHA256SUMS.txt"


def test_utilities_page_has_update_and_language_cards():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    tools = qml[qml.index("id: viewToolbox"):qml.index("SEKME 4: GLOSSARY")]
    assert "appBackend.checkForUpdates(true)" in tools
    assert "toolUpdatesStartupCheck" not in tools
    assert "appBackend.createUiLanguage(" in tools and "userLocalesFolderUrl()" in tools
    dialog = qml[qml.index("id: updateDialog"):qml.index("id: updateDialog") + 12000]
    assert "appBackend.startAutoUpdate()" in dialog and "ProgressBar" in dialog
    assert "function onUpdateInstallerLaunched()" in qml


def test_windows_launcher_bootstraps_pip_without_failing_ensurepip_first():
    launcher = Path("run.bat").read_text(encoding="utf-8")
    create_environment = launcher[
        launcher.index('if not exist "%VENV_PY%" ('):
        launcher.index(') else (\n    echo [1/4] Entorno virtual local encontrado.')
    ]
    assert "%PY_CMD% -m venv --without-pip \"%VENV_DIR%\"" in create_environment
    assert "%PY_CMD% -m pip --python \"%VENV_PY%\" install --upgrade pip" in create_environment
    assert "%PY_CMD% -m venv \"%VENV_DIR%\"" not in create_environment
    assert "-m ensurepip" not in launcher


# ── user interface languages ──────────────────────────────────────────────

def test_generator_never_sends_or_loses_placeholders():
    source = {"a": "🔍 Update check failed: {error}", "b": {"c": "Loaded %s files\nDone"}, "_x": "skip"}
    segments = gen.collect_segments(source)
    assert all("{" not in s and "%" not in s and "\n" not in s for s in segments)
    fake = {s: s.upper() for s in segments}
    data, done, missing = gen.build_language(source, fake, "qu", "Runa Simi")
    assert data["a"] == "🔍 UPDATE CHECK FAILED: {error}"
    assert data["b"]["c"] == "LOADED %s FILES\nDONE"
    assert data["_language_name"] == "Runa Simi" and "_x" not in data and (done, missing) == (2, 0)
    # A text whose pieces were not all translated stays in English (key left out).
    data, done, missing = gen.build_language(source, {"Update check failed:": "x"}, "qu", "Q")
    assert "b" not in data and missing == 1


def test_every_english_text_keeps_its_placeholders():
    en = json.loads(Path("locales/en.json").read_text(encoding="utf-8"))
    fake = {s: "«" + s + "»" for s in gen.collect_segments(en)}
    for path, text in gen.iter_strings(en):
        out = gen.rebuild(text, fake)
        assert sorted(gen.PROTECTED.findall(out)) == sorted(gen.PROTECTED.findall(text)), path


def test_only_five_built_in_ui_languages_are_selectable(tmp_path, monkeypatch):
    from src.utils.config import ConfigManager
    from src.backend.settings_backend import SettingsBackend

    monkeypatch.setenv("LINGUANOVA_PROJECT_ROOT", str(Path.cwd()))
    monkeypatch.setattr("src.utils.path_manager.get_data_path", lambda: tmp_path)
    user = tmp_path / "locales"
    user.mkdir()
    (user / "qu.json").write_text(json.dumps({"_language_name": "Runa Simi", "btn_check_updates": "Musuqchay"}),
                                  encoding="utf-8")
    (user / "es.json").write_text(json.dumps({"btn_check_updates": "Buscar ya"}), encoding="utf-8")
    (user / "bad name!.json").write_text("{}", encoding="utf-8")
    config = ConfigManager()
    config.app_settings.ui_language = "qu"
    assert config.get_ui_text("btn_check_updates") != "Musuqchay"
    config.app_settings.ui_language = "es"
    assert config.get_ui_text("btn_check_updates") == "Buscar ya"    # override of a built-in key
    assert config.get_ui_text("update_now_btn") == "Actualizar ahora"

    settings = SettingsBackend.__new__(SettingsBackend)
    settings.config = config
    settings.logger = mock.MagicMock()
    settings._emit = lambda *a: None
    codes = [x["code"] for x in settings.get_available_ui_languages()]
    assert codes == ["es", "en", "pt", "fr", "ru"]
    current_language = config.app_settings.ui_language
    with mock.patch.object(config, "save_config"):
        settings.set_ui_language("qu")
    assert config.app_settings.ui_language == current_language


def test_installer_language_is_used_on_first_run(tmp_path, monkeypatch):
    from src.utils import config as config_mod

    (tmp_path / "linguanova_installed.json").write_text(
        json.dumps({"installer_language": "pt"}), encoding="utf-8-sig")
    monkeypatch.setattr("src.utils.path_manager.get_app_dir", lambda: tmp_path)
    assert config_mod.installer_ui_language() == "pt"
    (tmp_path / "linguanova_installed.json").write_text(json.dumps({"installer_language": "xx"}), encoding="utf-8")
    assert config_mod.installer_ui_language() == ""


def test_update_is_refused_while_a_translation_runs(tmp_path):
    from src.backend.app_backend import AppBackend

    stub, events = _backend_stub()
    stub._update_plan = object()
    stub._update_downloading = False
    stub._is_translating = True
    stub._mod_running = False
    with mock.patch("threading.Thread") as thread:
        AppBackend.startAutoUpdate(stub)
    thread.assert_not_called()
    assert ("updateDownloadFinished", (False, "Finish or stop the current translation before updating.")) in events
