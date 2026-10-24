# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — the five interface languages are independent from translation languages.
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.ui_mod.languages import all_languages

UI_CODES = ["en", "fr", "es", "pt", "ru"]
EXPECTED_ENGLISH_NAME = {
    "es": "inglés", "en": "English", "fr": "anglais", "ru": "английский", "pt": "Inglês",
}
EXPECTED_RECOMMENDED_BADGE = {
    "en": "💎 Recommended",
    "es": "💎 Recomendado",
    "fr": "💎 Recommandé",
    "pt": "💎 Sugerido",
    "ru": "💎 Рекомендуется",
}


def _locale(code):
    return json.loads(Path("locales", f"{code}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("code", UI_CODES)
def test_locale_names_every_translation_language(code):
    names = _locale(code)["language_names"]
    renpy_ids = {lang.renpy for lang in all_languages()}
    assert set(names) == renpy_ids and len(renpy_ids) == 5
    assert all(isinstance(v, str) and v.strip() for v in names.values())
    assert names["english"] == EXPECTED_ENGLISH_NAME[code]


def test_all_locales_share_the_same_keys_including_mod_texts():
    keysets = {code: set(_locale(code)) for code in UI_CODES}
    reference = keysets["en"]
    assert all(keys == reference for keys in keysets.values())
    assert sum(1 for key in reference if key.startswith("mod_")) >= 20


@pytest.mark.parametrize("code", UI_CODES)
def test_recommended_badge_is_translated_for_each_interface_language(code):
    assert _locale(code)["badge_recommended"] == EXPECTED_RECOMMENDED_BADGE[code]


def test_portuguese_native_mode_label_has_no_english_output_term():
    assert "Output" not in _locale("pt")["native_tlid_label"]


def test_portuguese_brand_label_and_recommendation_are_portuguese():
    portuguese = _locale("pt")
    assert portuguese["nav_workspace_label"] == "Tradutor de Ren'Py"
    assert portuguese["badge_recommended"] == "💎 Sugerido"


def test_ui_language_popup_matches_five_visible_options():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    popup = qml[qml.index("id: uiLanguageCombo"):qml.index("id: uiLanguageCombo") + 3000]
    assert "height: 36" in popup
    assert "implicitHeight: contentHeight" in popup
    assert "implicitHeight: Math.min(contentItem.implicitHeight + padding * 2, 188)" in popup


def test_update_checks_are_not_started_automatically_but_manual_check_remains():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    startup = qml[qml.index("Component.onCompleted:", qml.index("function workspaceHint")):qml.index("// ── Backend")]
    assert "checkForUpdates" not in startup
    assert "toolUpdatesStartupCheck" not in qml
    assert "appBackend.checkForUpdates(true)" in qml

    from src.utils import update_checker

    assert update_checker.UPDATE_REPO == "Mustadio7813/LinguaNova"


@pytest.mark.parametrize("code", ["es", "fr", "pt", "ru"])
def test_common_interface_and_update_texts_are_localized(code):
    english = _locale("en")
    translated = _locale(code)
    for key in ("status_ready", "about_title", "update_checking"):
        assert translated[key] != english[key], key


@pytest.mark.parametrize("code", UI_CODES)
def test_locale_templates_preserve_all_runtime_placeholders(code):
    english = _locale("en")
    translated = _locale(code)
    for key, source in english.items():
        if isinstance(source, str) and isinstance(translated[key], str):
            translated_placeholders = Counter(
                re.findall(r"(?<!\{)\{(?!\{)([^{}]+)\}(?!\})", translated[key])
            )
            source_placeholders = Counter(
                re.findall(r"(?<!\{)\{(?!\{)([^{}]+)\}(?!\})", source)
            )
            assert translated_placeholders == source_placeholders, key


def test_language_picker_tiles_are_compact_and_content_sized():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert qml.count("cellHeight: 46") == 2
    assert qml.count(
        "readonly property int visibleRows: Math.max(1, Math.ceil(getFilteredList().length / columns))"
    ) == 2
    assert qml.count("width >= 700 ? 5 : (width >= 520 ? 4 : 3)") == 2
    assert "appBackend.localizeLogMessage(message)" in qml


@pytest.mark.parametrize("code", UI_CODES)
def test_catalog_backed_log_messages_follow_the_interface_language(code):
    from src.backend.app_backend import AppBackend

    locales = {language: _locale(language) for language in UI_CODES}
    config = SimpleNamespace(
        app_settings=SimpleNamespace(ui_language=code),
        get_ui_translations=lambda: locales,
    )
    backend = SimpleNamespace(config=config, _localized_log_patterns={})
    backend._get_log_translation_patterns = lambda language: (
        AppBackend._get_log_translation_patterns(backend, language)
    )

    checking = "🔍 Checking for updates... (owner/repository)"
    assert AppBackend.localizeLogMessage(backend, checking) == (
        f"🔍 {locales[code]['update_checking']} (owner/repository)"
    )

    project_path = "📁 Project path: C:\\games\\Game"
    assert AppBackend.localizeLogMessage(backend, project_path) == (
        locales[code]["log_project_path"].replace("{path}", "C:\\games\\Game")
    )

    error = "⚠️ Update check failed: network timeout"
    expected_error = locales[code]["log_update_check_failed"].replace(
        "{error}", "network timeout"
    )
    assert AppBackend.localizeLogMessage(backend, error) == f"⚠️ {expected_error}"


def test_ui_language_codes_never_collide_with_translation_folders():
    # UI uses ISO codes (tl folders use Ren'Py ids such as "spanish").
    folders = {lang.renpy for lang in all_languages()}
    assert not folders & set(UI_CODES)


def test_main_translation_selectors_expose_only_the_five_supported_languages():
    from src.utils.config import ConfigManager

    config = ConfigManager()
    expected = ["spanish", "english", "portuguese", "french", "russian"]
    assert [code for code, _name in config.get_target_languages_for_ui()] == expected
    assert [code for code, _name in config.get_source_languages_for_ui()] == ["auto", *expected]
    assert config.normalize_renpy_language_code("polish") == "polish"


def test_mod_package_does_not_read_the_interface_language():
    for path in Path("src/ui_mod").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "ui_language" not in text and "get_ui_text" not in text, path


def test_portuguese_locale_translates_mod_controls():
    assert _locale("pt")["mod_target_label"] != _locale("en")["mod_target_label"]


def test_mod_target_and_engine_snapshot_are_independent_from_translation_settings():
    from src.backend.app_backend import AppBackend
    from src.core.translator import TranslationEngine

    config = SimpleNamespace(translation_settings=SimpleNamespace(
        mod_target_language="russian",
        mod_selected_engine="deepseek",
        target_language="french",
        source_language="spanish",
        selected_engine="bing",
    ))
    backend = SimpleNamespace(_mod_project_path="C:\\game", config=config)
    snapshot = AppBackend._mod_job_snapshot(backend)

    assert snapshot == {
        "project_path": "C:\\game",
        "target_language": "russian",
        "source_language": "auto",
        "engine": "deepseek",
    }
    assert AppBackend._engine_from_str(snapshot["engine"]) == TranslationEngine.OPENAI


def test_mod_target_language_selector_contains_exactly_the_five_languages():
    from src.backend.app_backend import AppBackend

    assert [item["code"] for item in AppBackend.getModTargetLanguages(None)] == [
        "spanish", "french", "english", "portuguese", "russian",
    ]


def test_preparing_mod_engine_does_not_replace_main_translation_engine():
    from src.backend.app_backend import AppBackend
    from src.core.translator import TranslationEngine, TranslationManager
    from src.utils.config import ConfigManager

    config = ConfigManager()
    main_manager = TranslationManager(config_manager=config)
    mod_manager = TranslationManager(config_manager=config)

    class BackendStub:
        _replace_translator = AppBackend._replace_translator

    backend = BackendStub()
    backend._mod_translation_manager = mod_manager
    backend.translation_manager = main_manager
    backend.config = config
    backend.proxy_manager = None

    AppBackend._ensure_mod_translator(backend, TranslationEngine.GOOGLE, "google")

    assert TranslationEngine.GOOGLE in mod_manager.translators
    assert TranslationEngine.GOOGLE not in main_manager.translators


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
    config.translation_settings.target_language = "spanish"
    backend = SettingsBackend(config, translation_manager=None)
    backend.set_ui_language(code)
    assert config.app_settings.ui_language == code
    assert config.translation_settings.source_language == "portuguese"
    assert config.translation_settings.target_language == "spanish"
    reloaded = ConfigManager()
    assert reloaded.app_settings.ui_language == code
    assert reloaded.translation_settings.target_language == "spanish"
    assert reloaded.get_ui_text("language_names.english") == EXPECTED_ENGLISH_NAME[code]
