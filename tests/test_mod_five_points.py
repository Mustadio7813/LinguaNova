# -*- coding: utf-8 -*-
"""MOD improvements of 2026-10-17 (SIMULATED engine and Ren'Py stand-in):

1. compiled games (.rpyc / .rpa) are read in memory, nothing is written to the game;
2. tagged text is translated and registered as ONE string (no fragments);
3. fonts are replaced only when they cannot draw the language; RTL is enabled;
4. in-game language panel (Language() actions, hot switch);
5. per-language glossary (names kept, terms forced, cache re-checked).
"""
from __future__ import annotations

import io
import json
import os
import pickle
import zlib
from pathlib import Path

import pytest

from src.core.translator import TranslationEngine
from src.ui_mod import fonts as mod_fonts
from src.ui_mod.generator import generate_interface_mod
from src.ui_mod.glossary import consistent, protect_terms, restore_terms
from src.ui_mod.hook_check import displayed, run_hook
from src.ui_mod.languages import resolve_language
from src.ui_mod.scanner import ModProjectScanner

from test_mod_language_contract import ScriptedManager, _game, _hook_runtime

GOOGLE = TranslationEngine.GOOGLE


@pytest.fixture(autouse=True)
def _no_font_downloads(monkeypatch):
    monkeypatch.setattr(mod_fonts, "default_fetcher", lambda family, target_dir: (False, ""))


def _always(req):
    """Simulated engine that keeps protected tokens and marks the text as Polish."""
    return "PL " + req.text


def _accept_all(monkeypatch):
    from src.ui_mod import generator as gen, quality
    monkeypatch.setattr(gen, "validate_translation",
                        lambda s, t, target, source=None: quality.QualityVerdict("accepted"))


# ── synthetic compiled files ─────────────────────────────────────────────────

def _build_rpyc(nodes_spec) -> bytes:
    """RPC2 .rpyc whose pickle references renpy.ast.Say/Menu/Label (as real games do)."""
    import struct
    import sys
    import types
    renpy = types.ModuleType("renpy")
    ast = types.ModuleType("renpy.ast")
    classes = {}
    for name in ("Say", "Menu", "Label"):
        cls = type(name, (), {})
        cls.__module__ = "renpy.ast"
        setattr(ast, name, cls)
        classes[name.lower()] = cls
    renpy.ast = ast
    saved = {k: sys.modules.get(k) for k in ("renpy", "renpy.ast")}
    sys.modules["renpy"], sys.modules["renpy.ast"] = renpy, ast
    try:
        nodes = []
        for kind, data in nodes_spec:
            node = classes[kind]()
            node.__dict__.update(data)
            nodes.append(node)
        raw = pickle.dumps((None, nodes), protocol=2)
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value
    comp = zlib.compress(raw)
    return b"RENPY RPC2" + struct.pack("<III", 1, 34, len(comp)) + struct.pack("<III", 0, 0, 0) + comp


def _rpa3(path: Path, members) -> None:
    header_len = len(b"RPA-3.0 0000000000000000 00000000\n")
    body, index, offset = b"", {}, header_len
    for name, payload in members.items():
        index[name] = [(offset, len(payload), b"")]
        body += payload
        offset += len(payload)
    header = f"RPA-3.0 {offset:016x} {0:08x}\n".encode("ascii")
    path.write_bytes(header + body + zlib.compress(pickle.dumps(index, protocol=2)))


QUEST = "Olá {b}Anna{/b}, leve a {color=#f00}chave dourada{/color} até a torre [tower]!"
STORY = [("label", {"name": "start"}),
         ("say", {"who": "a", "what": QUEST, "linenumber": 3, "filename": "story.rpy"}),
         ("say", {"who": None, "what": "Pegue a chave antes de sair.", "linenumber": 4, "filename": "story.rpy"})]


def _snapshot(folder: Path):
    return sorted((str(p.relative_to(folder)), p.stat().st_size) for p in folder.rglob("*"))


# ── 1. compiled games ────────────────────────────────────────────────────────

def test_orphan_rpyc_is_read_in_memory_and_nothing_is_written(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "story.rpyc").write_bytes(_build_rpyc(STORY))
    before = _snapshot(tmp_path)
    report = ModProjectScanner().scan(str(tmp_path))
    assert report.decompiled_rpyc_files == 1 and report.skipped_compiled_files == 0
    assert set(report.unique_texts()) == {QUEST, "Pegue a chave antes de sair."}
    assert _snapshot(tmp_path) == before                      # no .rpy/.rpyc written


def test_rpyc_inside_rpa_and_fonts_inside_rpa_are_read(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    _rpa3(game / "archive.rpa", {
        "story.rpyc": _build_rpyc(STORY),
        "characters.rpy": b'define a = Character("Anna", color="#fff")\n',
        "fonts/Game.ttf": b"not really a font",
        "images/bg.png": b"\x89PNG....",
    })
    before = _snapshot(tmp_path)
    report = ModProjectScanner().scan(str(tmp_path))
    assert QUEST in report.unique_texts()
    assert "fonts/Game.ttf" in report.font_files and "images/bg.png" not in report.font_files
    assert "Anna" in report.character_names
    assert _snapshot(tmp_path) == before


# ── 2. whole tagged strings ──────────────────────────────────────────────────

def test_tagged_mission_text_is_sent_once_and_shown_whole(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = tmp_path / "game"
    game.mkdir()
    (game / "story.rpyc").write_bytes(_build_rpyc(STORY))
    manager = ScriptedManager(default=_always)
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, manager)
    assert result.success, result.message
    sent = [r.text for r in manager.requests]
    quest_requests = [t for t in sent if "chave dourada" in t]
    assert len(quest_requests) == 1                         # one request, not one per fragment
    assert "{b}" not in quest_requests[0] and "[tower]" not in quest_requests[0]   # tags protected
    hook = Path(result.output_path).read_text(encoding="utf-8")
    _ns, _config, translator, prefs = run_hook(hook, "polish")
    shown = displayed(translator, prefs, QUEST)
    assert shown.startswith("PL ") and "{b}Anna{/b}" in shown and "{color=#f00}" in shown and "[tower]" in shown
    assert displayed(translator, prefs, "Pegue a chave antes de sair.") == "PL Pegue a chave antes de sair."


def test_game_translation_already_present_is_never_overridden(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, ScriptedManager(default=_always))
    hook = Path(result.output_path).read_text(encoding="utf-8")
    ns, _config, translator, prefs = run_hook(hook, "polish", preexisting={"polish": {"Menu principal": "OFICJALNE"}})
    assert displayed(translator, prefs, "Menu principal") == "OFICJALNE"   # no duplicate → no crash
    assert ns["_lnmod_registered"]["polish"] == (0, 1)


# ── 3. fonts and RTL ─────────────────────────────────────────────────────────

def _ttf(chars: str) -> bytes:
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    names = [".notdef"] + [f"u{ord(c):04X}" for c in chars]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap({ord(c): f"u{ord(c):04X}" for c in chars})
    pen = TTGlyphPen(None)
    fb.setupGlyf({n: pen.glyph() for n in names})
    fb.setupHorizontalMetrics({n: (500, 0) for n in names})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Test", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    out = io.BytesIO()
    fb.save(out)
    return out.getvalue()


ASCII = "".join(chr(c) for c in range(32, 127))


def test_font_without_polish_letters_is_replaced_only_for_polish(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = _game(tmp_path, ["Menu principal"])
    (game / "fonts").mkdir()
    (game / "fonts" / "Game.ttf").write_bytes(_ttf(ASCII))
    fetched = []

    def fetcher(family, target_dir):
        fetched.append(family)
        (target_dir / "Full.ttf").write_bytes(_ttf(ASCII + "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"))
        return True, "Full.ttf"

    manager = ScriptedManager({"Menu principal": "Menu główne"})
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, manager, font_fetcher=fetcher)
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["fonts"]["status"] == "ok" and report["fonts"]["replaced"] == ["fonts/Game.ttf"]
    assert report["font_replacements"]["fonts/Game.ttf"] == "linguanova_mod_fonts/Full.ttf"
    assert (game / "linguanova_mod_fonts" / "Full.ttf").is_file()
    assert not (game / "tl" / "linguanova_mod_fonts").exists()     # never a fake language folder

    hook = Path(result.output_path).read_text(encoding="utf-8")
    assert 'translate polish python:\n    _lnmod_apply_fonts("polish")' in hook
    assert "translate None python:" in hook
    ns, config, _t, _p = run_hook(hook, "polish")
    ns["_lnmod_apply_fonts"]("polish")
    assert config.font_replacement_map[("fonts/Game.ttf", False, False)] == ("linguanova_mod_fonts/Full.ttf", False, False)
    ns["_lnmod_apply_fonts"](None)                                # back to the original language
    assert config.font_replacement_map == {}


def test_font_that_already_covers_the_language_is_kept(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = _game(tmp_path, ["Menu principal"])
    (game / "Game.ttf").write_bytes(_ttf(ASCII + "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"))
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE,
                                    ScriptedManager({"Menu principal": "Menu główne"}),
                                    font_fetcher=lambda f, d: pytest.fail("no download needed"))
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["font_replacements"] == {} and not (game / "linguanova_mod_fonts").exists()


def test_missing_font_is_reported_and_translation_still_published(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "japanese", GOOGLE,
                                    ScriptedManager({"Menu principal": "メインメニュー"}))
    assert result.success
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["fonts"]["status"] == "missing"
    assert any("squares" in note for note in report["notes"])


def test_rtl_language_enables_config_rtl(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "arabic", GOOGLE,
                                    ScriptedManager({"Menu principal": "القائمة الرئيسية"}))
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["rtl"] is True
    _ns, config, _t, _p = run_hook(Path(result.output_path).read_text(encoding="utf-8"), "arabic")
    assert config.rtl is True


# ── 4. language panel ────────────────────────────────────────────────────────

def test_panel_lists_every_mod_language_with_progress_and_native_switch(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = _game(tmp_path, ["Menu principal", "Carregar save"])
    (game / "tl" / "french").mkdir(parents=True)                  # the game's own translation
    generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE,
                           ScriptedManager({"Menu principal": "Menu główne"}))
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", GOOGLE, ScriptedManager(default=_always))
    hook = Path(result.output_path).read_text(encoding="utf-8")
    assert "screen lnmod_language_panel():" in hook and "screen lnmod_language_button():" in hook
    assert 'key "shift_K_l"' in hook and "Language(None)" in hook and "Language(_lnmod_lang)" in hook
    ns, config, translator, prefs = run_hook(hook, "polish")
    assert "lnmod_language_button" in config.overlay_screens
    # 2026-10-18 audit (point 3.3): the player sees language names only; the
    # coverage numbers stay in linguanova_mod_report.json.
    rows = dict(ns["_lnmod_menu_languages"]())
    assert rows["polish"] == "Polski"
    assert rows["russian"] == "Russian"                            # Cyrillic → English label
    panel = hook[hook.index("screen lnmod_language_panel():"):]
    assert "%" not in panel.split("translate ")[0] and "LinguaNova MOD" not in panel
    assert "translate french python:" in hook                      # fonts reset for the game's own language
    prefs.language = "russian"                                      # hot switch: same tables, no reload
    assert displayed(translator, prefs, "Menu principal") == "PL Menu principal"
    prefs.language = "polish"
    assert displayed(translator, prefs, "Menu principal") == "Menu główne"


def test_new_players_start_in_the_mod_language_but_game_default_is_respected(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, ScriptedManager(default=_always))
    hook = Path(result.output_path).read_text(encoding="utf-8")
    _ns, config, _t, _p = run_hook(hook, None)
    assert config.default_language == "polish"
    from src.ui_mod.hook_check import make_env, python_body
    ns, config, _t, _p = make_env(None)
    config.default_language = "english"                             # game already chose one
    exec(compile(python_body(hook), "hook", "exec"), ns, ns)
    assert config.default_language == "english"


# ── 5. glossary ──────────────────────────────────────────────────────────────

def test_glossary_helpers_round_trip():
    text, mapping = protect_terms("Anna bebe a Poção de vida.", {"Anna": "Anna", "Poção de vida": "Eliksir życia"})
    assert "Anna" not in text and "Poção" not in text and len(mapping) == 2
    assert restore_terms(text.replace("__LNMOD_TERM_1__", "__ LNMOD_TERM_1 __"), mapping) == "Anna bebe a Eliksir życia."
    tagged, mapping = protect_terms("__LNMOD_TOKEN_0__Anna__LNMOD_TOKEN_1__ bebe", {"Anna": "Anna"})
    assert "Anna" not in tagged and restore_terms(tagged, mapping) == "__LNMOD_TOKEN_0__Anna__LNMOD_TOKEN_1__ bebe"
    assert consistent("Anna bebe", "Anna pije", {"Anna": "Anna"})
    assert not consistent("Anna bebe", "Ania pije", {"Anna": "Anna"})


def test_character_names_are_kept_and_glossary_terms_forced(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = _game(tmp_path, ["Anna", "Fale com Anna sobre a Poção de vida.", "Olá {b}Anna{/b}!"])
    (game / "characters.rpy").write_text('define a = Character("Anna")\n', encoding="utf-8")
    manager = ScriptedManager(default=_always)
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, manager)
    gloss_path = game / "tl" / "polish" / "linguanova_mod_glossary.json"
    glossary = json.loads(gloss_path.read_text(encoding="utf-8"))
    assert glossary["terms"] == {"Anna": "Anna"}
    assert all("Anna" not in r.text for r in manager.requests)        # name protected / not sent alone
    data = json.loads((game / "tl/polish/linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"]["Fale com Anna sobre a Poção de vida."] == "PL Fale com Anna sobre a Poção de vida."
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["glossary_kept_as_is"] == 1 and report["character_names"] == ["Anna"]

    # The user adds a term: the cached line no longer agrees and is translated again.
    glossary["terms"]["Poção de vida"] = "Eliksir życia"
    gloss_path.write_text(json.dumps(glossary, ensure_ascii=False), encoding="utf-8")
    m2 = ScriptedManager(default=_always)
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, m2)
    assert len(m2.requests) == 1 and "Poção" not in m2.requests[0].text
    data = json.loads((game / "tl/polish/linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"]["Fale com Anna sobre a Poção de vida."] == "PL Fale com Anna sobre a Eliksir życia."
    assert json.loads(gloss_path.read_text(encoding="utf-8"))["terms"]["Poção de vida"] == "Eliksir życia"


def test_glossary_term_as_whole_string_needs_no_engine(tmp_path, monkeypatch):
    _accept_all(monkeypatch)
    game = _game(tmp_path, ["Inventário"])
    tl = game / "tl" / "polish"
    tl.mkdir(parents=True)
    (tl / "linguanova_mod_glossary.json").write_text(
        json.dumps({"schema": 1, "terms": {"Inventário": "Ekwipunek"}}), encoding="utf-8")
    manager = ScriptedManager(default=_always)
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, manager)
    assert manager.requests == [] and result.translated == 1
    show, _prefs, _ns = _hook_runtime(Path(result.output_path).read_text(encoding="utf-8"), "polish")
    assert show("Inventário") == "Ekwipunek"


# ── localized messages (9 interface languages) ───────────────────────────────

UI_LANGUAGES = ["es", "en", "de", "fr", "ru", "tr", "fa", "ja", "zh-CN"]


def _locale(lang):
    return json.loads((Path(__file__).resolve().parents[1] / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


def test_every_mod_message_exists_in_the_nine_languages_with_same_placeholders():
    import string
    from src.ui_mod.generator import MESSAGES

    def fields(text):
        return sorted(f for _, f, _, _ in string.Formatter().parse(text) if f)

    for lang in UI_LANGUAGES:
        table = _locale(lang)
        for key, english in MESSAGES.items():
            assert key in table, (lang, key)
            assert fields(table[key]) == fields(english), (lang, key)
    assert _locale("en")["mod_msg_no_candidates"] == MESSAGES["mod_msg_no_candidates"]


def test_generator_messages_follow_the_interface_language(tmp_path):
    table = _locale("es")

    def ui_text(key, default, **values):
        return table.get(key, default).format(**values)

    (tmp_path / "game").mkdir()
    progress = []
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE, ScriptedManager(),
                                    ui_text=ui_text)
    assert not result.success and result.message_key == "mod_msg_no_candidates"
    assert result.message == "No se detectaron textos para traducir en este juego."
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE,
                                    ScriptedManager({"Menu principal": "Menu główne"}),
                                    progress=lambda c, t, text: progress.append(text), ui_text=ui_text)
    assert result.message.startswith("MOD generado: 1/1") and progress[0].startswith("MOD: origen=pt")
    broken = generate_interface_mod(str(tmp_path), "portuguese", "polish", GOOGLE,
                                    ScriptedManager({"Menu principal": "Menu główne"}),
                                    ui_text=lambda *a, **k: 1 / 0)          # translator failure → English
    assert broken.message.startswith("MOD generated: 1/1")


def test_backend_text_helper_accepts_format_values():
    """The MOD finish handler formats its status with values; _t must accept them."""
    import ast
    source = (Path(__file__).resolve().parents[1] / "src/backend/app_backend.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    helper = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_t")
    assert helper.args.kwarg is not None
