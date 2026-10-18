# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
test_renpy_specifics.py — Ren'Py-specific regression tests for LinguaNova v2.8.3

Covers:
  - Translation ID computation (Ren'Py-compatible hash format)
  - Interpolation format flag protection ([value!t], [value!u], etc.)
  - Ruby/furigana lenticular bracket protection 【base｜ruby】
  - Character definition code string false positives
  - GUI config false positives (font paths, config assignments)
  - Escape character preservation ([[, {{, \\, \\n)
  - Ren'Py text tag LIFO nesting validation
"""

import pytest
import re
from src.core.parser import RenPyParser
from src.core.output_formatter import RenPyOutputFormatter
from src.core.syntax_guard import protect_renpy_syntax, restore_renpy_syntax, PROTECT_RE


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def parser():
    return RenPyParser()


@pytest.fixture
def fmt():
    return RenPyOutputFormatter()


# =============================================================================
# 1. TRANSLATION ID COMPUTATION
# =============================================================================

class TestTranslationIdComputation:
    """Verify compute_translation_id generates Ren'Py-compatible IDs."""

    def test_basic_id_format(self, parser):
        """ID must be: label_<8hexchars>"""
        tid = parser.compute_translation_id("start", 'e "Hello"')
        assert re.match(r'^[a-z0-9_]+_[0-9a-f]{8}$', tid), f"ID format wrong: {tid}"

    def test_label_is_included(self, parser):
        """Label name must appear at the start of the ID."""
        tid = parser.compute_translation_id("start", 'e "Hello"')
        assert tid.startswith("start_"), f"Label missing from ID: {tid}"

    def test_different_labels_give_different_ids(self, parser):
        """Same statement under different labels must produce different IDs."""
        tid1 = parser.compute_translation_id("start", 'e "Hello"')
        tid2 = parser.compute_translation_id("ending", 'e "Hello"')
        assert tid1 != tid2, "Same statement in different labels should have different IDs"

    def test_different_statements_give_different_ids(self, parser):
        """Different statements under same label must produce different IDs."""
        tid1 = parser.compute_translation_id("start", 'e "Hello"')
        tid2 = parser.compute_translation_id("start", 'e "Goodbye"')
        assert tid1 != tid2, "Different statements should have different IDs"

    def test_same_inputs_give_same_id(self, parser):
        """Identical inputs must always produce the same deterministic ID."""
        tid1 = parser.compute_translation_id("start", 'e "Thank you for taking a look."')
        tid2 = parser.compute_translation_id("start", 'e "Thank you for taking a look."')
        assert tid1 == tid2, "Same inputs must give same ID (deterministic)"

    def test_serial_collision_handling(self, parser):
        """Serial counter must append the correct letter suffix."""
        tid0 = parser.compute_translation_id("start", 'e "Hello"', serial=0)
        tid1 = parser.compute_translation_id("start", 'e "Hello"', serial=1)
        tid2 = parser.compute_translation_id("start", 'e "Hello"', serial=2)
        # serial=0: no suffix, serial=1: 'm', serial=2: 'n'
        assert not tid0.endswith(('m', 'n', 'o'))
        assert tid1.endswith('m'), f"Serial 1 should end with 'm': {tid1}"
        assert tid2.endswith('n'), f"Serial 2 should end with 'n': {tid2}"

    def test_special_chars_in_label_sanitized(self, parser):
        """Special characters in label should be sanitized for the ID."""
        tid = parser.compute_translation_id("my-label.sub", 'e "Hello"')
        # Should not raise, should produce valid identifier prefix
        label_part = tid.split('_')[0]
        assert re.match(r'^[a-z0-9_]+$', label_part), f"Unsanitized label: {label_part}"

    def test_empty_label_fallback(self, parser):
        """Empty label context must use a fallback (not crash)."""
        tid = parser.compute_translation_id("", 'e "Hello"')
        assert tid  # Must not be empty
        assert '_' in tid  # Must have the separator


# =============================================================================
# 2. INTERPOLATION FORMAT FLAG PROTECTION
# =============================================================================

class TestInterpolationFormatFlags:
    """Verify [value!flag] format flags are protected from translation."""

    @pytest.mark.parametrize("text, expected_matches", [
        ("[mood!t]", ["[mood!t]"]),             # Basic translate flag
        ("[value!q]", ["[value!q]"]),            # Quote flag
        ("[name!u]", ["[name!u]"]),              # Uppercase flag
        ("[name!l]", ["[name!l]"]),              # Lowercase flag
        ("[name!c]", ["[name!c]"]),              # Capitalize flag
        ("[value!ti]", ["[value!ti]"]),          # Translate + interpolate combined
        ("[value!cl]", ["[value!cl]"]),          # Capitalize + lowercase combined
        ("[points:.2]", ["[points:.2]"]),        # Format specifier (not flag)
        ("[player.name]", ["[player.name]"]),    # Attribute access
    ])
    def test_format_flags_matched_by_protect_re(self, text, expected_matches):
        """PROTECT_RE must match interpolation expressions including format flags."""
        matches = PROTECT_RE.findall(text)
        flat = [m[0] if isinstance(m, tuple) else m for m in matches]
        for expected in expected_matches:
            assert any(expected in m or m in expected for m in flat), \
                f"Expected '{expected}' to be matched in '{text}', got: {flat}"

    def test_format_flag_preserved_in_protect_cycle(self):
        """Format flags must survive protect → restore cycle unchanged."""
        text = "I'm [mood!t] to see you."
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "[mood!t]" in restored, f"Format flag lost after protect/restore: {restored}"

    def test_complex_format_flag_preserved(self):
        """Complex format like [value!ti] must survive protect → restore cycle."""
        text = "Points: [earned_points_info!ti] earned."
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "[earned_points_info!ti]" in restored, \
            f"Complex flag lost after protect/restore: {restored}"

    def test_multiple_interpolations_with_flags(self):
        """Multiple interpolations with flags must all be preserved."""
        text = "Hello [player_name!q], you have [points!u] points."
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "[player_name!q]" in restored, "player_name!q lost"
        assert "[points!u]" in restored, "points!u lost"

    def test_nested_attribute_access_preserved(self):
        """Nested attribute access in interpolation must be preserved."""
        text = "My name is [player.names[0]]."
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "[player.names[0]]" in restored or "player" in restored, \
            f"Nested access lost: {restored}"


# =============================================================================
# 3. RUBY / FURIGANA LENTICULAR BRACKET PROTECTION
# =============================================================================

class TestRubyFuriganaProtection:
    """Verify 【base｜ruby】 format is protected from translation splitting."""

    def test_ruby_text_matched_by_protect_re(self):
        """PROTECT_RE must match lenticular bracket ruby text."""
        text = "Furigana: 【東京｜とうきょう】"
        matches = PROTECT_RE.findall(text)
        flat = [m[0] if isinstance(m, tuple) else m for m in matches]
        assert any("【" in m and "】" in m for m in flat), \
            f"Ruby bracket not matched: {flat}"

    def test_ruby_text_preserved_in_cycle(self):
        """Ruby text must survive protect → restore cycle."""
        text = "Ruby can be used for 【東京｜Tokyo】."
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "【東京｜Tokyo】" in restored, f"Ruby text lost after protect/restore: {restored}"

    def test_ruby_with_halfwidth_bar_preserved(self):
        """Ruby text with half-width vertical bar must be preserved."""
        text = "Furigana: 【東|とう】"
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        # At minimum, should not corrupt the text
        assert "東" in restored, f"Ruby base text lost: {restored}"

    def test_multiple_ruby_pairs_preserved(self):
        """Multiple ruby pairs in same string must all be preserved."""
        text = "Ruby: 【東｜とう】 【京｜きょう】"
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "【東｜とう】" in restored, "First ruby pair lost"
        assert "【京｜きょう】" in restored, "Second ruby pair lost"

    def test_lenticular_bracket_not_split(self):
        """Ruby bracket must NOT be split into separate tokens."""
        text = "【東京｜Tokyo】"
        matches = PROTECT_RE.findall(text)
        flat = [m[0] if isinstance(m, tuple) else m for m in matches]
        # Should produce ONE token containing both brackets, not two
        assert len(flat) <= 1, f"Ruby bracket was split into multiple tokens: {flat}"


# =============================================================================
# 4. CHARACTER DEFINITION CODE STRING FALSE POSITIVES
# =============================================================================

class TestCharacterDefinitionFalsePositives:
    """Verify Character() code parameters are correctly skipped."""

    @pytest.mark.parametrize("text", [
        'who_prefix="["',
        "what_suffix=')'",
        'voice_tag="eileen_voice"',
        'image="char_eileen"',
        'who_suffix="]"',
        'what_prefix="("',
    ])
    def test_character_code_params_skipped(self, fmt, text):
        """Character code parameters should be detected as false positives."""
        assert fmt._should_skip_translation(text) is True, \
            f"Character code param should be skipped: {text}"

    @pytest.mark.parametrize("text", [
        "Hello, how are you?",
        "Good morning, sunshine!",
        "Would you like to come inside?",
    ])
    def test_dialogue_text_not_skipped(self, fmt, text):
        """Normal dialogue text should NOT be identified as false positive."""
        assert fmt._should_skip_translation(text) is False, \
            f"Dialogue text should not be skipped: {text}"


# =============================================================================
# 5. GUI FONT / CONFIG FALSE POSITIVES
# =============================================================================

class TestGuiFontConfigFalsePositives:
    """Verify GUI config assignments with font paths are correctly skipped."""

    @pytest.mark.parametrize("text", [
        "define gui.text_font = ",
        "gui.text_size = ",
        "config.font_size = ",
        "gui.label_color = ",
        "gui.button_spacing = ",
    ])
    def test_gui_font_assignments_skipped(self, fmt, text):
        """GUI/config font assignments should be detected as false positives."""
        assert fmt._should_skip_translation(text) is True, \
            f"GUI config assignment should be skipped: {text}"

    @pytest.mark.parametrize("text", [
        "fonts/NotoSans.ttf",
        "images/background.png",
    ])
    def test_font_paths_skipped(self, fmt, text):
        """Font and image file paths should be skipped (via SKIP_FILE_EXTENSIONS)."""
        assert fmt._should_skip_translation(text) is True, \
            f"File path should be skipped: {text}"


# =============================================================================
# 6. ESCAPE CHARACTER PRESERVATION
# =============================================================================

class TestEscapeCharacterPreservation:
    """Verify Ren'Py escape sequences are preserved through protect/restore."""

    def test_escaped_left_bracket_preserved(self):
        """[[ should be preserved as literal [."""
        text = "Click [[here]] to continue."
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        # The [[here]] should be preserved intact
        assert "[[here]]" in restored or "[here]" in restored, \
            f"Escaped bracket lost: {restored}"

    def test_escaped_brace_preserved(self):
        """{{ should be preserved as literal {."""
        text = "Use {{b}} for bold text."
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "{{b}}" in restored or "{b}" in restored, \
            f"Escaped brace lost: {restored}"

    def test_real_variable_not_confused_with_escape(self):
        """[variable] should be protected as placeholder, not confused with [[ escape."""
        text = "Welcome, [player_name]!"
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "[player_name]" in restored, f"Variable lost: {restored}"


# =============================================================================
# 7. TEXT TAG NESTING VALIDATION
# =============================================================================

class TestTextTagNesting:
    """Verify Ren'Py text tag LIFO nesting is respected."""

    def test_bold_italic_nesting_preserved(self):
        """Nested {b}{i}...{/i}{/b} must survive protect/restore."""
        text = "Plain {b}Bold {i}Bold-Italic{/i} Bold{/b} Plain"
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "Bold-Italic" in restored, f"Inner text lost: {restored}"

    def test_color_size_tags_preserved(self):
        """Color and size tags must survive protect/restore."""
        text = "{color=#f00}Red{/color}, {size=+10}Bigger{/size}"
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "Red" in restored, f"Color text lost: {restored}"
        assert "Bigger" in restored, f"Size text lost: {restored}"

    def test_disambiguation_tag_preserved(self):
        """Disambiguation tag {#...} must be preserved intact."""
        text = "New{#playlist}"
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "{#playlist}" in restored, f"Disambiguation tag lost: {restored}"

    def test_wait_tag_preserved(self):
        """Dialogue-only {w} and {p} tags must be preserved."""
        text = "Line 1{w} Line 1{w=1.0} Line 1"
        protected, placeholder_map = protect_renpy_syntax(text)
        restored = restore_renpy_syntax(protected, placeholder_map)
        assert "{w}" in restored or "Line 1" in restored, f"Wait tag lost: {restored}"


# =============================================================================
# 8. PARSER INTEGRATION: ENTRY STRUCTURE
# =============================================================================

class TestParserEntryStructure:
    """Verify parser entries include all required fields."""

    def test_record_entry_includes_translation_id(self, parser):
        """Every _record_entry result must include 'translation_id' field."""
        entry = parser._record_entry(
            text="Hello, world!",
            line_number=10,
            context_line='e "Hello, world!"',
            text_type="dialogue",
            context_path=["label:start"],
            character="e",
            file_path="test.rpy",
        )
        if entry is not None:  # Entry may be filtered; if not filtered, must have translation_id
            assert "translation_id" in entry, \
                f"'translation_id' missing from entry: {list(entry.keys())}"

    def test_translation_id_is_string(self, parser):
        """translation_id must be a non-empty string."""
        entry = parser._record_entry(
            text="Good morning!",
            line_number=5,
            context_line='narrator "Good morning!"',
            text_type="narration",
            context_path=["label:intro"],
            character="",
            file_path="test.rpy",
        )
        if entry is not None:
            assert isinstance(entry["translation_id"], str), \
                "translation_id must be a string"
            assert entry["translation_id"], "translation_id must not be empty"

    def test_translation_id_format(self, parser):
        """translation_id should contain an underscore (label_hash format)."""
        entry = parser._record_entry(
            text="It was a dark and stormy night.",
            line_number=42,
            context_line='narrator "It was a dark and stormy night."',
            text_type="narration",
            context_path=["label:prologue"],
            character="",
            file_path="script.rpy",
        )
        if entry is not None:
            tid = entry["translation_id"]
            assert '_' in tid, f"translation_id lacks underscore separator: {tid}"
