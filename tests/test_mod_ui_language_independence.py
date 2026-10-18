# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — the nine interface languages are independent from translation languages.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ui_mod.languages import all_languages

UI_CODES = ["tr", "en", "de", "fr", "es", "ru", "fa", "zh-CN", "ja"]
EXPECTED_ENGLISH_NAME = {
    "es": "inglés", "en": "English", "de": "Englisch", "fr": "anglais", "ru": "английский",
    "tr": "İngilizce", "fa": "انگلیسی", "ja": "英語", "zh-CN": "英语",
}


def _locale(code):
    return json.loads(Path("locales", f"{code}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("code", UI_CODES)
def test_locale_names_every_translation_language(code):
    names = _locale(code)["language_names"]
    renpy_ids = {lang.renpy for lang in all_languages()}
    assert set(names) == renpy_ids and len(renpy_ids) == 135
    assert all(isinstance(v, str) and v.strip() for v in names.values())
    assert names["english"] == EXPECTED_ENGLISH_NAME[code]


def test_all_locales_share_the_same_keys_including_mod_texts():
    keysets = {code: set(_locale(code)) for code in UI_CODES}
    reference = keysets["en"]
    assert all(keys == reference for keys in keysets.values())
    assert sum(1 for key in reference if key.startswith("mod_")) >= 20


def test_ui_language_codes_never_collide_with_translation_folders():
    # UI uses ISO codes (tl folders use Ren'Py ids such as "spanish").
    folders = {lang.renpy for lang in all_languages()}
    assert not folders & set(UI_CODES)


def test_mod_package_does_not_read_the_interface_language():
    for path in Path("src/ui_mod").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "ui_language" not in text and "get_ui_text" not in text, path


@pytest.mark.parametrize("code", UI_CODES)
def test_switching_interface_language_keeps_translation_settings(tmp_path, monkeypatch, code):
    import src.utils.path_manager as path_manager
    monkeypatch.setattr(path_manager, "get_data_path", lambda: tmp_path)
    from src.utils.config import ConfigManager
    import importlib.util
    # Load the Qt-free module directly: src/backend/__init__ imports the Qt backend.
    spec = importlib.util.spec_from_file_location("_ln_settings_backend", "src/backend/settings_backend.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    SettingsBackend = module.SettingsBackend

    config = ConfigManager()
    config.translation_settings.source_language = "portuguese"
    config.translation_settings.target_language = "polish"
    backend = SettingsBackend(config, translation_manager=None)
    backend.set_ui_language(code)
    assert config.app_settings.ui_language == code
    assert config.translation_settings.source_language == "portuguese"
    assert config.translation_settings.target_language == "polish"
    reloaded = ConfigManager()
    assert reloaded.app_settings.ui_language == code
    assert reloaded.translation_settings.target_language == "polish"
    assert reloaded.get_ui_text("language_names.english") == EXPECTED_ENGLISH_NAME[code]
