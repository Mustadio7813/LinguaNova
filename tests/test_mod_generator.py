# -*- coding: utf-8 -*-
import json
from pathlib import Path
from types import SimpleNamespace

from src.core.translator import TranslationEngine
from src.ui_mod.generator import (
    generate_interface_mod,
    load_interface_mod_translations,
    save_interface_mod_corrections,
)


_ES = {
    "Inventory": "Inventario",
    "Do not translate this dialogue.": "No traduzcas este diálogo.",
    "Manual label": "Etiqueta manual",
    "Needs a real translation": "Necesita una traducción real",
}


class FakeManager:
    """Simulated engine (no network): returns real Spanish so MOD validation applies."""

    async def translate_batch(self, requests):
        self.last_requests = list(requests)
        FakeManager.last_seen = list(requests)
        out = []
        for req in requests:
            text = req.text
            if text.startswith("Money:"):
                translated = text.replace("Money:", "Dinero:")
            else:
                translated = _ES.get(text, "Traducción de prueba")
            out.append(SimpleNamespace(success=True, translated_text=translated))
        return out


def test_generate_mod_from_visible_rpy_is_independent(tmp_path: Path):
    game = tmp_path / "game"
    game.mkdir()
    exe = tmp_path / "My Sandbox.exe"
    exe.write_bytes(b"")
    (game / "screens.rpy").write_text(
        '''screen inventory():\n    text "Inventory"\n    text "Money: [money]"\n\nlabel start:\n    e "Do not translate this dialogue."\n''',
        encoding="utf-8",
    )

    result = generate_interface_mod(
        str(exe), "english", "spanish", TranslationEngine.GOOGLE, FakeManager()
    )
    assert result.success
    assert (game / "zzz_linguanova_ocultar_fuentes.rpy").is_file()
    assert result.translated == 3
    output = Path(result.output_path)
    assert output.name == "linguanova_mod_my_sandbox_multilang.rpy"
    content = output.read_text(encoding="utf-8")
    data = json.loads((game / "tl" / "spanish" / "linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"]["Inventory"] == "Inventario"
    assert data["mapping"]["Money: [money]"] == "Dinero: [money]"
    assert data["mapping"]["Do not translate this dialogue."] == "No traduzcas este diálogo."
    assert "config.replace_text = _lnmod_replace_text" in content
    # 2026-10-17: the hook is readable (one "original": "translation" line per entry).
    assert '"Do not translate this dialogue.": "No traduzcas este diálogo.",' in content
    assert "b85decode" not in content
    assert "linguanova_mod_hook_data.json" in content
    assert all(request.target_lang == "es" and request.source_lang == "en" for request in FakeManager.last_seen)
    report = json.loads((game / "tl" / "spanish" / "linguanova_mod_report.json").read_text(encoding="utf-8"))
    assert report["coverage_percent"] == 100.0


def test_existing_tl_is_reused_and_junk_manual_translation_is_rejected(tmp_path: Path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "screens.rpy").write_text(
        'screen inventory():\n    text "Inventory"\n    text "Manual label"\n', encoding="utf-8"
    )
    tl = game / "tl" / "spanish" / "nested"
    tl.mkdir(parents=True)
    (tl / "strings.rpy").write_text(
        'translate spanish strings:\n    old "Inventory"\n    new "Inventario manual"\n'
        '    old "Manual label"\n    new "A"\n', encoding="utf-8"
    )
    manager = FakeManager()
    result = generate_interface_mod(
        str(tmp_path), "english", "spanish", TranslationEngine.GOOGLE, manager
    )
    assert result.success and result.translated == 2
    data = json.loads((game / "tl" / "spanish" / "linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"]["Inventory"] == "Inventario manual"
    assert data["mapping"]["Manual label"] == "Etiqueta manual"
    assert [request.text for request in manager.last_requests] == ["Manual label"]


def test_manual_json_edits_survive_regeneration_and_junk_is_rejected(tmp_path: Path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "screens.rpy").write_text(
        'screen inventory():\n    text "Inventory"\n    text "Needs a real translation"\n',
        encoding="utf-8",
    )
    first = generate_interface_mod(
        str(tmp_path), "english", "spanish", TranslationEngine.GOOGLE, FakeManager()
    )
    assert first.success

    tl = game / "tl" / "spanish"
    manual_path = tl / "linguanova_mod_manual.json"
    manual = json.loads(manual_path.read_text(encoding="utf-8"))
    manual["mapping"]["Inventory"] = "Inventario revisado"
    manual["mapping"]["Needs a real translation"] = "A"
    manual_path.write_text(json.dumps(manual, ensure_ascii=False), encoding="utf-8")

    manager = FakeManager()
    second = generate_interface_mod(
        str(tmp_path), "english", "spanish", TranslationEngine.GOOGLE, manager
    )
    assert second.success
    # The validated machine translation comes from MOD's own cache; no new request.
    assert not hasattr(manager, "last_requests")

    data = json.loads((tl / "linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"]["Inventory"] == "Inventario revisado"
    assert data["mapping"]["Needs a real translation"] == "Necesita una traducción real"
    report = json.loads((tl / "linguanova_mod_report.json").read_text(encoding="utf-8"))
    assert report["manual_entries_used"] == 1
    assert report["manual_entries_rejected"] == 1


def test_manual_corrections_can_be_edited_in_app_and_survive_regeneration(tmp_path: Path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "screens.rpy").write_text(
        'screen inventory():\n    text "Inventory"\n', encoding="utf-8"
    )

    generated = generate_interface_mod(
        str(tmp_path), "auto", "spanish", TranslationEngine.GOOGLE, FakeManager()
    )
    assert generated.success

    rows = load_interface_mod_translations(str(tmp_path), "spanish")
    assert rows == [{"source": "Inventory", "target": "Inventario"}]
    rows[0]["target"] = "Inventario corregido"
    assert save_interface_mod_corrections(str(tmp_path), "spanish", rows) == 1
    assert load_interface_mod_translations(str(tmp_path), "spanish")[0]["target"] == "Inventario corregido"

    regenerated = generate_interface_mod(
        str(tmp_path), "auto", "spanish", TranslationEngine.GOOGLE, FakeManager()
    )
    assert regenerated.success
    assert load_interface_mod_translations(str(tmp_path), "spanish")[0]["target"] == "Inventario corregido"
