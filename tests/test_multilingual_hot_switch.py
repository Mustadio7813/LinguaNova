# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline regressions for preserving languages and switching runtime dictionaries.

Python init blocks execute unchanged against small Ren'Py stand-ins. The tests
do not pretend to render a game, emulate a save file or translate via a server.
"""

import itertools
import json
from pathlib import Path
import re
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.core.language_menu_template import (
    RESOURCE_FILTER_FILE, install_resource_filter, render_language_picker,
)
from src.core.pipeline.orchestrator import TranslationPipeline
from src.core.pipeline.saving import create_language_init_file
from src.core.runtime_hook_template import render_runtime_hook
from src.utils.config import ConfigManager


LANGUAGES = {
    "english": "Inventory",
    "spanish": "Inventario",
    "french": "Inventaire",
    "portuguese": "Inventário",
    "russian": "Инвентарь",
}


def python_blocks(script):
    """Only init-python suites, keeping their real declaration order."""
    lines = script.splitlines(keepends=True)
    blocks = []
    index = 0
    while index < len(lines):
        if re.match(r"^init(?:\s+-?\d+)?\s+python\s*:", lines[index]):
            index += 1
            body = []
            while index < len(lines) and (not lines[index].strip() or lines[index][0].isspace()):
                body.append(lines[index])
                index += 1
            blocks.append(textwrap.dedent("".join(body)))
        else:
            index += 1
    return blocks


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.path_manager.get_data_path", lambda: tmp_path / "appdata")
    return ConfigManager()


def language_folder(game, code):
    folder = game / "tl" / code
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "script.rpy").write_text(
        f'translate {code} strings:\n    old "Inventory"\n    new "{LANGUAGES.get(code, code)}"\n',
        encoding="utf-8",
    )
    return folder


def picker_env(script, known, *, mod=False, modern=True):
    config = SimpleNamespace(overlay_screens=[])
    if modern:
        config.always_shown_screens = []
    namespace = {
        "config": config,
        "persistent": SimpleNamespace(),
        "renpy": SimpleNamespace(known_languages=lambda: known, has_screen=lambda name: mod),
        "main_menu": False, "_menu": False,
    }
    for body in python_blocks(script):
        exec(compile(body, "language_picker", "exec"), namespace)
    return namespace


def test_successive_targets_keep_every_previous_native_option(tmp_path, config):
    game = tmp_path / "game"
    game.mkdir()
    source = game / "screens.rpy"
    source.write_text(
        'screen preferences():\n    vbox:\n'
        '        textbutton "English" action Language(None)\n'
        '        textbutton "Deutsch" action Language("german")\n', encoding="utf-8",
    )
    original = source.read_bytes()
    installed = []
    for code in ("spanish", "portuguese", "french", "russian", "english"):
        language_folder(game, code)
        installed.append(code)
        result = create_language_init_file(str(game), code, config, lambda *args: None)
        helper = Path(result["output"])
        assert result["status"] == "integrated"
        assert set(result["languages"]) == set(installed)
        text = helper.read_text(encoding="utf-8-sig")
        for previous in installed:
            assert f'Language("{previous}")' in text
        assert source.read_bytes() == original
        env = picker_env(text, installed)
        assert {code for code, _ in env["_lntl_languages"]()} == set(installed)


def test_regeneration_is_independent_of_last_target_and_keeps_bytecode_if_unchanged(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    language_folder(game, "portuguese")
    first = create_language_init_file(str(game), "spanish", config, lambda *args: None)
    path = Path(first["output"])
    original = path.read_bytes()
    bytecode = Path(str(path) + "c")
    bytecode.write_bytes(b"existing compiled helper")
    with patch("src.utils.encoding.save_text_safely") as writer:
        second = create_language_init_file(str(game), "portuguese", config, lambda *args: None)
    assert second["changed"] is False
    writer.assert_not_called()
    assert bytecode.is_file()
    assert path.read_bytes() == original


def test_failed_update_keeps_previous_selector_and_bytecode(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    first = create_language_init_file(str(game), "spanish", config, lambda *args: None)
    path = Path(first["output"])
    original = path.read_bytes()
    bytecode = Path(str(path) + "c")
    bytecode.write_bytes(b"previous helper")
    language_folder(game, "portuguese")
    messages = []
    with patch("src.utils.encoding.save_text_safely", return_value=False):
        result = create_language_init_file(str(game), "portuguese", config, lambda *args: messages.append(args))
    assert result["status"] == "error"
    assert path.read_bytes() == original
    assert bytecode.read_bytes() == b"previous helper"
    assert all(level == "error" for level, _ in messages)


def test_missing_write_is_reported_as_error_to_the_pipeline(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    stub = SimpleNamespace(config=config, target_language="spanish", log_message=SimpleNamespace(emit=lambda *args: None))
    with patch("src.utils.encoding.save_text_safely", return_value=False):
        with pytest.raises(OSError, match="selector"):
            TranslationPipeline._create_language_init_file(stub, str(game))
    assert not (game / "zzz_linguanova_language_menu.rpy").exists()


def test_already_existing_native_language_still_has_gameplay_hotkey(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    (game / "screens.rpy").write_text(
        'screen preferences():\n    textbutton "Español" action Language("spanish")\n', encoding="utf-8",
    )
    result = create_language_init_file(str(game), "spanish", config, lambda *args: None)
    assert result["status"] == "already_present"
    assert Path(result["output"]).is_file()
    env = picker_env(Path(result["output"]).read_text(encoding="utf-8-sig"), ["spanish"])
    assert "lntl_language_button" in env["config"].always_shown_screens
    assert env["_lntl_show_button"] is False


def test_large_picker_lists_only_loaded_languages_and_defers_to_mod():
    known = set(LANGUAGES) | {f"language_{i}" for i in range(40)}
    script = render_language_picker({"not_installed": "Unavailable"})
    env = picker_env(script, known | {None})
    assert {code for code, _ in env["_lntl_languages"]()} == known
    assert dict(env["_lntl_languages"]())["russian"] == "Русский"
    assert 'scrollbars "vertical"' in script
    assert 'action Language(None)' in script
    assert 'action Language(_lntl_code)' in script
    assert 'key "shift_K_l" action ToggleScreen' in script
    # MOD owns its hotkey/panel when installed; the core picker adds no button.
    assert picker_env(script, known, mod=True)["_lntl_button_visible"]() is False
    older = picker_env(script, known, modern=False)
    assert older["config"].overlay_screens == ["lntl_language_button"]


def test_font_resources_are_hidden_from_original_game_menu_too():
    known = {"spanish", "portuguese", "russian", "linguanova_fonts", "linguanova_font", "linguanova_mod_fonts"}
    env = picker_env(render_language_picker({}), known)
    assert env["renpy"].known_languages() == {"spanish", "portuguese", "russian"}
    assert {code for code, _ in env["_lntl_languages"]()} == {"spanish", "portuguese", "russian"}


@pytest.mark.parametrize("menu_enabled", [True, False])
def test_translator_installs_font_protection_automatically_even_without_menu(tmp_path, config, menu_enabled):
    game = tmp_path / "game"
    language_folder(game, "russian")
    legacy_font = game / "tl" / "linguanova_fonts" / "Cyrillic.ttf"
    legacy_font.parent.mkdir()
    legacy_font.write_bytes(b"existing Russian font asset")
    font_hook = game / "zzz_linguanova_font.rpy"
    font_hook.write_text('translate russian style default:\n    font "tl/linguanova_fonts/Cyrillic.ttf"\n', encoding="utf-8")
    original_hook = font_hook.read_bytes()
    config.translation_settings.activate_language_on_launch = menu_enabled

    result = create_language_init_file(str(game), "russian", config, lambda *args: None)

    protection = game / RESOURCE_FILTER_FILE
    assert result["status"] != "error"
    assert Path(result["resource_filter"]) == protection
    assert protection.is_file()  # No user copy and no font download are involved.
    env = picker_env(protection.read_text(encoding="utf-8-sig"), {"russian", "linguanova_fonts"})
    assert env["renpy"].known_languages() == {"russian"}
    assert legacy_font.read_bytes() == b"existing Russian font asset"
    assert font_hook.read_bytes() == original_hook
    assert (game / "zzz_linguanova_language_menu.rpy").exists() is menu_enabled
    from src.core.constants import is_linguanova_generated_script
    assert is_linguanova_generated_script(protection.name)


def test_font_protection_keeps_working_file_on_failure_and_is_idempotent(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    protection = game / RESOURCE_FILTER_FILE
    protection.write_text("# older managed filter\n", encoding="utf-8")
    bytecode = Path(str(protection) + "c")
    bytecode.write_bytes(b"previous compiled filter")
    with patch("src.utils.encoding.save_text_safely", return_value=False):
        with pytest.raises(OSError):
            install_resource_filter(str(game))
    assert protection.read_text(encoding="utf-8") == "# older managed filter\n"
    assert bytecode.read_bytes() == b"previous compiled filter"
    install_resource_filter(str(game))
    assert not bytecode.exists()
    bytecode.write_bytes(b"current compiled filter")
    with patch("src.utils.encoding.save_text_safely") as writer:
        install_resource_filter(str(game))
    writer.assert_not_called()
    assert bytecode.read_bytes() == b"current compiled filter"


def test_automatic_filter_and_embedded_menu_filter_can_coexist():
    from src.core.language_menu_template import render_resource_filter
    env = picker_env(render_resource_filter() + "\n" + render_language_picker({"russian": "Русский"}),
                     {"russian", "linguanova_fonts"})
    assert env["renpy"].known_languages() == {"russian"}
    assert env["_lntl_languages"]() == [("russian", "Русский")]


def test_native_menu_with_only_original_gets_matching_siblings(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    language_folder(game, "portuguese")
    source = game / "screens.rpy"
    source.write_text(
        'screen preferences():\n    vbox:\n        style_prefix "radio"\n'
        '        label _("Language")\n'
        '        textbutton _("English"):\n'
        '            action Language(None)\n'
        '            selected (_preferences.language is None)\n', encoding="utf-8",
    )
    original = source.read_bytes()
    result = create_language_init_file(str(game), "spanish", config, lambda *args: None)
    text = Path(result["output"]).read_text(encoding="utf-8-sig")
    assert result["status"] == "integrated"
    assert 'Language("spanish")' in text and 'Language("portuguese")' in text
    assert "selected (_preferences.language == 'spanish')" in text
    assert 'style_prefix "radio"' in text
    assert source.read_bytes() == original


def test_unindented_comments_do_not_truncate_native_screen(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    source = game / "screens.rpy"
    source.write_text(
        'screen preferences():\n    vbox:\n        text "Preferences"\n'
        '# A column-zero comment can legally occur inside a screen.\n'
        '        textbutton "English" action Language(None)\n'
        '        text "Keep the rest of the screen"\n\n'
        'screen unrelated():\n    text "Unrelated"\n', encoding="utf-8",
    )
    result = create_language_init_file(str(game), "spanish", config, lambda *args: None)
    text = Path(result["output"]).read_text(encoding="utf-8-sig")
    assert result["status"] == "integrated"
    assert 'text "Keep the rest of the screen"' in text
    assert 'screen unrelated()' not in text


def test_existing_automatic_native_menu_is_not_duplicated(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    source = game / "screens.rpy"
    source.write_text(
        'screen preferences():\n    vbox:\n'
        '        textbutton "English" action Language(None)\n'
        '        for language in renpy.known_languages():\n'
        '            textbutton language action Language(language)\n', encoding="utf-8",
    )
    result = create_language_init_file(str(game), "spanish", config, lambda *args: None)
    text = Path(result["output"]).read_text(encoding="utf-8-sig")
    assert result["status"] == "already_present"
    assert 'screen preferences()' not in text
    assert picker_env(text, {"spanish", "linguanova_fonts"})["renpy"].known_languages() == {"spanish"}


def test_standard_preferences_without_language_section_gets_native_radio_group(tmp_path, config):
    game = tmp_path / "game"
    language_folder(game, "spanish")
    source = game / "screens.rpy"
    source.write_text(
        'screen preferences():\n    tag menu\n'
        '    use game_menu(_("Preferences"), scroll="viewport"):\n'
        '        vbox:\n            hbox:\n                box_wrap True\n'
        '                vbox:\n                    style_prefix "radio"\n'
        '                    label _("Display")\n'
        '                    textbutton _("Window") action Preference("display", "window")\n', encoding="utf-8",
    )
    original = source.read_bytes()
    result = create_language_init_file(str(game), "spanish", config, lambda *args: None)
    text = Path(result["output"]).read_text(encoding="utf-8-sig")
    assert result["status"] == "integrated"
    assert '                use lntl_language_preferences\n' in text
    assert 'screen lntl_language_preferences()' in text
    assert picker_env(text, {"spanish"})["_lntl_show_button"] is False
    assert source.read_bytes() == original


def runtime_env(game, language, *, shadow_dict=False):
    preferences = SimpleNamespace(language=language)
    config = SimpleNamespace(
        gamedir=str(game), say_menu_text_filter=None, replace_text=None,
        start_interact_callbacks=[], interact_callbacks=[], rtl=False,
    )
    env = {
        "_preferences": preferences, "config": config, "style": SimpleNamespace(),
        "renpy": SimpleNamespace(config=SimpleNamespace(searchpath=[]), android=False),
    }
    if shadow_dict:
        # Ren'Py's store aliases dict to its rollback-aware dict subclass;
        # json.loads still returns the built-in type, not that subclass.
        env["dict"] = type("RollbackDict", (dict,), {})
    for body in python_blocks(render_runtime_hook("russian", thread_enabled=False)):
        exec(compile(body, "runtime_hook", "exec"), env)
    return env


def test_json_loading_accepts_builtin_dict_when_renpy_shadows_dict(tmp_path):
    game = tmp_path / "game"
    folder = language_folder(game, "spanish")
    (folder / "strings.json").write_text('{"translations":{"Source label":"Español"}}', encoding="utf-8")
    env = runtime_env(game, "spanish", shadow_dict=True)
    assert env["config"].replace_text("Source label") == "Español"


@pytest.mark.parametrize("source,target", list(itertools.permutations(LANGUAGES, 2)))
@pytest.mark.parametrize("wrapped", [False, True])
def test_all_twenty_directions_and_original_clear_old_runtime_data(tmp_path, source, target, wrapped):
    game = tmp_path / "game"
    for code, text in LANGUAGES.items():
        folder = language_folder(game, code)
        # English can have UI translations too; use a distinct key for the test.
        mapping = {"Source label": text, f"Only {code}": "unique " + text}
        payload = {"translations": mapping, "dynamic": {}} if wrapped else mapping
        (folder / "strings.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    env = runtime_env(game, source)
    assert env["config"].replace_text("Source label") == LANGUAGES[source]
    env["_rl_alias_cache"]["obsolete"] = LANGUAGES[source]
    env["_rl_miss_set"].add("Source label")
    env["_preferences"].language = target
    for callback in env["config"].interact_callbacks:
        callback()
    assert env["_rl_alias_cache"] == {}
    assert "Source label" not in env["_rl_miss_set"]
    assert env["config"].replace_text("Source label") == LANGUAGES[target]
    assert env["config"].say_menu_text_filter("Source label") == LANGUAGES[target]
    assert env["config"].say_menu_text_filter("Source label") == LANGUAGES[target]
    assert env["config"].replace_text(f"Only {source}") == f"Only {source}"
    env["_preferences"].language = None
    # Also synchronize before a lookup, without waiting for a callback or timer.
    assert env["config"].replace_text("Source label") == "Source label"
    assert env["config"].say_menu_text_filter("Source label") == "Source label"
    assert env["_rl_translations"] == {}


@pytest.mark.parametrize("bad_data", [None, "{bad json", "[]", '{"translations": {}}'])
def test_missing_or_invalid_target_never_uses_previous_or_generation_language(tmp_path, bad_data):
    game = tmp_path / "game"
    folder = language_folder(game, "spanish")
    (folder / "strings.json").write_text('{"translations":{"Source label":"Español"}}', encoding="utf-8")
    env = runtime_env(game, "spanish")
    assert env["config"].replace_text("Source label") == "Español"
    if bad_data is not None:
        folder = language_folder(game, "russian")
        (folder / "strings.json").write_text(bad_data, encoding="utf-8")
    env["_preferences"].language = "russian"
    assert env["config"].replace_text("Source label") == "Source label"
    assert env["_rl_translations"] == {}
