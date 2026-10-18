# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression checks for the active-translation configuration lock."""

from pathlib import Path


def test_backend_has_hard_guards():
    source = Path("src/backend/app_backend.py").read_text(encoding="utf-8")
    for method in ("setProjectPath", "setSourceLanguage", "setTargetLanguage", "setSelectedEngine"):
        pos = source.index(f"def {method}")
        assert "if self._is_translating:" in source[pos:pos + 1600]


def test_qml_locks_project_and_route_cards():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    for marker in ("id: cardProject", "id: cardEngine", "id: btnBrowseFolder", "id: btnBrowseExe"):
        pos = qml.index(marker)
        assert "enabled: !isTranslating" in qml[pos:pos + 600]


def test_stop_button_remains_available_during_run():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    pos = qml.index("id: startButton")
    block = qml[pos:pos + 2200]
    assert "appBackend.stopTranslation()" in block
    assert "ln_stop_translation" in block
