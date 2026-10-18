# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression checks for locale/content-aware page scrollbar behavior."""

from pathlib import Path


def test_main_qml_has_fit_first_1080p_mode():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert "readonly property bool fitFirstDesktop" in qml
    assert "Screen.desktopAvailableHeight >= 900" in qml
    assert "function needsPageScroll(contentHeight, viewportHeight)" in qml


def test_page_scrollbars_hide_when_content_fits():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    for page_id in ("viewDashboard", "viewSettings", "viewToolbox", "viewGlossary"):
        assert f"root.needsPageScroll({page_id}.contentHeight, {page_id}.availableHeight)" in qml
    assert "ScrollBar.AlwaysOff" in qml
    assert "ScrollBar.AsNeeded" in qml


def test_locale_behavior_is_content_based_not_spanish_specific():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    fn = qml[qml.index("function needsPageScroll"):qml.index("function needsPageScroll") + 220]
    assert "contentHeight" in fn and "viewportHeight" in fn
    assert "spanish" not in fn.lower()
