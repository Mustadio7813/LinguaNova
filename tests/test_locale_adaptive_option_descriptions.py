# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression checks for localized option-description sizing."""

from pathlib import Path


def test_ui_settings_card_uses_content_height():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    block = qml[qml.index("id: cardUiSettings"):qml.index("id: cardOutputSettings")]
    assert "Layout.preferredHeight: uiSettingsCol.implicitHeight + 44" in block
    assert "Layout.preferredHeight: 160" not in block


def test_notification_description_stays_readable_and_wraps():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    pos = qml.index('getTextWithDefault("enable_desktop_notifications_tooltip"')
    block = qml[pos:pos + 600]
    assert "font.pixelSize: 11" in block
    assert "wrapMode: Text.WordWrap" in block
    assert "lineHeight: 1.15" in block


def test_header_identifies_the_product_as_renpy_translator():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert 'getTextWithDefault("nav_workspace_label", "Ren\\\'Py Translator")' in qml
