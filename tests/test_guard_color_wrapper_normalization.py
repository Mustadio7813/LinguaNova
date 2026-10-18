# -*- coding: utf-8 -*-
"""
Tests for the v2.8.17 pure outer color-wrapper normalization helper.

Covers:
  - Baseline characterization: classify_translation_corruption() stays a
    pure, strict classifier — a raw wrapped translation is still rejected
    as ``renpy_tag_set_mismatch`` and the classifier NEVER rewrites text.
  - normalize_outer_color_wrapper(): the five exact observed fixtures
    (engine-added ``{color=#e1e3e6}...{/color}`` wrappers on untagged
    preference labels) unwrap to their inner Turkish text.
  - Strict source boundary: ANY Ren'Py tag in the source (incl. ``{#...}``)
    keeps the wrapped translation untouched.
  - Safe color grammar: literal #rgb / #rgba / #rrggbb / #rrggbbaa only.
  - Rejection of nested, mismatched, empty, leading/trailing-text,
    non-literal, self-closing, and non-color wrappers.
  - Placeholder and printf integrity re-checked on the unwrapped value.
  - Idempotency and plain-text passthrough.
"""

import pytest

from src.core.pipeline.constants import OUTER_COLOR_WRAPPER_RE, SAFE_COLOR_HEX_RE
from src.core.pipeline.translating import (
    classify_translation_corruption,
    normalize_outer_color_wrapper,
)


# The five exact pairs observed in diagnostic_turkish.json:37663-37697.
FIVE_FIXTURES = [
    ("Text Speed", "{color=#e1e3e6}Metin Hızı{/color}", "Metin Hızı"),
    ("Auto-Forward Time", "{color=#e1e3e6}Otomatik İletme Zamanı{/color}", "Otomatik İletme Zamanı"),
    ("Music Volume", "{color=#e1e3e6}Müzik Sesi{/color}", "Müzik Sesi"),
    ("Sound Volume", "{color=#e1e3e6}Ses Seviyesi{/color}", "Ses Seviyesi"),
    ("Voice Volume", "{color=#e1e3e6}Ses Seviyesi{/color}", "Ses Seviyesi"),
]


# ==================================================================
# 1. BASELINE CHARACTERIZATION (unchanged classifier behavior)
# ==================================================================
class TestClassifierBaselineUnchanged:
    """The pure classifier must keep rejecting raw wrapped input exactly
    as before this change — normalization lives ONLY in the helper."""

    @pytest.mark.parametrize("original,wrapped,_inner", FIVE_FIXTURES)
    def test_raw_wrapped_input_still_rejected(self, original, wrapped, _inner):
        reason = classify_translation_corruption(original, wrapped)
        assert reason == "renpy_tag_set_mismatch"

    @pytest.mark.parametrize("original,_wrapped,inner", FIVE_FIXTURES)
    def test_unwrapped_inner_passes_classifier(self, original, _wrapped, inner):
        assert classify_translation_corruption(original, inner) is None


# ==================================================================
# 2. SAFE COLOR HEX GRAMMAR
# ==================================================================
class TestSafeColorHexGrammar:
    @pytest.mark.parametrize("hex_value", [
        "#fff", "#FFF", "#abc", "#123",          # #rgb
        "#ffff", "#abcd", "#1234",               # #rgba
        "#e1e3e6", "#E1E3E6", "#aAbBcC",         # #rrggbb
        "#ffffffff", "#12345678",                # #rrggbbaa
    ])
    def test_safe_hex_accepted(self, hex_value):
        assert SAFE_COLOR_HEX_RE.fullmatch(hex_value) is not None

    @pytest.mark.parametrize("hex_value", [
        "#ff",                                   # too short
        "#fffff", "#fffffff", "#fffffffff",      # 5 / 7 / 9 digits
        "#ggg", "#12x456",                       # non-hex characters
        "fff", "ffffff",                         # missing '#'
        "red", "gui.text_color", "(gui.text_color)",
        "# fff", "#fff ", " #fff",               # whitespace
        "",                                      # empty
    ])
    def test_unsafe_hex_rejected(self, hex_value):
        assert SAFE_COLOR_HEX_RE.fullmatch(hex_value) is None


# ==================================================================
# 3. THE FIVE EXACT OBSERVED FIXTURES NORMALIZE
# ==================================================================
class TestFiveObservedFixtures:
    @pytest.mark.parametrize("original,wrapped,inner", FIVE_FIXTURES)
    def test_exact_fixture_unwraps(self, original, wrapped, inner):
        assert normalize_outer_color_wrapper(original, wrapped) == inner

    @pytest.mark.parametrize("original,wrapped,inner", FIVE_FIXTURES)
    def test_unwrapped_value_is_classifier_clean(self, original, wrapped, inner):
        normalized = normalize_outer_color_wrapper(original, wrapped)
        assert classify_translation_corruption(original, normalized) is None


# ==================================================================
# 4. STRICT SOURCE BOUNDARY — tagged sources never normalize
# ==================================================================
class TestTaggedSourceBoundary:
    @pytest.mark.parametrize("original", [
        "{b}Text Speed{/b}",
        "{i}Text Speed{/i}",
        "{color=#fff}Text Speed{/color}",
        "{#auto_page}Text Speed",
        "{#tag}",
        "Text {size=+10}Speed{/size}",
    ])
    def test_tagged_source_returns_wrapped_unchanged(self, original):
        wrapped = "{color=#e1e3e6}Metin Hızı{/color}"
        assert normalize_outer_color_wrapper(original, wrapped) == wrapped

    def test_disambiguation_tag_source_stays_strict(self):
        wrapped = "{color=#e1e3e6}A{/color}"
        assert normalize_outer_color_wrapper("{#auto_page}A", wrapped) == wrapped


# ==================================================================
# 5. NON-COLOR / SEMANTIC / TIMING / IMAGE TAGS STAY BLOCKED
# ==================================================================
class TestNonColorWrappersRejected:
    @pytest.mark.parametrize("wrapped", [
        "{font=DejaVuSans.ttf}Metin Hızı{/font}",
        "{size=+10}Metin Hızı{/size}",
        "{cps=20}Metin Hızı{/cps}",
        "{nw}Metin Hızı",
        "{nw}Metin Hızı{/nw}",
        "{image=gui/heart.png}",
        "{image=gui/heart.png}Metin{/image}",
        "{b}Metin Hızı{/b}",
        "{i}Metin Hızı{/i}",
        "{rt}Metin{/rt}Hızı",
        "{#auto_page}Metin Hızı",
    ])
    def test_non_color_tag_returns_unchanged(self, wrapped):
        assert normalize_outer_color_wrapper("Text Speed", wrapped) == wrapped

    @pytest.mark.parametrize("wrapped", [
        "{font=DejaVuSans.ttf}Metin Hızı{/font}",
        "{size=+10}Metin Hızı{/size}",
        "{cps=20}Metin Hızı{/cps}",
        "{nw}Metin Hızı",
    ])
    def test_classifier_still_rejects_non_color_tags(self, wrapped):
        assert classify_translation_corruption("Text Speed", wrapped) == (
            "renpy_tag_set_mismatch"
        )


# ==================================================================
# 6. MALFORMED / NESTED / EMPTY / AFFIXED WRAPPERS REJECTED
# ==================================================================
class TestMalformedWrappersRejected:
    @pytest.mark.parametrize("wrapped", [
        # nested color pairs
        "{color=#fff}a{color=#abc}b{/color}c{/color}",
        "{color=#fff}{color=#abc}Metin{/color}{/color}",
        # mismatched / unbalanced pairs
        "{color=#fff}Metin{/font}",
        "{color=#fff}Metin",
        "Metin{/color}",
        "{color=#fff}Metin{/color}{/color}",
        # empty inner text
        "{color=#fff}{/color}",
        "{color=#fff} {/color}",
        "{color=#fff}\n{/color}",
        # leading / trailing text (incl. whitespace)
        "x{color=#fff}Metin{/color}",
        "{color=#fff}Metin{/color}x",
        " {color=#fff}Metin{/color}",
        "{color=#fff}Metin{/color} ",
        "\n{color=#fff}Metin{/color}",
        # non-literal / unsafe color arguments
        "{color=(gui.text_color)}Metin{/color}",
        "{color=gui.text_color}Metin{/color}",
        "{color=red}Metin{/color}",
        "{color= #fff}Metin{/color}",
        "{color =#fff}Metin{/color}",
        "{color=#fff }Metin{/color}",
        "{color=#ff}Metin{/color}",
        "{color=#fffff}Metin{/color}",
        "{color=#gggggg}Metin{/color}",
        # self-closing / wrong case
        "{color=#fff/}Metin{/color}",
        "{COLOR=#fff}Metin{/COLOR}",
        "{Color=#fff}Metin{/Color}",
        # inner text carrying tags of its own
        "{color=#fff}Metin {b}kalın{/b}{/color}",
        "{color=#fff}Metin {#tag}{/color}",
        "{color=#fff}Metin {/color} artı",
    ])
    def test_malformed_returns_unchanged(self, wrapped):
        assert normalize_outer_color_wrapper("Text Speed", wrapped) == wrapped

    def test_nested_inner_tag_keeps_classifier_strict(self):
        wrapped = "{color=#fff}Metin {b}kalın{/b}{/color}"
        assert normalize_outer_color_wrapper("Text Speed", wrapped) == wrapped
        assert classify_translation_corruption("Text Speed", wrapped) == (
            "renpy_tag_set_mismatch"
        )


# ==================================================================
# 7. PLACEHOLDER & PRINTF INTEGRITY RE-CHECKED POST-UNWRAP
# ==================================================================
class TestPostUnwrapIntegrity:
    def test_placeholder_survives_normalization(self):
        wrapped = "{color=#fff}[name] Hızı{/color}"
        assert normalize_outer_color_wrapper("[name] Speed", wrapped) == "[name] Hızı"

    def test_dropped_placeholder_blocks_normalization(self):
        wrapped = "{color=#fff}Hız{/color}"
        assert normalize_outer_color_wrapper("[name] Speed", wrapped) == wrapped

    def test_mutated_placeholder_blocks_normalization(self):
        wrapped = "{color=#fff}[player] Hız{/color}"
        assert normalize_outer_color_wrapper("[name] Speed", wrapped) == wrapped

    def test_printf_spec_survives_normalization(self):
        wrapped = "{color=#fff}Hız: %d{/color}"
        assert normalize_outer_color_wrapper("Speed: %d", wrapped) == "Hız: %d"

    def test_dropped_printf_spec_blocks_normalization(self):
        wrapped = "{color=#fff}Hız{/color}"
        assert normalize_outer_color_wrapper("Speed: %d", wrapped) == wrapped

    def test_mutated_printf_spec_blocks_normalization(self):
        wrapped = "{color=#fff}Hız: %s{/color}"
        assert normalize_outer_color_wrapper("Speed: %d", wrapped) == wrapped

    def test_length_inflation_blocks_normalization(self):
        wrapped = "{color=#fff}" + "çok " * 40 + "uzun{/color}"
        assert normalize_outer_color_wrapper("Hi", wrapped) == wrapped

    def test_html_leak_blocks_normalization(self):
        wrapped = "{color=#fff}<span>Metin</span>{/color}"
        assert normalize_outer_color_wrapper("Text Speed", wrapped) == wrapped

    def test_placeholder_remnant_blocks_normalization(self):
        wrapped = "{color=#fff}Metin ⟦RLPH0A1_0⟧{/color}"
        assert normalize_outer_color_wrapper("Text Speed", wrapped) == wrapped


# ==================================================================
# 8. IDEMPOTENCY & PASSTHROUGH
# ==================================================================
class TestIdempotencyAndPassthrough:
    @pytest.mark.parametrize("original,wrapped,_inner", FIVE_FIXTURES)
    def test_normalization_is_idempotent(self, original, wrapped, _inner):
        once = normalize_outer_color_wrapper(original, wrapped)
        twice = normalize_outer_color_wrapper(original, once)
        assert twice == once

    def test_plain_translation_passes_through(self):
        assert normalize_outer_color_wrapper("Text Speed", "Metin Hızı") == "Metin Hızı"

    def test_empty_translation_passes_through(self):
        assert normalize_outer_color_wrapper("Text Speed", "") == ""

    def test_none_translation_passes_through(self):
        assert normalize_outer_color_wrapper("Text Speed", None) is None

    def test_whitespace_only_translation_passes_through(self):
        assert normalize_outer_color_wrapper("Text Speed", "   ") == "   "


# ==================================================================
# 9. WRAPPER REGEX SHAPE (anchored, single balanced pair)
# ==================================================================
class TestWrapperRegexShape:
    def test_exact_pair_matches(self):
        match = OUTER_COLOR_WRAPPER_RE.match("{color=#e1e3e6}Metin{/color}")
        assert match is not None
        assert match.group("hex") == "#e1e3e6"
        assert match.group("inner") == "Metin"

    @pytest.mark.parametrize("wrapped", [
        "x{color=#fff}Metin{/color}",
        "{color=#fff}Metin{/color}x",
        "{color=#fff}Metin",
        "{color=red}Metin{/color}",
        "{COLOR=#fff}Metin{/COLOR}",
    ])
    def test_non_exact_shapes_do_not_match(self, wrapped):
        assert OUTER_COLOR_WRAPPER_RE.match(wrapped) is None


# ==================================================================
# 10. SAVE-PATH PARITY (strings.json ingestion unwraps cleanly)
# ==================================================================
class TestSavePathParity:
    def test_extract_raw_mapping_unwraps_color_wrappers(self):
        from src.core.pipeline.saving import _extract_raw_mapping

        class MockEntry:
            def __init__(self, original, translated, line=10):
                self.original_text = original
                self.translated_text = translated
                self.line_number = line

        class MockTLFile:
            def __init__(self, entries):
                self.file_path = "game/tl/turkish/screens.rpy"
                self.entries = entries

        entries = [
            MockEntry("Text Speed", "{color=#e1e3e6}Metin Hızı{/color}"),
            MockEntry("Auto-Forward Time", "{color=#e1e3e6}Otomatik İletme Zamanı{/color}"),
            MockEntry("Regular UI", "Normal UI"),
        ]
        tl_files = [MockTLFile(entries)]
        extra_translations = {
            "Music Volume": "{color=#e1e3e6}Müzik Sesi{/color}",
        }

        mapping, skipped_corrupt, skipped_reasons, _ = _extract_raw_mapping(
            tl_files, extra_translations=extra_translations
        )

        assert mapping["Text Speed"] == "Metin Hızı"
        assert mapping["Auto-Forward Time"] == "Otomatik İletme Zamanı"
        assert mapping["Regular UI"] == "Normal UI"
        assert mapping["Music Volume"] == "Müzik Sesi"
        assert skipped_corrupt == 0

    def test_unwrapped_matching_original_is_excluded_from_mapping(self):
        from src.core.pipeline.saving import _extract_raw_mapping

        class MockEntry:
            def __init__(self, original, translated, line=10):
                self.original_text = original
                self.translated_text = translated
                self.line_number = line

        class MockTLFile:
            def __init__(self, entries):
                self.file_path = "game/tl/turkish/screens.rpy"
                self.entries = entries

        # Engine wrapped untranslated English text:
        entries = [
            MockEntry("Quit", "{color=#e1e3e6}Quit{/color}"),
        ]
        tl_files = [MockTLFile(entries)]

        mapping, skipped_corrupt, _, _ = _extract_raw_mapping(tl_files)
        # Unwrapped value equals original ("Quit" == "Quit"), so excluded from strings.json
        assert "Quit" not in mapping
        assert skipped_corrupt == 0


# ==================================================================
# 11. STALE-TL REQUEUE POLICY (corrupt stale TL entries stay strictly reopened)
# ==================================================================
class TestStaleTLRequeuePolicy:
    def test_stale_corrupted_tl_entries_are_reopened_for_translation(self):
        from src.core.pipeline.extraction import reopen_stale_tl_entries

        class MockEntry:
            def __init__(self, original, translated, line=10):
                self.original_text = original
                self.translated_text = translated
                self.line_number = line
                self.file_path = "game/tl/turkish/screens.rpy"
                self.translation_id = "tid_123"

            def compute_id(self):
                return self.translation_id

        class MockTLFile:
            def __init__(self, entries):
                self.file_path = "game/tl/turkish/screens.rpy"
                self.entries = entries

        # A stale TL file with wrapped color text from an older buggy run
        stale_entry = MockEntry("Text Speed", "{color=#e1e3e6}Metin Hızı{/color}")
        clean_entry = MockEntry("Start", "Başla")
        tl_files = [MockTLFile([stale_entry, clean_entry])]

        counts = reopen_stale_tl_entries(
            tl_files,
            config=None,
            diagnostic_report=None,
            record_translation_guard_event=lambda **kw: None,
        )

        # The stale entry with tag mismatch MUST be cleared for retranslation
        assert counts["reopened"] == 1
        assert counts["corrupted"] == 1
        assert stale_entry.translated_text == ""
        # Clean entry remains untouched
        assert clean_entry.translated_text == "Başla"

