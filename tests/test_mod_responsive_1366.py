# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression checks for MOD responsiveness on 1366x768-class displays."""
from pathlib import Path


def _mod_block():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    start = qml.index("id: pageMod")
    end = qml.index("// ── Toast", start)
    return qml[start:end]


def test_mod_has_explicit_vertical_scroll_range():
    block = _mod_block()
    assert "id: viewMod" in block
    assert "id: modContent" in block
    assert "contentWidth: availableWidth" in block
    assert "contentHeight: modContent.implicitHeight" in block
    assert "ScrollBar.vertical.policy: root.needsPageScroll" in block


def test_mod_compacts_info_cards_at_low_height():
    block = _mod_block()
    assert "id: modInfoGrid" in block
    assert "columns: root.compactHeight && !root.compactWidth ? 3 : 1" in block
    assert "anchors.margins: root.compactHeight ? 11 : 20" in block


def test_mod_actions_remain_responsive():
    block = _mod_block()
    assert "anchors.margins: root.compactHeight ? 12 : 20" in block
    assert "Layout.preferredHeight: root.responsiveButtonHeight" in block
    assert "columns: root.narrowWidth ? 1 : 3" in block
