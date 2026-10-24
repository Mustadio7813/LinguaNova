# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — regression tests for the 2026-10-17 language-mixing fix.
#
# All engines here are SIMULATED (no network). They check the MOD contract:
# codes sent to engines, source resolution, validation, caches, files, hook.
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from src.core.translator import TranslationEngine
from src.ui_mod import generator as gen
from src.ui_mod.filters import code_exclusion_reason, unwrap_marked_literal
from src.ui_mod.languages import all_languages, api_code, folder_aliases, resolve_language
from src.ui_mod.quality import language_identification_available, validate_translation
from src.ui_mod.generator import generate_interface_mod

PL = resolve_language("russian")
PT = resolve_language("portuguese")
ES = resolve_language("spanish")

needs_lid = pytest.mark.skipif(not language_identification_available(), reason="py3langid not installed")


@pytest.fixture(autouse=True)
def _no_font_downloads(monkeypatch):
    """Font downloads are simulated: no network in tests (fonts are tested in test_mod_five_points)."""
    from src.ui_mod import fonts
    monkeypatch.setattr(fonts, "default_fetcher", lambda family, target_dir: (False, ""))


def _game(tmp_path: Path, texts) -> Path:
    game = tmp_path / "game"
    game.mkdir(parents=True, exist_ok=True)
    body = "screen hud():\n" + "".join(f"    text {json.dumps(t, ensure_ascii=False)}\n" for t in texts)
    (game / "screens.rpy").write_text(body, encoding="utf-8")
    return game


class ScriptedManager:
    """Simulated TranslationManager: answers from a table keyed by (source_lang, text)."""

    def __init__(self, table=None, default=None, fail=False):
        self.table = table or {}
        self.default = default
        self.fail = fail
        self.requests = []
        self.bypass_active_during_calls = []
        self._local = threading.local()

    @contextmanager
    def bypass_cache(self):
        self._local.active = True
        try:
            yield
        finally:
            self._local.active = False

    async def translate_batch(self, requests):
        if self.fail:
            raise RuntimeError("network down")
        self.bypass_active_during_calls.append(getattr(self._local, "active", False))
        self.requests.extend(requests)
        out = []
        for req in requests:
            answer = self.table.get((req.source_lang, req.text), self.table.get(req.text))
            if answer is None and self.default is not None:
                answer = self.default(req)
            out.append(SimpleNamespace(success=answer is not None, translated_text=answer or "", error=""))
        return out


# ── language catalogue ───────────────────────────────────────────────────────

def test_every_catalogue_language_maps_to_its_api_code_not_its_folder_name():
    languages = all_languages()
    assert [(lang.renpy, lang.api) for lang in languages] == [
        ("spanish", "es"),
        ("english", "en"),
        ("portuguese", "pt"),
        ("french", "fr"),
        ("russian", "ru"),
    ]
    for lang in languages:
        assert api_code(lang.renpy) == lang.api
        assert api_code(lang.api) == lang.api
        assert resolve_language(lang.english) is lang
        assert lang.renpy.lower() in folder_aliases(lang.renpy)
    assert api_code("auto") == "auto"
    with pytest.raises(ValueError):
        api_code("polish")
    with pytest.raises(ValueError):
        api_code("klingon_unknown")


def test_old_shim_no_longer_forwards_folder_names():
    assert gen._api_language("russian") == "ru"
    with pytest.raises(ValueError):
        gen._api_language("polish")


def test_rtl_and_scripts_are_known():
    assert not PL.rtl
    assert resolve_language("russian").script == "CYRILLIC"


# ── candidates ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    '"color" in h.who_args',
    'max(0, CONFIRM_BUBBLE_CONTAINER_SIZE[0] - CONFIRM_BUBBLE_TEXT_PADDING[0])',
    'SetScreenVariable("phase", "leave")',
    '\n_DEVSB = {\n    "dim": "#0009",\n    "panel": "#12161F",\n}\n',
    ' | reason=%s',
    '  (erro lendo rotas: %r)',
    'pool lookside_chatting3',
])
def test_code_and_debug_strings_are_excluded(text):
    assert code_exclusion_reason(text)


@pytest.mark.parametrize("text", [
    "Save (1)", "Slot [2]", "This is it", "yes or no", "Money: [money]", "Menu principal",
    "helena.main01#110 fechado. À noite na frente do motel.", "%d item(ns) · dinheiro %s",
])
def test_player_text_is_kept(text):
    assert code_exclusion_reason(text) is None


def test_marked_call_is_unwrapped():
    assert unwrap_marked_literal('_("Menu principal")') == "Menu principal"
    assert unwrap_marked_literal('Function(x, "a")') is None


# ── validation (real engine answers recorded in the Portuguese→Russian report) ─

@needs_lid
@pytest.mark.parametrize("source,answer", [
    ("( ...são as duas. As DUAS. )", "( ... São as Duas. Jako DUAS. )"),
    ("( A Donna mandou eu olhar pela janela... melhor pegar o binóculo. )",
     "( A Donna mandou eu olhar pela janela... Zrób to z góry. )"),
    ("( Vou avisar as meninas que a torta tá pronta. )",
     "( Będziesz awisar jako meninas que a torta tá pronta. )"),
    ("Ainda mais porque o Henk andou passando por lá...", "Ainda mais boque o Henk andou idą por lá..."),
])
def test_recorded_mixed_answers_are_rejected(source, answer):
    verdict = validate_translation(source, answer, PL, PT)
    assert verdict.status == "rejected", verdict


def test_case_only_or_identical_answers_are_not_counted_as_translations():
    assert validate_translation("  (erro lendo rotas)", "  (Erro Lendo Rotas)", PL, PT).status == "invariant"
    assert validate_translation("Mouse", "Mouse", PL, PT).status == "invariant"


@needs_lid
@pytest.mark.parametrize("source,answer,target", [
    ("( A Donna mandou eu olhar pela janela... melhor pegar o binóculo. )",
     "(Donna me dijo que mirara por la ventana... Mejor coger los prismáticos. )", "spanish"),
    ("Nenhuma missão ativa no momento.", "Сейчас нет активных заданий.", "russian"),
    ("Nenhuma missão ativa no momento.", "Нет активных миссий на данный момент.", "russian"),
])
def test_real_translations_are_accepted(source, answer, target):
    verdict = validate_translation(source, answer, resolve_language(target), PT)
    assert verdict.accepted, verdict


def test_wrong_script_and_broken_variables_are_rejected():
    ru = resolve_language("russian")
    assert validate_translation("Nenhuma missão ativa no momento.", "Nenhuma missao ativa agora mesmo.", ru, PT).status == "rejected"
    assert validate_translation("Dinheiro: [money]", "Деньги: [dinheiro]", PL, PT).reason == "structure_changed"
    assert validate_translation("Olá {b}mundo{/b}", "Привет, мир", PL, PT).reason == "structure_changed"


# ── generator contract ───────────────────────────────────────────────────────

def test_requests_use_api_codes_and_detected_source_and_bypass_shared_cache(tmp_path):
    texts = ["Nenhuma missão ativa no momento.", "Menu principal"]
    _game(tmp_path, texts)
    manager = ScriptedManager({
        ("pt", "Nenhuma missão ativa no momento."): "Сейчас нет активных заданий.",
        ("pt", "Menu principal"): "Главное меню",
    })
    result = generate_interface_mod(str(tmp_path), "auto", "russian", TranslationEngine.GOOGLE, manager,
                                    source_detector=lambda samples: "pt")
    assert result.success and result.translated == 2 and result.pending == 0
    assert {(r.source_lang, r.target_lang) for r in manager.requests} == {("pt", "ru")}
    assert manager.bypass_active_during_calls and all(manager.bypass_active_during_calls)
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["api_source"] == "pt" and report["api_target"] == "ru"
    assert report["engine_codes"] == {"source": "pt", "target": "ru"}


def test_undetermined_source_is_reported_not_turned_into_english(tmp_path):
    _game(tmp_path, ["Menu principal"])
    manager = ScriptedManager({"Menu principal": "Главное меню"})
    result = generate_interface_mod(str(tmp_path), "auto", "russian", TranslationEngine.DEEPL, manager,
                                    source_detector=lambda samples: None)
    assert result.success
    assert {r.source_lang for r in manager.requests} == {"auto"}
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["source_detection"] == "undetermined"


@needs_lid
def test_mixed_batch_answer_is_retried_individually_and_never_published(tmp_path):
    src_ok = "Nenhuma missão ativa no momento."
    src_bad = "( A Donna mandou eu olhar pela janela... melhor pegar o binóculo. )"
    _game(tmp_path, [src_ok, src_bad, "( ...são as duas. As DUAS. )"])
    manager = ScriptedManager({
        ("pt", src_ok): "Сейчас нет активных заданий.",
        ("pt", src_bad): "( A Donna falou que eu deveria olhar pela janela... лучше взять бинокль. )",
        ("auto", src_bad): "( Донна велела мне выглянуть в окно... лучше взять бинокль. )",
        ("pt", "( ...são as duas. As DUAS. )"): "( ... this is both. BOTH. )",
        ("auto", "( ...são as duas. As DUAS. )"): "( ... this is both. BOTH. )",
    })
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE, manager)
    data = json.loads((tmp_path / "game/tl/russian/linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"][src_bad].startswith("( Донна велела")
    assert "( ...são as duas. As DUAS. )" not in data["mapping"]
    assert result.partial and result.pending == 1
    hook = Path(result.output_path).read_text(encoding="utf-8")
    assert "Это обе" not in hook and "сказала мне посмотреть" not in hook


def test_engine_failure_publishes_nothing_and_keeps_previous_output(tmp_path):
    _game(tmp_path, ["Menu principal"])
    ok = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE,
                                ScriptedManager({"Menu principal": "Главное меню"}))
    before = Path(ok.output_path).read_bytes()
    _game(tmp_path, ["Menu principal", "Carregar save"])
    again = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE,
                                   ScriptedManager(fail=True))
    assert again.success and again.partial            # cached valid entry kept, new one pending
    data = json.loads((tmp_path / "game/tl/russian/linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"] == {"Menu principal": "Главное меню"}
    assert "Главное меню".encode("utf-8") in Path(again.output_path).read_bytes() and before


def test_first_run_failure_writes_no_files(tmp_path):
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE,
                                    ScriptedManager(fail=True))
    assert not result.success
    assert not list((tmp_path / "game").glob("linguanova_mod_*.rpy"))
    assert not (tmp_path / "game/tl/russian").exists()


def test_legacy_manual_mirror_and_unprovenanced_data_are_not_trusted(tmp_path):
    game = _game(tmp_path, ["Menu principal"])
    tl = game / "tl" / "russian"
    tl.mkdir(parents=True)
    # Old generator wrote every machine answer here and re-read it as "manual".
    (tl / "linguanova_mod_manual.json").write_text(json.dumps({"mapping": {"Menu principal": "Menú principal"}}), "utf-8")
    (tl / "linguanova_mod_hook_data.json").write_text(json.dumps({"mapping": {"Menu principal": "Menú principal"}, "contexts": {}}), "utf-8")
    manager = ScriptedManager({"Menu principal": "Главное меню"})
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE, manager)
    assert result.success and [r.text for r in manager.requests] == ["Menu principal"]
    manual = json.loads((tl / "linguanova_mod_manual.json").read_text(encoding="utf-8"))
    assert manual["schema"] == 2 and manual["mapping"] == {}
    backups = list((tl / "linguanova_mod_backup").rglob("*.bak"))
    assert {b.name for b in backups} >= {"russian__linguanova_mod_manual.json.bak", "russian__linguanova_mod_hook_data.json.bak"}
    assert not list((tl / "linguanova_mod_backup").rglob("*.rpy"))


def test_hand_edit_wins_and_cache_from_other_source_is_not_reused(tmp_path):
    _game(tmp_path, ["Menu principal", "Carregar save"])
    table = {"Menu principal": "Главное меню", "Carregar save": "Загрузить игру"}
    generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE, ScriptedManager(table))
    tl = tmp_path / "game/tl/russian"
    manual = json.loads((tl / "linguanova_mod_manual.json").read_text(encoding="utf-8"))
    manual["mapping"]["Carregar save"] = "Загрузить игру"
    (tl / "linguanova_mod_manual.json").write_text(json.dumps(manual, ensure_ascii=False), "utf-8")
    m2 = ScriptedManager(table)
    generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE, m2)
    data = json.loads((tl / "linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"]["Carregar save"] == "Загрузить игру" and m2.requests == []
    m3 = ScriptedManager(table)   # declared source changes → cached machine answers are retranslated
    generate_interface_mod(str(tmp_path), "spanish", "russian", TranslationEngine.GOOGLE, m3)
    assert [r.text for r in m3.requests] == ["Menu principal"]


def _hook_runtime(hook_text, language, files=None, preexisting=None):
    """Run the hook in the Ren'Py stand-in; ``show`` = what the player would read."""
    import re as _re
    from src.ui_mod.hook_check import displayed, run_hook
    ns, config, translator, prefs = run_hook(hook_text, language, files, preexisting)

    def show(text, **values):
        out = displayed(translator, prefs, text)            # native table, whole string
        out = _re.sub(r"\[(\w+)\]", lambda m: str(values.get(m.group(1), m.group(0))), out)
        return config.replace_text(out) if callable(config.replace_text) else out

    return show, prefs, ns


def test_consecutive_languages_coexist_without_contamination(tmp_path):
    _game(tmp_path, ["Menu principal", "Dinheiro: [money]"])
    pl = ScriptedManager({"Menu principal": "Главное меню", "Dinheiro: __LNMOD_TOKEN_0__": "Деньги: __LNMOD_TOKEN_0__"})
    generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE, pl)
    es = ScriptedManager({"Menu principal": "Menú principal", "Dinheiro: __LNMOD_TOKEN_0__": "Dinero: __LNMOD_TOKEN_0__"})
    result = generate_interface_mod(str(tmp_path), "portuguese", "spanish", TranslationEngine.BING, es)
    assert {r.target_lang for r in es.requests} == {"es"}
    pl_data = json.loads((tmp_path / "game/tl/russian/linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert pl_data["mapping"]["Menu principal"] == "Главное меню"
    hook = Path(result.output_path).read_text(encoding="utf-8")
    show, prefs, _ = _hook_runtime(hook, "russian")
    assert show("Menu principal") == "Главное меню"
    assert show("Dinheiro: [money]", money=30) == "Деньги: 30"
    prefs.language = "spanish"
    assert show("Menu principal") == "Menú principal"
    prefs.language = "german"                      # language without MOD data → untouched
    assert show("Menu principal") == "Menu principal"
    prefs.language = None                          # original language is never touched
    assert show("Menu principal") == "Menu principal"


def test_hook_prefers_edited_json_and_survives_missing_loader(tmp_path):
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE,
                                    ScriptedManager({"Menu principal": "Главное меню"}))
    hook = Path(result.output_path).read_text(encoding="utf-8")
    edited = {"tl/russian/linguanova_mod_hook_data.json": {"mapping": {"Menu principal": "Menu startowe"}, "contexts": {}}}
    show, _, _ = _hook_runtime(hook, "russian", edited)
    assert show("Menu principal") == "Menu startowe"
    show, _, _ = _hook_runtime(hook, "russian")          # no JSON readable → embedded copy
    assert show("Menu principal") == "Главное меню"
    assert ": null" not in hook and "b85decode" not in hook


@pytest.mark.parametrize("lang", ["russian"])
def test_unicode_targets_round_trip_through_files_and_hook(tmp_path, lang, monkeypatch):
    target = resolve_language(lang)
    sample = "Главное меню"
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", lang, TranslationEngine.GOOGLE,
                                    ScriptedManager({"Menu principal": sample}))
    assert result.success, result.message
    data = json.loads((tmp_path / "game/tl" / target.renpy / "linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    assert data["mapping"]["Menu principal"] == sample and data["api_target"] == target.api
    hook = Path(result.output_path).read_text(encoding="utf-8")
    assert sample in hook
    show, _, _ = _hook_runtime(hook, target.renpy)
    assert show("Menu principal") == sample


def test_publish_rolls_back_when_a_replace_fails(tmp_path, monkeypatch):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text("old-a", "utf-8")
    b.write_text("old-b", "utf-8")
    real_replace = gen.os.replace
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr(gen.os, "replace", flaky)
    with pytest.raises(OSError):
        gen._publish({a: "new-a", b: "new-b"}, tmp_path / "bk")
    assert a.read_text("utf-8") == "old-a" and b.read_text("utf-8") == "old-b"
    assert not list(tmp_path.glob("*.tmp"))


def test_existing_native_translation_must_pass_the_same_policy(tmp_path):
    game = _game(tmp_path, ["Menu principal", "Carregar save"])
    tl = game / "tl" / "russian"
    tl.mkdir(parents=True)
    (tl / "strings.rpy").write_text(
        'translate russian strings:\n    old "Menu principal"\n    new "Главное меню"\n'
        '    old "Carregar save"\n    new "Carregar save"\n', encoding="utf-8")
    manager = ScriptedManager({"Carregar save": "Загрузить игру"})
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE, manager)
    assert [r.text for r in manager.requests] == ["Carregar save"]   # untranslated native "new" not reused
    assert result.translated == 2


# ── engines × five targets (SIMULATED engine; plumbing, files and hook) ──────

from src.ui_mod.engine_support import request_code, support as engine_support

ENGINES = [TranslationEngine.GOOGLE, TranslationEngine.BING, TranslationEngine.DEEPL,
           TranslationEngine.LIBRETRANSLATE, TranslationEngine.OPENAI, TranslationEngine.GEMINI]


def test_deepl_codes_fix_main_mapping_variants():
    assert request_code(TranslationEngine.DEEPL, resolve_language("russian"), "target") == "RU"
    assert request_code(TranslationEngine.DEEPL, resolve_language("portuguese"), "target") == "PT-PT"
    assert request_code(TranslationEngine.DEEPL, resolve_language("english"), "target") == "EN-US"
    assert request_code(TranslationEngine.OPENAI, resolve_language("russian"), "target") == "ru"
    assert request_code(TranslationEngine.GOOGLE, resolve_language("russian"), "target") == "ru"


def test_deepl_main_mapping_passes_mod_codes_through_unchanged():
    from src.core.translators.services import DeepLTranslator
    mapper = DeepLTranslator.__new__(DeepLTranslator)
    for lang in all_languages():
        code = request_code(TranslationEngine.DEEPL, lang, "target")
        assert mapper._map_lang(code, True) == code


def test_unsupported_engine_language_sends_nothing(tmp_path):
    _game(tmp_path, ["Menu principal"])
    manager = ScriptedManager({"Menu principal": "x"})
    result = generate_interface_mod(str(tmp_path), "portuguese", "meiteilon", TranslationEngine.DEEPL, manager)
    assert not result.success and manager.requests == []
    assert not (tmp_path / "game/tl/meiteilon").exists()


@pytest.mark.parametrize("engine", ENGINES, ids=lambda e: e.value)
def test_every_target_language_reaches_engine_files_and_hook(tmp_path, engine, monkeypatch):
    """For each of the five targets: engine code, tl/<folder>, JSON, readable hook, runtime lookup."""
    from src.ui_mod import quality
    # The engine is simulated, so its answer is a marker; acceptance rules are tested above.
    monkeypatch.setattr(gen, "validate_translation",
                        lambda s, t, target, source=None: quality.QualityVerdict("accepted"))
    checked = 0
    for lang in all_languages():
        if engine_support(engine, lang, "target")[0] == "unsupported":
            continue
        root = tmp_path / lang.renpy
        _game(root, ["Menu principal"])
        manager = ScriptedManager(default=lambda req: f"⟪{req.target_lang}⟫ ok")
        src = resolve_language("english" if lang.api == "pt" else "portuguese")
        result = generate_interface_mod(str(root), src.renpy, lang.renpy, engine, manager)
        assert result.success, (lang.renpy, result.message)
        expected = request_code(engine, lang, "target")
        assert {r.target_lang for r in manager.requests} == {expected}
        assert {r.source_lang for r in manager.requests} <= {request_code(engine, src, "source"), "auto"}
        data = json.loads((root / "game/tl" / lang.renpy / "linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
        assert data["api_target"] == lang.api and data["language"] == lang.renpy
        show, _, _ = _hook_runtime(Path(result.output_path).read_text(encoding="utf-8"), lang.renpy)
        assert show("Menu principal") == f"⟪{expected}⟫ ok"
        checked += 1
    assert checked == 5


def test_old_mod_native_files_are_not_reused_and_are_reported(tmp_path):
    game = _game(tmp_path, ["Menu principal"])
    tl = game / "tl" / "russian"
    tl.mkdir(parents=True)
    # Native file left by an earlier LinguaNova MOD build (contaminated text).
    (tl / "linguanova_mod_native_strings.rpy").write_text(
        'translate russian strings:\n    old "Menu principal"\n    new "главное меню"\n', encoding="utf-8")
    manager = ScriptedManager({"Menu principal": "Главное меню"})
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE, manager)
    assert [r.text for r in manager.requests] == ["Menu principal"]
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["legacy_mod_native_files"] == ["tl/russian/linguanova_mod_native_strings.rpy"]
    assert "WARNING" in result.message
    assert (tl / "linguanova_mod_native_strings.rpy").exists()   # never deleted by MOD


def test_hand_edit_in_manual_json_applies_in_game_without_regenerating(tmp_path):
    _game(tmp_path, ["Menu principal", "Carregar save"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE,
                                    ScriptedManager({"Menu principal": "Главное меню", "Carregar save": "Загрузить игру"}))
    hook = Path(result.output_path).read_text(encoding="utf-8")
    data = json.loads((tmp_path / "game/tl/russian/linguanova_mod_hook_data.json").read_text(encoding="utf-8"))
    payloads = {
        "tl/russian/linguanova_mod_hook_data.json": data,
        "tl/russian/linguanova_mod_manual.json": {"schema": 2, "mapping": {"Carregar save": "Запустить игру"}},
    }
    show, _, _ = _hook_runtime(hook, "russian", payloads)
    assert show("Carregar save") == "Запустить игру"    # hand edit wins
    assert show("Menu principal") == "Главное меню"      # rest untouched
    payloads["tl/russian/linguanova_mod_manual.json"] = "not json {"         # a damaged file is ignored
    show, _, _ = _hook_runtime(hook, "russian", payloads)
    assert show("Carregar save") == "Загрузить игру"


def test_hook_errors_never_stop_the_game(tmp_path):
    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE,
                                    ScriptedManager({"Menu principal": "Главное меню"}))
    from src.ui_mod.hook_check import make_env, python_body
    body = python_body(Path(result.output_path).read_text(encoding="utf-8"))

    def broken_screen(name):
        raise RuntimeError("screen system exploded")

    ns, config, _translator, _prefs = make_env("russian")
    ns["renpy"].get_screen = broken_screen
    del ns["renpy"].game.script            # no string table at all
    exec(compile(body, "hook", "exec"), ns, ns)
    for callback in config.start_callbacks:
        callback()                         # must log, not raise
    assert config.replace_text(12345) == 12345                     # non-text passes through
    assert config.replace_text("Texto desconocido") == "Texto desconocido"


def test_partial_run_is_reported_as_warning_not_success(tmp_path):
    _game(tmp_path, ["Menu principal", "Carregar save", "Nenhuma missão ativa no momento."])
    result = generate_interface_mod(str(tmp_path), "portuguese", "russian", TranslationEngine.GOOGLE,
                                    ScriptedManager({"Menu principal": "Главное меню"}))
    assert result.success and result.partial and result.pending == 2
    assert result.message.startswith("MOD generated PARTIALLY")
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["partial"] is True and report["pending"] == 2
    assert set(report["pending_texts"]) == {"Carregar save", "Nenhuma missão ativa no momento."}

    # Backend status: warning text with the pending count, never the "done" text.
    import importlib, sys, types
    if "PyQt6" not in sys.modules:
        try:
            importlib.import_module("PyQt6.QtCore")
        except Exception:
            pytest.skip("PyQt6 not available")
    from src.backend.app_backend import AppBackend
    logs = []
    stub = SimpleNamespace(
        _mod_running=True, _mod_status="", _mod_candidate_count=0, _mod_translated_count=0,
        _mod_rejected_count=0, _mod_coverage=0.0, _mod_output_path="", _mod_partial=False,
        modRunningChanged=SimpleNamespace(emit=lambda: None), modStatusChanged=SimpleNamespace(emit=lambda: None),
        modStatsChanged=SimpleNamespace(emit=lambda: None), modOutputPathChanged=SimpleNamespace(emit=lambda: None),
        logMessage=SimpleNamespace(emit=lambda level, msg: logs.append((level, msg))),
        progressChanged=SimpleNamespace(emit=lambda *a: None),
        statsDetailReady=SimpleNamespace(emit=lambda *a: None),
        _mod_unchanged_count=0, _mod_excluded_count=0,
        _t=lambda key, default, **kw: (key, default.format(**kw)),
        _complete_active_work=lambda: None,
    )
    AppBackend._on_mod_worker_finished.__get__(stub)(result)
    assert stub._mod_partial is True
    assert stub._mod_status[0] == "mod_status_generated_partial" and "2 could not be translated" in stub._mod_status[1]
    assert logs[0][0] == "warning" and all(level != "success" for level, _ in logs)
