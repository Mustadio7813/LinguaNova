# -*- coding: utf-8 -*-
"""
Regression tests for escaped literal brackets (v2.8.17).

Ren'Py writes a menu label that should show brackets as "\\[Sleep until the next
morning\\]". Its lexer turns that source escape into `[[` in the runtime string
(renpy/lexer.py, dequote: "\\[" -> "[["), and `[[` renders as a single literal
`[`. So the label is display text — never interpolation.

Four independent components each carried their own `\\[[^\\]]+\\]` rule and
therefore each mistook such a label for a variable: the parser refused to
extract it, the output formatter skipped it, the corruption guard reverted its
translation, and the protector packed the whole sentence into one placeholder so
the words never reached the engine. FunTanariZ 1.12 has 309 of these labels
across 24 files, all of which stayed English.
"""

import pytest

from src.core.output_formatter import RenPyOutputFormatter
from src.core.parser import RenPyParser
from src.core.pipeline.translating import classify_translation_corruption
from src.core.syntax_guard import protect_renpy_syntax, restore_renpy_syntax

# The forms the same label takes along the pipeline.
SOURCE_FORM = '"\\[Sleep until the next morning\\]"'   # as written in the .rpy
RUNTIME_FORM = "[[Sleep until the next morning]"       # after Ren'Py-style unescaping
RENDERED_FORM = "[Sleep until the next morning]"       # what the player sees


@pytest.fixture(scope="module")
def parser():
    return RenPyParser()


@pytest.fixture(scope="module")
def formatter():
    return RenPyOutputFormatter()


class TestParserAcceptsLabels:
    @pytest.mark.parametrize("text", [
        RUNTIME_FORM,
        RENDERED_FORM,
        "\\[Sleep until the next morning\\]",
        "[[Take her to the police station]",
        '[[Do "Release Exchange"]',
        "[[Weight Bench Exercise] (-$100) (+3 Fitness)",
    ])
    def test_bracketed_phrases_are_translatable(self, parser, text):
        assert parser.is_meaningful_text(text) is True

    @pytest.mark.parametrize("text", [
        "[player_name]",      # a variable
        "[item]",             # a variable
        "[config.name]",      # attribute access
        "[a + b]",            # an expression
        "[get_name()]",       # a call
        "[x, y]",             # an argument list
        "[item 3]",           # digits mark it technical
    ])
    def test_real_interpolation_is_still_rejected(self, parser, text):
        assert parser.is_meaningful_text(text) is False

    def test_menu_choice_is_extracted_from_a_script(self, parser, tmp_path):
        script = tmp_path / "bedroom.rpy"
        script.write_text(
            'label test:\n\nmenu:\n\n'
            '    "\\[Sleep until the next morning\\]":\n        jump a\n\n'
            '    "Cancel.":\n        jump b\n',
            encoding="utf-8",
        )
        texts = [e.get("text") for e in parser.extract_text_entries(str(script))]
        assert RUNTIME_FORM in texts, "the escaped label must be extracted"
        assert "Cancel." in texts


class TestProtectionExposesTheWords:
    def test_only_the_escape_is_protected(self):
        protected, placeholders = protect_renpy_syntax(RUNTIME_FORM)
        assert "Sleep until the next morning" in protected, "the engine must see the words"
        assert restore_renpy_syntax(protected, placeholders) == RUNTIME_FORM

    def test_a_real_variable_is_still_hidden(self):
        protected, placeholders = protect_renpy_syntax("Hello [player_name]!")
        assert "player_name" not in protected
        assert restore_renpy_syntax(protected, placeholders) == "Hello [player_name]!"

    def test_backslash_escape_round_trips(self):
        text = "\\[Sleep until the next morning\\]"
        protected, placeholders = protect_renpy_syntax(text)
        assert "Sleep until the next morning" in protected
        assert restore_renpy_syntax(protected, placeholders) == text

    def test_complete_double_pair_keeps_its_atomic_handling(self):
        text = "[[Phone]]"
        protected, placeholders = protect_renpy_syntax(text)
        assert restore_renpy_syntax(protected, placeholders) == text


class TestOutputFormatterKeepsLabels:
    @pytest.mark.parametrize("text", [RUNTIME_FORM, RENDERED_FORM])
    def test_label_is_not_skipped(self, formatter, text):
        assert formatter._should_skip_translation(text) is False

    def test_variable_only_string_is_still_skipped(self, formatter):
        assert formatter._should_skip_translation("[player_name]") is True


class TestCorruptionGuardAllowsTheTranslation:
    def test_translated_label_is_not_reverted(self):
        assert classify_translation_corruption(
            RUNTIME_FORM, "[[Ertesi sabaha kadar uyu]"
        ) is None

    def test_a_renamed_variable_is_still_caught(self):
        assert classify_translation_corruption(
            "Hello [name]!", "Merhaba [isim]!"
        ) == "placeholder_set_mismatch"

    def test_a_preserved_variable_passes(self):
        assert classify_translation_corruption(
            "Press [key] now", "Şimdi [key] bas"
        ) is None
