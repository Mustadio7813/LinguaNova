# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for the LinguaNova audit of 2026-10-18.

Every test reproduces a failure seen in the user's runs on
"iNSight of you ver.13" (Ren'Py 8.0.3) with the exact strings involved.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.tag_structure import (
    introduces_replacement_char, tag_structure_error, tag_structure_regression,
)
from src.core.tl_parser import TLParser, get_translation_stats


# ── 1. Escaped quotes before a "with" word (SDK error log) ───────────────────

SDK_BLOCK = '''translate spanish chapter6_x:

    # s "Bring the \\"results\\" with you."
    s "Bring the \\"results\\" with you."

translate spanish newday_e_x:

    # e plan "Still \\"making babies\\" with Mr.Simmons?"
    e plan "Still \\"making babies\\" with Mr.Simmons?"

translate spanish ch2_x:

    # s "{size=+10}{b}Get your ass back here!!{/b}{/size}" with vpunch
    s "{size=+10}{b}Get your ass back here!!{/b}{/size}" with vpunch
'''


def _write(tmp_path, text, name="Chapter6.rpy"):
    path = tmp_path / "tl" / "spanish" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_escaped_quotes_are_part_of_the_text_not_a_with_clause(tmp_path):
    path = _write(tmp_path, SDK_BLOCK)
    parsed = TLParser().parse_file(str(path))
    originals = [e.original_text for e in parsed.entries]
    assert originals == [
        'Bring the "results" with you.',
        'Still "making babies" with Mr.Simmons?',
        "{size=+10}{b}Get your ass back here!!{/b}{/size}",
    ]


def test_rewrite_keeps_valid_renpy_syntax(tmp_path):
    path = _write(tmp_path, SDK_BLOCK)
    parser = TLParser()
    parsed = parser.parse_file(str(path))
    translations = {
        'Bring the "results" with you.': 'Trae los "resultados" contigo.',
        'Still "making babies" with Mr.Simmons?': '¿Sigues "haciendo bebés" con el Sr. Simmons?',
        "{size=+10}{b}Get your ass back here!!{/b}{/size}": "{size=+10}{b}¡Vuelve aquí!{/b}{/size}",
    }
    out = parser.update_translations(parsed, translations)
    assert '    s "Trae los \\"resultados\\" contigo."' in out
    assert '    e plan "¿Sigues \\"haciendo bebés\\" con el Sr. Simmons?"' in out
    assert '    s "{size=+10}{b}¡Vuelve aquí!{/b}{/size}" with vpunch' in out
    # The two corrupt forms from the error log can no longer be produced.
    assert '\\"" with you."' not in out and '?" with Mr.Simmons?"' not in out


def test_lines_damaged_by_the_old_bug_are_repaired_and_retranslated(tmp_path):
    damaged = '''translate spanish chapter6_x:

    # s "Bring the \\"results\\" with you."
    s "Y trae los \\"resultados\\"" with you."
'''
    path = _write(tmp_path, damaged)
    parser = TLParser()
    parsed = parser.parse_file(str(path))
    entry = parsed.entries[0]
    assert entry.original_text == 'Bring the "results" with you.'
    assert entry.needs_translation()          # the broken text is translated again
    assert parsed.needs_rewrite
    out = parser.update_translations(parsed, {})
    # Without a new translation the slot falls back to the source: valid syntax.
    assert '    s "Bring the \\"results\\" with you."' in out
    assert out.rstrip("\n").splitlines()[-1] == '    s "Bring the \\"results\\" with you."'
    assert '\\"" with you."' not in out


def test_unmatched_translation_line_is_never_dropped(tmp_path):
    text = '''translate spanish x:

    # e "Hello"
    e "Hola" with fade foo bar
'''
    path = _write(tmp_path, text)
    parser = TLParser()
    out = parser.update_translations(parser.parse_file(str(path)), {})
    assert 'e "Hola" with fade foo bar' in out


# ── 2. Empty slots are shown as EMPTY lines by Ren'Py ────────────────────────

def test_empty_slots_are_written_with_the_source_text(tmp_path):
    text = '''translate spanish es_butt5_a1f06532:

    # e "...sensorimotor-OH{image=h} rhythm neurofeedback t-training..."
    e ""

translate spanish strings:

    old "Skip"
    new ""
'''
    path = _write(tmp_path, text, "Es_events.rpy")
    parser = TLParser()
    parsed = parser.parse_file(str(path))
    assert parsed.needs_rewrite
    out = parser.update_translations(parsed, {})
    assert 'e "...sensorimotor-OH{image=h} rhythm neurofeedback t-training..."' in out
    assert 'new "Skip"' in out
    assert 'e ""' not in out and 'new ""' not in out


def test_stats_do_not_count_source_copies_as_translated(tmp_path):
    text = '''translate spanish a:

    # e "Hello there."
    e "Hola."

translate spanish b:

    # e "Argh!!!"
    e "Argh!!!"

translate spanish c:

    # e "Good night."
    e ""
'''
    path = _write(tmp_path, text, "s.rpy")
    stats = get_translation_stats([TLParser().parse_file(str(path))])
    assert stats["total"] == 3
    assert stats["translated"] == 1
    assert stats["same_as_source"] == 1
    assert stats["empty"] == 1
    assert stats["untranslated"] == 2
    assert round(stats["progress"], 1) == 33.3


# ── 3. Tag order (exe crash: "'/i' closes a text tag that isn't open") ───────

CASE01_SRC = "I've found this {i}Dude's{/i} profile."
CASE01_BAD = "Encontré el perfil {/i} de este {i}Dude."


def test_tag_order_mirrors_renpy_check():
    assert tag_structure_error(CASE01_SRC) is None
    assert tag_structure_error(CASE01_BAD).startswith("close_without_open")
    assert tag_structure_regression(CASE01_SRC, CASE01_BAD)
    assert tag_structure_regression(CASE01_SRC, "Encontré el perfil de este {i}Dude{/i}.") is None
    # Nested tags and self-closing tags (audit case 07 control, {image=h}, {w})
    assert tag_structure_regression("{size=+10}{b}Get!{/b}{/size}", "{size=+10}{b}¡Ven!{/b}{/size}") is None
    assert tag_structure_regression("{size=+10}{b}Get!{/b}{/size}", "{b}{size=+10}¡Ven!{/b}{/size}")
    assert tag_structure_regression("Hi{w} there{image=h}", "Hola{image=h} ahí{w}") is None
    assert tag_structure_regression("{{literal} {i}x{/i}", "{{literal} {i}y{/i}") is None
    # A game-specific tag closed in the source is treated as paired.
    assert tag_structure_regression("{shake}Boo{/shake}", "{/shake}Bu{shake}")


def test_main_guard_blocks_inverted_tags_and_replacement_chars():
    from src.core.pipeline.translating import classify_translation_corruption
    assert classify_translation_corruption(CASE01_SRC, CASE01_BAD) == "renpy_tag_order_invalid"
    assert classify_translation_corruption(CASE01_SRC, "Encontré el perfil de este {i}Dude{/i}.") is None
    src5 = "From trustworthy friendship to passionate love. Currently [em_love] out of 17."
    bad5 = "Desde una amistad de confianza hasta un amor apasionado. Actualmente ��[em_love] de 17."
    assert introduces_replacement_char(src5, bad5)
    assert classify_translation_corruption(src5, bad5) == "replacement_char"


def test_mod_validators_reject_case_01():
    from src.ui_mod.protect import structure_problem, validate_mod_translation
    from src.ui_mod.quality import validate_translation
    from src.ui_mod.languages import resolve_language
    assert structure_problem(CASE01_SRC, CASE01_BAD) == "tag_order_invalid"
    assert not validate_mod_translation(CASE01_SRC, CASE01_BAD)
    verdict = validate_translation(CASE01_SRC, CASE01_BAD, resolve_language("es"), resolve_language("en"))
    assert verdict.status == "rejected" and verdict.reason == "tag_order_invalid"


def test_existing_tl_with_inverted_tags_is_reopened():
    from src.core.pipeline.extraction import reopen_stale_tl_entries
    entry = SimpleNamespace(original_text=CASE01_SRC, translated_text=CASE01_BAD, file_path="x.rpy",
                            translation_id="id", line_number=1, compute_id=lambda: "id")
    tl_file = SimpleNamespace(entries=[entry], file_path="x.rpy")
    counts = reopen_stale_tl_entries([tl_file], None, None, lambda **kw: None)
    assert counts["reopened"] == 1 and entry.translated_text == ""


# ── 4. MOD: native "Skip" = "Skip" must not hide the MOD's "Saltar" ──────────

def test_mod_replaces_identity_native_translations(tmp_path):
    from src.core.translator import TranslationEngine
    from src.ui_mod.generator import generate_interface_mod
    from test_mod_language_contract import ScriptedManager, _game, _hook_runtime

    _game(tmp_path, ["Skip", "Menu principal"])
    manager = ScriptedManager({"Skip": "Saltar", "Menu principal": "Menú principal"})
    result = generate_interface_mod(str(tmp_path), "en", "spanish", TranslationEngine.BING, manager)
    hook = Path(result.output_path).read_text(encoding="utf-8")
    show, _prefs, ns = _hook_runtime(hook, "spanish",
                                     preexisting={"spanish": {"Skip": "Skip", "Menu principal": "Menú"}})
    assert show("Skip") == "Saltar"                 # identity entry replaced
    assert show("Menu principal") == "Menú"         # a real native translation is kept
    # The player never sees counters; the language list is names only.
    assert all(len(row) == 2 for row in ns["_lnmod_menu_languages"]())


def test_mod_report_explains_counters_and_pending_files(tmp_path):
    from src.core.translator import TranslationEngine
    from src.ui_mod.generator import generate_interface_mod
    from test_mod_language_contract import ScriptedManager, _game

    _game(tmp_path, ["Menu principal", "Carregar save", "OK"])
    progress = []
    manager = ScriptedManager({"Menu principal": "Menu główne"})
    result = generate_interface_mod(str(tmp_path), "portuguese", "polish", TranslationEngine.GOOGLE, manager,
                                    progress=lambda c, t, msg: progress.append((c, t, msg)))
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["candidates"] == report["translated"] + report["invariant"] + report["pending"]
    assert "counter_definitions" in report
    assert report["pending_files"] == 1
    (only_file, items), = report["pending_by_file"].items()
    assert only_file.endswith("screens.rpy") and {i["text"] for i in items} >= {"Carregar save"}
    # The last progress line is the final result, not "retrying N strings".
    assert progress[-1][0] == progress[-1][1] == report["candidates"]
    assert "pending" in progress[-1][2]


def test_mod_reuses_dialogue_translations_from_tl(tmp_path):
    from src.ui_mod.scanner import read_existing_tl_translations
    game = tmp_path / "game"
    tl = game / "tl" / "spanish"
    tl.mkdir(parents=True)
    (tl / "Carl_scenes.rpy").write_text(
        'translate spanish gloria_subway_menu_c14ca3d7:\n\n'
        '    # "Some events can be blocked behind {b}general progress{/b}."\n'
        '    "Algunos eventos pueden estar bloqueados detrás del {b}progreso general{/b}."\n',
        encoding="utf-8")
    found = read_existing_tl_translations(game, "spanish")
    assert found["Some events can be blocked behind {b}general progress{/b}."].startswith("Algunos eventos")


# ── 5. Language picker when the game has no selector ─────────────────────────

def _config():
    from src.utils.config import ConfigManager
    return ConfigManager()


def test_fallback_picker_when_game_has_no_language_selector(tmp_path):
    from src.core.pipeline.saving import create_language_init_file
    game = tmp_path / "game"
    (game / "tl" / "spanish").mkdir(parents=True)
    (game / "tl" / "spanish" / "script.rpy").write_text("translate spanish strings:\n", encoding="utf-8")
    (game / "screens.rpy").write_text("screen preferences():\n    vbox:\n        text \"Prefs\"\n", encoding="utf-8")
    logs = []
    result = create_language_init_file(str(game), "spanish", _config(), lambda lvl, msg: logs.append((lvl, msg)))
    assert result["status"] == "fallback_picker"
    helper = (game / "zzz_linguanova_language_menu.rpy").read_text(encoding="utf-8-sig")
    assert '"spanish": "Español"' in helper          # id kept, visible name shown
    assert "Language(_lntl_code)" in helper and "Language(None)" in helper
    code = "\n".join(line for line in helper.splitlines() if not line.lstrip().startswith("#"))
    assert "config.language" not in code and "change_language" not in code   # nothing is forced
    assert "%" not in helper                          # no counters for the player
    # Python part compiles (Ren'Py init python body).
    body = helper.split("init 950 python:\n", 1)[1].split("\nscreen ", 1)[0]
    compile("\n".join(line[4:] for line in body.splitlines()), "picker", "exec")
    assert logs and logs[-1][0] == "info"


def test_no_second_picker_when_the_game_has_its_own(tmp_path):
    from src.core.pipeline.saving import create_language_init_file
    game = tmp_path / "game"
    (game / "tl" / "spanish").mkdir(parents=True)
    (game / "tl" / "spanish" / "script.rpy").write_text("translate spanish strings:\n", encoding="utf-8")
    (game / "screens.rpy").write_text(
        "screen custom_languages():\n    vbox:\n"
        "        imagebutton idle \"en.png\" action Language(None)\n"
        "        imagebutton idle \"de.png\" action Language(\"german\")\n", encoding="utf-8")
    result = create_language_init_file(str(game), "spanish", _config(), lambda *a: None)
    assert result["status"] == "not_found"
    assert not (game / "zzz_linguanova_language_menu.rpy").exists()


# ── 6. Pipeline: source copies retried, honest completion stats ─────────────

def _pipeline_stub():
    from src.core.pipeline.orchestrator import TranslationPipeline
    stub = SimpleNamespace(
        tl_parser=TLParser(), diagnostic_report=SimpleNamespace(mark_written=lambda *a: None),
        logger=SimpleNamespace(debug=lambda *a, **k: None),
        log_message=SimpleNamespace(emit=lambda *a: None),
        config=SimpleNamespace(get_log_text=lambda key, default=None, **kw: (default or key).format(**kw)),
    )
    for name in ("_collect_entries_to_translate", "_save_tl_files", "_completion_stats", "_completion_message"):
        setattr(stub, name, getattr(TranslationPipeline, name).__get__(stub))
    stub._quote_balance_issues = TranslationPipeline._quote_balance_issues
    return stub


def test_quote_check_flags_the_line_from_the_sdk_error_log(tmp_path):
    from src.core.pipeline.orchestrator import TranslationPipeline
    bad = _write(tmp_path, 'translate spanish x:\n\n    # s "a"\n    s "Y trae los \\"resultados\\"" with you."\n', "bad.rpy")
    good = _write(tmp_path, SDK_BLOCK, "good.rpy")
    assert TranslationPipeline._quote_balance_issues(str(bad)) == ["bad.rpy:4"]
    assert TranslationPipeline._quote_balance_issues(str(good)) == []


def test_game_flow_retries_source_copies_and_reports_partial(tmp_path):
    text = '''translate spanish a:

    # e "Hello there."
    e "Hello there."

translate spanish b:

    # e "Good night."
    e ""
'''
    path = _write(tmp_path, text, "s.rpy")
    stub = _pipeline_stub()
    tl_files = [stub.tl_parser.parse_file(str(path))]
    entries, copies = stub._collect_entries_to_translate(tl_files)
    assert copies == 1 and len(entries) == 2
    translations = {"Hello there.": "Hola."}     # "Good night." failed in the engine
    stub._run_counts = {"engine_failed": 1, "guard_blocked": 0}
    saved, failed = stub._save_tl_files(tl_files, translations)
    assert saved == 1 and failed == []
    out = path.read_text(encoding="utf-8-sig")
    assert 'e "Hola."' in out and 'e "Good night."' in out and 'e ""' not in out
    stats = stub._completion_stats([stub.tl_parser.parse_file(str(path))], failed)
    assert stats["translated"] == 1 and stats["same_as_source"] == 1
    assert stats["partial"] is True and stats["pending"] == 1
    message = stub._completion_message(stats, saved)
    assert message.startswith("Translation finished with pending lines.")
    assert "1/2" in message


# ── 7. Encoding: no U+FFFD from mixed files, no needless rewrites ────────────

def test_mixed_utf8_file_is_read_without_replacement_chars(tmp_path):
    from src.utils.encoding import normalize_to_utf8_sig, read_text_safely
    path = tmp_path / "mixed.rpy"
    good = "translate spanish strings:\n    old \"Love\"\n    new \"Amor ñandú\"\n".encode("utf-8")
    bad_line = "    new \"Actualmente “mucho” [em_love]\"\n".encode("cp1252")
    path.write_bytes(good * 3 + bad_line)
    text = read_text_safely(path)
    assert "�" not in text and "“mucho”" in text and "ñandú" in text
    assert normalize_to_utf8_sig(path) is True           # rewritten once, as UTF-8-SIG
    assert normalize_to_utf8_sig(path) is False          # already normal: untouched
    assert "�" not in path.read_text(encoding="utf-8-sig")


# ── 8. End to end: TL-folder flow on an SDK template (offline fake engine) ───

def test_tl_mode_end_to_end_on_sdk_template(tmp_path, monkeypatch):
    from src.core.pipeline.orchestrator import TranslationPipeline, PipelineStage
    from src.core.translator import TranslationEngine, TranslationManager
    from src.core.translators.base import TranslationResult
    from src.utils.config import ConfigManager

    tl_dir = tmp_path / "game" / "tl" / "spanish"
    tl_dir.mkdir(parents=True)
    (tl_dir / "Chapter6.rpy").write_text(SDK_BLOCK + '''
translate spanish tutorial1_279d29d9:

    # s "I've found this {i}Dude's{/i} profile."
    s "I've found this {i}Dude's{/i} profile."

translate spanish strings:

    old "Skip"
    new "Skip"
''', encoding="utf-8")

    answers = {
        'Bring the "results" with you.': 'Trae los "resultados" contigo.',
        "{size=+10}{b}Get your ass back here!!{/b}{/size}": "{size=+10}{b}¡Vuelve aquí!{/b}{/size}",
        "I've found this {i}Dude's{/i} profile.": "Encontré el perfil {/i} de este {i}Dude.",   # inverted tags
        "Skip": "Saltar",
        # 'Still "making babies" with Mr.Simmons?' -> engine error
    }

    async def fake_batch(self, requests):
        out = []
        for req in requests:
            src = (req.metadata or {}).get("original_text", req.text)
            ans = answers.get(src)
            out.append(TranslationResult(original_text=src, translated_text=ans or "", source_lang="en",
                                         target_lang="es", engine=TranslationEngine.GOOGLE,
                                         success=ans is not None, error=None if ans else "HTTP 500",
                                         metadata=dict(req.metadata or {})))
        return out

    monkeypatch.setattr(TranslationManager, "translate_batch", fake_batch)
    config = ConfigManager()
    config.translation_settings.use_global_cache = False
    manager = TranslationManager(config_manager=config)
    monkeypatch.setattr(manager, "get_cached_translation", lambda *a, **k: None, raising=False)
    pipeline = TranslationPipeline(config=config, translation_manager=manager)
    pipeline.configure(game_exe_path=str(tl_dir), target_language="spanish", source_language="en",
                       engine=TranslationEngine.GOOGLE, auto_unren=False, is_tl_mode=True)
    results = []
    pipeline.finished.connect(results.append)
    pipeline.run()
    result = results[0]
    assert result.success and result.stage == PipelineStage.COMPLETED, result.message
    out = (tl_dir / "Chapter6.rpy").read_text(encoding="utf-8-sig")
    assert '    s "Trae los \\"resultados\\" contigo."' in out
    assert '    s "{size=+10}{b}¡Vuelve aquí!{/b}{/size}" with vpunch' in out
    assert '    e plan "Still \\"making babies\\" with Mr.Simmons?"' in out     # failed: source kept
    assert "Encontré el perfil {/i}" not in out                              # blocked by the guard
    assert '    s "I\'ve found this {i}Dude\'s{/i} profile."' in out
    assert '    new "Saltar"' in out
    stats = result.stats
    assert stats["translated"] == 3 and stats["same_as_source"] == 2
    assert stats["engine_failed"] == 1 and stats["guard_blocked"] == 1
    assert stats["partial"] is True and stats["syntax_issues"] == 0
    assert "3/5" in result.message
    assert TranslationPipeline._quote_balance_issues(str(tl_dir / "Chapter6.rpy")) == []


def test_mod_button_lives_in_menus_on_renpy_8(tmp_path):
    """Ren'Py hides overlay screens in menus (suppress_overlay); on Ren'Py 8 the
    button is an always-shown screen visible only in main/game menus."""
    from src.core.translator import TranslationEngine
    from src.ui_mod.generator import generate_interface_mod
    from src.ui_mod.hook_check import make_env
    from src.ui_mod.ui_mod_hook_template import python_body
    from test_mod_language_contract import ScriptedManager, _game

    _game(tmp_path, ["Menu principal"])
    result = generate_interface_mod(str(tmp_path), "portuguese", "spanish", TranslationEngine.GOOGLE,
                                    ScriptedManager({"Menu principal": "Menú principal"}))
    hook = Path(result.output_path).read_text(encoding="utf-8")
    ns, config, _translator, _prefs = make_env("spanish")
    config.always_shown_screens = []
    exec(compile(python_body(hook), "hook", "exec"), ns, ns)
    assert "lnmod_language_button" in config.always_shown_screens
    assert "lnmod_language_button" not in config.overlay_screens
    ns["main_menu"], ns["_menu"] = False, False
    assert ns["_lnmod_show_button"]() is False          # during play: Shift+L only
    ns["_menu"] = True
    assert ns["_lnmod_show_button"]() is True           # game menu


def test_merge_keeps_new_strings_that_share_a_prefix_before_an_escaped_quote():
    from src.core.pipeline.extraction import merge_tl_content
    existing = 'translate spanish strings:\n\n    old "Say \\"hi\\" now"\n    new "Say \\"hi\\" now"\n'
    new = 'translate spanish strings:\n\n    old "Say \\"bye\\" later"\n    new ""\n'
    merged = merge_tl_content(existing, new, "spanish")
    assert 'old "Say \\"bye\\" later"' in merged
    again = merge_tl_content(merged, new, "spanish")   # no duplicate on the next run
    assert again.count('old "Say \\"bye\\" later"') == 1
