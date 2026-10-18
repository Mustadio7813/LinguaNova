# -*- coding: utf-8 -*-
"""
Tests for v2.8.17 mixed-case underscore identifier filtering.

Covers the pending discovery from the 2026-09-16 handover report:
  - is_meaningful_text() rejects Mixed_Case identifier strings with underscores
    (u2_Fire_And_Ice, alt_K_RETURN) that previously slipped through the
    all-lowercase snake_case filter.
  - RenPyOutputFormatter._should_skip_translation() rejects the same tokens.
  - deep_scan_strings_ast() drops docstrings, hasattr/getattr attribute-name
    strings, and subscript keys while preserving real dialogue.
"""

import tempfile
from pathlib import Path

import pytest

from src.core.output_formatter import RenPyOutputFormatter
from src.core.parser import RenPyParser


@pytest.fixture
def fmt():
    return RenPyOutputFormatter()


@pytest.fixture
def parser():
    return RenPyParser()


# ==================================================================
# 1. PARSER: is_meaningful_text rejects mixed underscore identifiers
# ==================================================================
class TestParserMixedIdentifier:
    @pytest.mark.parametrize("text", [
        "u2_Fire_And_Ice",
        "alt_K_RETURN",
        "Mixed_Snake_Case",
        "u3_Bruce_Did_What",
        "u17_Favor_Of_The_Void",
        "shift_K_INSERT",
        "meta_K_LEFT",
        "osctrl_K_BACKSPACE",
        "game_state",          # already-lowercase (regression)
        "player_name",
    ])
    def test_mixed_identifier_rejected(self, parser, text):
        assert parser.is_meaningful_text(text) is False, f"Should reject: {text}"

    @pytest.mark.parametrize("text", [
        "Hello world",
        "You have a fire and ice potion.",
        "Save Game",
        "Return",
        "I can't believe it!",
        "{b}Important{/b} news.",
    ])
    def test_real_text_still_allowed(self, parser, text):
        assert parser.is_meaningful_text(text) is True, f"Should allow: {text}"


# ==================================================================
# 2. FORMATTER: _should_skip_translation rejects mixed identifiers
# ==================================================================
class TestFormatterMixedIdentifier:
    @pytest.mark.parametrize("text", [
        "u2_Fire_And_Ice",
        "alt_K_RETURN",
        "Mixed_Snake_Case",
        "meta_K_LEFT",
        "shift_K_INSERT",
    ])
    def test_mixed_identifier_skipped(self, fmt, text):
        assert fmt._should_skip_translation(text) is True, f"Should skip: {text}"

    @pytest.mark.parametrize("text", [
        "The Dark Forest",
        "A New Beginning",
        "Save Game",
        "Continue",
    ])
    def test_real_text_not_skipped(self, fmt, text):
        assert fmt._should_skip_translation(text) is False, f"Should NOT skip: {text}"


# ==================================================================
# 3. DEEP SCAN: docstrings + hasattr attribute names are excluded
# ==================================================================
class TestDeepScanIdentifierFilter:
    def test_deep_scan_filters_docstrings_and_attribute_calls(self, parser):
        code = '''init python:
    def foo():
        """This docstring should never be translated."""
        return "Hello user"

    if hasattr(store, 'u2_Fire_And_Ice'):
        renpy.say("e", "You have a fire and ice potion.")
'''
        with tempfile.NamedTemporaryFile("w", suffix=".rpy", delete=False, encoding="utf-8") as tf:
            tf.write(code)
            path = tf.name

        try:
            entries = parser.deep_scan_strings_ast(path)
            texts = [e["text"] for e in entries]
            assert "Hello user" in texts
            assert "You have a fire and ice potion." in texts
            assert "This docstring should never be translated." not in texts
            assert "u2_Fire_And_Ice" not in texts
        finally:
            Path(path).unlink(missing_ok=True)

    def test_deep_scan_filters_subscript_keys(self, parser):
        code = '''init python:
    val = store['u17_Favor_Of_The_Void']
    renpy.say("n", "The void favors you.")
'''
        with tempfile.NamedTemporaryFile("w", suffix=".rpy", delete=False, encoding="utf-8") as tf:
            tf.write(code)
            path = tf.name

        try:
            entries = parser.deep_scan_strings_ast(path)
            texts = [e["text"] for e in entries]
            assert "The void favors you." in texts
            assert "u17_Favor_Of_The_Void" not in texts
        finally:
            Path(path).unlink(missing_ok=True)


# ==================================================================
# 4. RTL & CJK: legitimate non-Latin dialogue is NOT skipped as corruption
# ==================================================================
class TestNonLatinNotSkipped:
    @pytest.mark.parametrize("text", [
        "مرحبا",                                   # Arabic: hello (short word)
        "مرحبا بكم في هذه اللعبة الرائعة",           # Arabic sentence
        "به بازی خوش آمدید",                         # Persian sentence
        "ברוכים הבאים למשחק",                       # Hebrew sentence
        "こんにちは",                                # Japanese: hello (short word)
        "セーブ",                                   # Japanese: save (UI label)
        "このゲームをお楽しみください",                 # Japanese sentence
    ])
    def test_non_latin_not_skipped(self, fmt, text):
        assert fmt._should_skip_translation(text) is False, f"Should NOT skip: {text}"

    def test_replacement_char_still_skipped(self, fmt):
        # Corruption detection must still catch replacement characters.
        assert fmt._should_skip_translation("z\uFFFDX\uFFFD") is True
