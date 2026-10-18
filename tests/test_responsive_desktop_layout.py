# SPDX-License-Identifier: GPL-3.0-or-later
"""Static regression checks for LinguaNova's responsive desktop layout."""

from pathlib import Path


def test_main_qml_has_global_responsive_breakpoints():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    for marker in (
        "readonly property bool compactHeight",
        "readonly property bool compactWidth",
        "readonly property bool narrowWidth",
        "readonly property int responsivePageMargin",
        "minimumWidth: Math.min(760, Screen.desktopAvailableWidth)",
        "minimumHeight: Math.min(560, Screen.desktopAvailableHeight)",
    ):
        assert marker in qml


def test_long_workspaces_have_explicit_vertical_scroll_ranges():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    for marker in (
        "contentHeight: dashboardContent.implicitHeight",
        "contentHeight: settingsContent.implicitHeight",
        "contentHeight: toolboxContent.implicitHeight",
        "contentHeight: glossaryContent.implicitHeight",
        "contentHeight: modContent.implicitHeight",
        "ScrollBar.vertical.policy:",
    ):
        assert marker in qml


def test_toolbox_has_responsive_column_count_and_compact_cards():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert "columns: viewToolbox.availableWidth < 900 ? 1 : 2" in qml
    assert "root.responsiveCardPadding" in qml
    assert "root.responsiveButtonHeight" in qml


def test_launcher_opens_main_window_maximized():
    run_py = Path("run.py").read_text(encoding="utf-8")
    assert "root_window.showMaximized()" in run_py
