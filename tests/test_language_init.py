# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""Tests for native language-menu integration."""

from src.core.pipeline.saving import (
    create_language_init_file,
    remove_all_language_integration_files,
)
from src.utils.config import ConfigManager


def _game_with_direct_language_menu(tmp_path):
    game = tmp_path / "game"
    (game / "tl" / "spanish").mkdir(parents=True)
    (game / "tl" / "spanish" / "script.rpy").write_text(
        "translate spanish strings:\n", encoding="utf-8"
    )
    (game / "screens.rpy").write_text(
        """screen preferences():
    vbox:
        textbutton "English" action Language(None)
        textbutton "Deutsch" action Language("german")
        textbutton "Français" action Language("french")
        textbutton "Русский" action Language("russian")
""",
        encoding="utf-8",
    )
    return game


def test_menu_integration_adds_language_without_forcing(tmp_path):
    game = _game_with_direct_language_menu(tmp_path)
    result = create_language_init_file(
        str(game), "spanish", ConfigManager(), lambda *args: None
    )
    assert result["status"] == "integrated"
    helper = game / "zzz_linguanova_language_menu.rpy"
    assert helper.exists()
    content = helper.read_text(encoding="utf-8-sig")
    assert 'Language("spanish")' in content
    assert "Español" in content
    assert "define config.language" not in content
    assert "config.language =" not in content
    assert "config.start_callbacks" not in content
    assert "persistent.language" not in content


def test_integration_preserves_original_script(tmp_path):
    game = _game_with_direct_language_menu(tmp_path)
    original = (game / "screens.rpy").read_bytes()
    create_language_init_file(
        str(game), "spanish", ConfigManager(), lambda *args: None
    )
    assert (game / "screens.rpy").read_bytes() == original


def test_integration_can_be_disabled_and_removes_legacy_forcer(tmp_path):
    game = _game_with_direct_language_menu(tmp_path)
    (game / "zzz_spanish_language.rpy").write_text(
        'define config.language = "spanish"\n', encoding="utf-8-sig"
    )
    (game / "zzz_spanish_language.rpyc").write_bytes(b"compiled")
    config = ConfigManager()
    config.translation_settings.activate_language_on_launch = False
    result = create_language_init_file(
        str(game), "spanish", config, lambda *args: None
    )
    assert result["status"] == "disabled"
    assert not (game / "zzz_spanish_language.rpy").exists()
    assert not (game / "zzz_spanish_language.rpyc").exists()
    assert not (game / "zzz_linguanova_language_menu.rpy").exists()


def test_simple_data_driven_menu_is_extended_without_screen_override(tmp_path):
    game = tmp_path / "game"
    (game / "tl" / "spanish").mkdir(parents=True)
    (game / "tl" / "spanish" / "script.rpy").write_text(
        "translate spanish strings:\n", encoding="utf-8"
    )
    (game / "screens.rpy").write_text(
        """define languages = [
    ("English", None),
    ("Deutsch", "german"),
    ("Русский", "russian"),
]

screen language_settings():
    vbox:
        for label, code in languages:
            textbutton label action Language(code)
""",
        encoding="utf-8",
    )
    result = create_language_init_file(
        str(game), "spanish", ConfigManager(), lambda *args: None
    )
    assert result["status"] == "integrated"
    helper = (game / "zzz_linguanova_language_menu.rpy").read_text(
        encoding="utf-8-sig"
    )
    assert 'globals().get("languages"' in helper
    assert '"spanish"' in helper
    assert "Español" in helper
    assert "screen language_settings" not in helper
    assert "config.language" not in helper


def test_unsupported_custom_menu_is_not_modified(tmp_path):
    game = tmp_path / "game"
    (game / "tl" / "spanish").mkdir(parents=True)
    (game / "tl" / "spanish" / "script.rpy").write_text(
        "translate spanish strings:\n", encoding="utf-8"
    )
    (game / "screens.rpy").write_text(
        """screen custom_languages():
    vbox:
        imagebutton idle "en.png" action Language(None)
        imagebutton idle "de.png" action Language("german")
        imagebutton idle "ru.png" action Language("russian")
""",
        encoding="utf-8",
    )
    original = (game / "screens.rpy").read_bytes()
    result = create_language_init_file(
        str(game), "spanish", ConfigManager(), lambda *args: None
    )
    assert result["status"] == "not_found"
    assert not (game / "zzz_linguanova_language_menu.rpy").exists()
    assert (game / "screens.rpy").read_bytes() == original


def test_remove_integration_removes_new_and_legacy_files(tmp_path):
    game = _game_with_direct_language_menu(tmp_path)
    create_language_init_file(
        str(game), "spanish", ConfigManager(), lambda *args: None
    )
    (game / "zzz_old_language.rpy").write_text("# legacy\n", encoding="utf-8")
    assert remove_all_language_integration_files(str(game)) >= 2
    assert not list(game.glob("zzz_*language*.rpy*"))
