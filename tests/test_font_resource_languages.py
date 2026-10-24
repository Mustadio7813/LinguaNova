# SPDX-License-Identifier: GPL-3.0-or-later
"""Font files must not create phantom languages or replace previous font blocks."""

from pathlib import Path

from src.core.language_menu_template import RESOURCE_FILTER_FILE, installed_language_folders
from src.tools.font_injector import inject_font


def test_font_assets_live_outside_tl_and_other_language_fonts_are_preserved(tmp_path, monkeypatch):
    game = tmp_path / "game"
    game.mkdir()

    def download(family, folder):
        name = family.replace(" ", "") + ".ttf"
        (folder / name).write_bytes(b"offline font fixture")
        return True, name

    monkeypatch.setattr("src.tools.font_injector._download_font", download)
    assert inject_font(str(game), "russian")["success"]
    assert (game / RESOURCE_FILTER_FILE).is_file()
    assert not (game / "tl" / "linguanova_fonts").exists()
    helper = game / "zzz_linguanova_font.rpy"
    text = helper.read_text(encoding="utf-8")
    assert '"linguanova_fonts/NotoSans.ttf"' in text
    assert inject_font(str(game), "spanish")["success"]
    text = helper.read_text(encoding="utf-8")
    assert "translate russian python:" in text
    assert "translate spanish python:" in text
    assert text.count("def linguanova_get_font_hook") == 1
    assert inject_font(str(game), "russian")["success"]
    assert helper.read_text(encoding="utf-8").count("translate russian python:") == 1


def test_font_utility_protects_legacy_resources_without_menu_generation(tmp_path, monkeypatch):
    game = tmp_path / "game"
    legacy = game / "tl" / "linguanova_fonts" / "Cyrillic.ttf"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"existing Cyrillic font")
    helper = game / "zzz_linguanova_font.rpy"
    helper.write_text(
        '# managed by linguanova_get_font_hook\n'
        'translate russian python:\n'
        '    renpy.store.linguanova_fonts["russian"] = {"Default": "tl/linguanova_fonts/Cyrillic.ttf"}\n',
        encoding="utf-8",
    )
    def download(family, folder):
        (folder / "Latin.ttf").write_bytes(b"new Latin font")
        return True, "Latin.ttf"
    monkeypatch.setattr("src.tools.font_injector._download_font", download)

    result = inject_font(str(game), "spanish")

    assert result["success"]
    assert (game / RESOURCE_FILTER_FILE).is_file()
    assert not (game / "zzz_linguanova_language_menu.rpy").exists()
    assert legacy.read_bytes() == b"existing Cyrillic font"
    assert '"tl/linguanova_fonts/Cyrillic.ttf"' in helper.read_text(encoding="utf-8")
    assert '"linguanova_fonts/Latin.ttf"' in helper.read_text(encoding="utf-8")


def test_reserved_resource_folders_never_enter_generation_language_list(tmp_path):
    game = tmp_path / "game"
    for code in ("russian", "linguanova_fonts", "linguanova_font", "linguanova_mod_fonts"):
        folder = game / "tl" / code
        folder.mkdir(parents=True)
        (folder / "helper.rpy").write_text("# resource helper\n", encoding="utf-8")
    assert installed_language_folders(str(game)) == ["russian"]
