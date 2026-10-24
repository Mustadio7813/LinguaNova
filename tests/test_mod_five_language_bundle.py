# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.core.translator import TranslationEngine
from src.ui_mod import generator
from src.ui_mod.generator import (
    DATA_FILE,
    generate_interface_mod,
    generate_interface_mod_languages,
)
from src.ui_mod.hook_check import displayed, run_hook
from src.ui_mod.quality import QualityVerdict


class RecordingManager:
    def __init__(self):
        self.requests = []

    async def translate_batch(self, requests):
        self.requests.extend(requests)
        return [
            SimpleNamespace(
                success=True,
                translated_text=f"{request.target_lang.upper()}::{request.text}",
            )
            for request in requests
        ]


def _accept_all(monkeypatch):
    monkeypatch.setattr(
        generator,
        "validate_translation",
        lambda source, target, language, source_language=None: QualityVerdict("accepted"),
    )


def test_five_target_languages_share_one_live_switch_hook(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = tmp_path / "game"
    game.mkdir()
    (game / "screens.rpy").write_text(
        'screen main_menu():\n    textbutton "Main Menu" action NullAction()\n'
        '    textbutton "Start Game" action NullAction()\n',
        encoding="utf-8",
    )
    manager = RecordingManager()
    scans = []
    original_scan = generator.ModProjectScanner.scan

    def counted_scan(scanner, path):
        scans.append(path)
        return original_scan(scanner, path)

    monkeypatch.setattr(generator.ModProjectScanner, "scan", counted_scan)

    result = generate_interface_mod_languages(
        str(tmp_path),
        "english",
        ["spanish", "french", "english", "portuguese", "russian"],
        TranslationEngine.GOOGLE,
        manager,
    )

    assert result.success
    assert result.languages_generated == result.languages_total == 5
    assert scans == [str(tmp_path)]
    assert Path(result.output_path).parent == game
    assert Path(result.output_path).name == f"linguanova_mod_{tmp_path.name}_multilang.rpy"
    assert {request.target_lang for request in manager.requests} == {"es", "fr", "pt", "ru"}
    assert {request.engine for request in manager.requests} == {TranslationEngine.GOOGLE}
    expected_targets = {
        "spanish": "es", "french": "fr", "english": "en",
        "portuguese": "pt", "russian": "ru",
    }
    for language, target_code in expected_targets.items():
        data = json.loads((game / "tl" / language / DATA_FILE).read_text(encoding="utf-8"))
        assert data["api_target"] == target_code

    hook = Path(result.output_path).read_text(encoding="utf-8")
    for language in ("spanish", "french", "english", "portuguese", "russian"):
        assert f'"{language}": {{' in hook
    assert '"Русский"' in hook

    namespace, _config, translator, preferences = run_hook(hook, "russian")
    assert displayed(translator, preferences, "Main Menu") == "RU::Main Menu"
    assert namespace["_lnmod_ui_text"]("title") == "Выбрать язык"
    assert namespace["_lnmod_ui_text"]("button") == "Язык"
    preferences.language = "french"
    assert displayed(translator, preferences, "Main Menu") == "FR::Main Menu"
    assert namespace["_lnmod_ui_text"]("title") == "Choisir la langue"
    preferences.language = "portuguese"
    assert namespace["_lnmod_ui_text"]("title") == "Escolher idioma"
    preferences.language = "spanish"
    assert namespace["_lnmod_ui_text"]("title") == "Elegir idioma"
    preferences.language = "english"
    assert namespace["_lnmod_ui_text"]("title") == "Choose language"


def test_long_interface_text_is_sent_as_one_complete_translation_request(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = tmp_path / "game"
    game.mkdir()
    source = "A complete interface description that must remain whole. " * 20
    (game / "screens.rpy").write_text(
        "screen help_menu():\n    text " + json.dumps(source, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manager = RecordingManager()

    result = generate_interface_mod(
        str(tmp_path),
        "english",
        "spanish",
        TranslationEngine.GOOGLE,
        manager,
    )

    assert result.success
    assert len(manager.requests) == 1
    assert manager.requests[0].text == source
    data = json.loads((game / "tl" / "spanish" / DATA_FILE).read_text(encoding="utf-8"))
    assert source in data["mapping"]
    assert data["mapping"][source] == f"ES::{source}"
