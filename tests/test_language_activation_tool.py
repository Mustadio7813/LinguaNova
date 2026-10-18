# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""Toolbox / CLI native language-menu integration."""

import sys
from unittest import mock
from src.core.pipeline.saving import list_tl_languages


def _game(tmp_path, *languages):
    game = tmp_path / "game"
    for lang in languages:
        (game / "tl" / lang).mkdir(parents=True)
        (game / "tl" / lang / "script.rpy").write_text(
            f"translate {lang} strings:\n", encoding="utf-8"
        )
    (game / "screens.rpy").write_text(
        """screen preferences():
    vbox:
        textbutton "English" action Language(None)
        textbutton "Deutsch" action Language("german")
        textbutton "Русский" action Language("russian")
""",
        encoding="utf-8",
    )
    (game / "tl" / ".diagnostics").mkdir(parents=True, exist_ok=True)
    (game / "tl" / "None").mkdir(parents=True, exist_ok=True)
    (game / "tl" / "linguanova_fonts").mkdir(parents=True, exist_ok=True)
    (game / "tl" / "linguanova_fonts" / "NotoSans-Regular.ttf").write_bytes(b"\0")
    return game


def test_lists_only_real_language_folders(tmp_path):
    game = _game(tmp_path, "russian", "Spanish")
    assert list_tl_languages(str(game)) == ["Spanish", "russian"]


def test_gui_tool_finds_game_dir_from_any_selected_path(tmp_path):
    from types import SimpleNamespace
    from src.backend.app_backend import AppBackend

    game = _game(tmp_path, "russian")
    exe = tmp_path / "Game.exe"
    exe.write_bytes(b"")
    for selected in (tmp_path, game, game / "tl" / "russian", exe):
        stub = SimpleNamespace(_project_path=str(selected))
        assert AppBackend._tool_game_dir(stub) == str(game), selected


def test_cli_activate_language_alias_now_integrates_menu(tmp_path):
    import src.cli_main as cli
    game = _game(tmp_path, "russian", "german")

    def run(*argv):
        with mock.patch.object(sys, "argv", ["cli", *argv]):
            return cli.main()

    assert run("activate-language", str(tmp_path)) == 1
    assert run("activate-language", str(tmp_path), "--lang", "de") == 0
    helper = game / "zzz_linguanova_language_menu.rpy"
    assert helper.exists()
    content = helper.read_text(encoding="utf-8-sig")
    assert 'Language("german")' in content
    assert "config.language" not in content
    assert run("activate-language", str(tmp_path), "--remove") == 0
    assert not helper.exists()
