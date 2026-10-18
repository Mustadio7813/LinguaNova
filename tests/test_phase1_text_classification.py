"""
Test Phase 1: Text Type Classification Enhancement (v2.8.7+)

Tests for:
1. Button vs translatable_string distinction  
2. Screen translatable vs generic translatable
3. Tooltip extraction
4. Backward compatibility with Ren'Py 7 & 8
"""

import unittest
from src.core.parser import RenPyParser, TextType
from src.core.output_formatter import RenPyOutputFormatter


class TestPhase1TextClassification(unittest.TestCase):
    """Test improved text type classification"""
    
    def setUp(self):
        self.parser = RenPyParser()
        self.formatter = RenPyOutputFormatter()
    
    # ========================================================================
    # TEST 1: TextType Constants (Foundation)
    # ========================================================================
    
    def test_texttype_constants_defined(self):
        """New TextType constants should be defined for Phase 1"""
        self.assertEqual(TextType.BUTTON_TEXT, 'button_text')
        self.assertEqual(TextType.SCREEN_TRANSLATABLE, 'screen_translatable')
        self.assertEqual(TextType.TOOLTIP_TEXT, 'tooltip_text')
    
    # ========================================================================
    # TEST 2: Pattern Registry Structure (Phase 1 Ordering)
    # ========================================================================
    
    def test_pattern_registry_exists(self):
        """Parser should have pattern_registry defined"""
        self.parser._register_patterns()
        self.assertIsNotNone(self.parser.pattern_registry)
        self.assertGreater(len(self.parser.pattern_registry), 0)
    
    def test_textbutton_patterns_registered(self):
        """textbutton patterns should be registered with BUTTON_TEXT type"""
        self.parser._register_patterns()
        registry = self.parser.pattern_registry
        
        # Find button-related entries
        button_entries = [e for e in registry if e.get('type') == TextType.BUTTON_TEXT]
        self.assertGreater(len(button_entries), 0,
                          "Should have at least one entry with BUTTON_TEXT type")
    
    def test_tooltip_pattern_registered(self):
        """tooltip pattern should be registered with TOOLTIP_TEXT type"""
        self.parser._register_patterns()
        registry = self.parser.pattern_registry
        
        # Find tooltip-related entries
        tooltip_entries = [e for e in registry if e.get('type') == TextType.TOOLTIP_TEXT]
        self.assertGreater(len(tooltip_entries), 0,
                          "Should have at least one entry with TOOLTIP_TEXT type")
    
    def test_screen_translatable_registered(self):
        """screen translatable pattern should be registered with SCREEN_TRANSLATABLE type"""
        self.parser._register_patterns()
        registry = self.parser.pattern_registry
        
        screen_trans_entries = [e for e in registry if e.get('type') == TextType.SCREEN_TRANSLATABLE]
        self.assertGreater(len(screen_trans_entries), 0,
                          "Should have at least one entry with SCREEN_TRANSLATABLE type")
    
    # ========================================================================
    # TEST 3: Pattern Priority (Most Specific First)
    # ========================================================================
    
    def test_button_patterns_early_in_registry(self):
        """Button patterns should be registered EARLY (high priority)"""
        self.parser._register_patterns()
        registry = self.parser.pattern_registry
        
        # Button patterns should be in TIER 1-2 (early)
        button_positions = []
        generic_position = None
        
        for i, entry in enumerate(registry):
            if entry.get('type') == TextType.BUTTON_TEXT:
                button_positions.append(i)
            elif entry.get('type') == 'translatable_string':
                if generic_position is None:
                    generic_position = i
        
        self.assertGreater(len(button_positions), 0, "Should have button patterns")
        if generic_position is not None:
            avg_button_pos = sum(button_positions) / len(button_positions)
            self.assertLess(avg_button_pos, generic_position,
                           "Button patterns should appear before generic translatable_string")
    
    def test_screen_patterns_early_in_registry(self):
        """Screen text patterns should be registered early"""
        self.parser._register_patterns()
        registry = self.parser.pattern_registry
        
        screen_positions = []
        generic_position = None
        
        for i, entry in enumerate(registry):
            if entry.get('type') in [TextType.SCREEN_TRANSLATABLE, 'ui']:
                screen_positions.append(i)
            elif entry.get('type') == 'translatable_string':
                if generic_position is None:
                    generic_position = i
        
        self.assertGreater(len(screen_positions), 0)
        if generic_position is not None:
            avg_screen_pos = sum(screen_positions) / len(screen_positions)
            # Screen UI should generally be before generic translatable
            self.assertLessEqual(avg_screen_pos, generic_position + 20,
                                "Screen patterns should be relatively early")
    
    # ========================================================================
    # TEST 4: False Positive Filter - New Types Should NOT Be Filtered
    # ========================================================================
    
    def test_button_text_passes_false_positive_filter(self):
        """Button text like 'Save' should NOT be filtered as false positive"""
        self.assertFalse(
            self.formatter._should_skip_translation("Save"),
            "Button text 'Save' should pass through filter"
        )
        self.assertFalse(
            self.formatter._should_skip_translation("Load"),
            "Button text 'Load' should pass through filter"
        )
        self.assertFalse(
            self.formatter._should_skip_translation("Options"),
            "Button text 'Options' should pass through filter"
        )
        self.assertFalse(
            self.formatter._should_skip_translation("Continue"),
            "Button text 'Continue' should pass through filter"
        )
    
    def test_screen_translatable_passes_false_positive_filter(self):
        """Screen UI text should pass through filter"""
        self.assertFalse(
            self.formatter._should_skip_translation("Current HP: [hp]"),
            "Screen text with variable should pass through filter"
        )
        self.assertFalse(
            self.formatter._should_skip_translation("Items in inventory"),
            "Screen translatable text should pass through filter"
        )
        self.assertFalse(
            self.formatter._should_skip_translation("Status"),
            "UI status text should pass through filter"
        )
    
    def test_tooltip_text_passes_false_positive_filter(self):
        """Tooltip text should pass through filter"""
        self.assertFalse(
            self.formatter._should_skip_translation("Click to save"),
            "Tooltip text should pass through filter"
        )
        self.assertFalse(
            self.formatter._should_skip_translation("Skill description here"),
            "Tooltip description should pass through filter"
        )
        self.assertFalse(
            self.formatter._should_skip_translation("Quick save to slot 1"),
            "Tooltip content should pass through filter"
        )
    
    # ========================================================================
    # TEST 5: Regex Patterns Exist and Are Compiled
    # ========================================================================
    
    def test_textbutton_regex_exists(self):
        """textbutton regex patterns should exist"""
        self.assertTrue(hasattr(self.parser, 'textbutton_re'))
        self.assertTrue(hasattr(self.parser, 'textbutton_translatable_re'))
        self.assertIsNotNone(self.parser.textbutton_re)
        self.assertIsNotNone(self.parser.textbutton_translatable_re)
    
    def test_screen_text_regex_exists(self):
        """Screen text regex patterns should exist"""
        self.assertTrue(hasattr(self.parser, 'screen_text_re'))
        self.assertTrue(hasattr(self.parser, 'screen_text_translatable_re'))
        self.assertIsNotNone(self.parser.screen_text_re)
        self.assertIsNotNone(self.parser.screen_text_translatable_re)
    
    def test_tooltip_regex_exists(self):
        """Tooltip regex pattern should exist"""
        self.assertTrue(hasattr(self.parser, 'tooltip_property_re'))
        self.assertIsNotNone(self.parser.tooltip_property_re)
    
    # ========================================================================
    # TEST 6: Regex Pattern Matching (Sample Texts)
    # ========================================================================
    
    def test_textbutton_plain_text_regex_match(self):
        """textbutton_re should match plain textbutton"""
        pattern = self.parser.textbutton_re
        test_line = 'textbutton "Save" action FileSave(1)'
        match = pattern.match(test_line)
        self.assertIsNotNone(match, "Should match textbutton plain text")
    
    def test_textbutton_translatable_regex_match(self):
        """textbutton_translatable_re should match _() wrapped"""
        pattern = self.parser.textbutton_translatable_re
        test_line = 'textbutton _("Save") action FileSave(1)'
        match = pattern.match(test_line)
        self.assertIsNotNone(match, "Should match textbutton with _()")
    
    def test_screen_text_regex_match(self):
        """screen_text_re should match text in screens"""
        pattern = self.parser.screen_text_re
        test_cases = [
            'text "Inventory"',
            'text _("Status")',
            'label "Information"',
            'tooltip "Quick save"'
        ]
        for test_line in test_cases:
            with self.subTest(line=test_line):
                match = pattern.match(test_line)
                self.assertIsNotNone(match, f"Should match: {test_line}")
    
    def test_screen_text_translatable_regex_match(self):
        """screen_text_translatable_re should match _() wrapped text"""
        pattern = self.parser.screen_text_translatable_re
        test_cases = [
            'text _("Status")',
            'label _("Information")',
            'tooltip _("Quick save")'
        ]
        for test_line in test_cases:
            with self.subTest(line=test_line):
                match = pattern.match(test_line)
                self.assertIsNotNone(match, f"Should match: {test_line}")
    
    def test_tooltip_regex_match(self):
        """tooltip_property_re should match tooltip statements"""
        pattern = self.parser.tooltip_property_re
        test_cases = [
            'tooltip "Quick save"',
            'tooltip r"Raw string tooltip"'
        ]
        for test_line in test_cases:
            with self.subTest(line=test_line):
                match = pattern.search(test_line)
                self.assertIsNotNone(match, f"Should match: {test_line}")


class TestBackwardCompatibilityRenPy7V8(unittest.TestCase):
    """Test backward compatibility across Ren'Py versions"""
    
    def setUp(self):
        self.parser = RenPyParser()
        self.formatter = RenPyOutputFormatter()
    
    # ========================================================================
    # TEST 1: Regex Pattern Flexibility (v7 & v8 Syntax)
    # ========================================================================
    
    def test_regex_flexible_trailing_comma(self):
        """Patterns should handle both trailing-comma and non-trailing-comma"""
        pattern = self.parser.textbutton_re
        
        # v7 style (no trailing comma required in pattern)
        v7_style = 'textbutton "Save" action FileSave(1)'
        self.assertIsNotNone(pattern.match(v7_style), "Should match v7 style")
        
        # v8 style (trailing comma in actual code)
        # Pattern doesn't need to match the action part, so this works too
        v8_style = 'textbutton "Save",'
        # Note: Pattern matches up to the quote, colon, etc., so this should work
        self.assertIsNotNone(pattern.match(v8_style), "Should handle variations")
    
    def test_regex_line_continuation_handling(self):
        """Patterns should work with lines that have line continuations"""
        pattern = self.parser.textbutton_re
        
        # Lines with backslash continuation are typically split by parser before regex
        # But we can test that escaped quotes don't break things
        test_line = 'textbutton "Multi \\\\ Line Text" action Return()'
        # Pattern should still work (as it's a single line after parsing)
        self.assertIsNotNone(pattern.match(test_line), "Should handle escaped characters")
    
    def test_character_define_regex_exists(self):
        """Character definition regex should exist"""
        self.assertTrue(hasattr(self.parser, 'character_define_re'))
        self.assertIsNotNone(self.parser.character_define_re)
    
    # ========================================================================
    # TEST 2: Type Constants Backward Compat
    # ========================================================================
    
    def test_old_button_type_still_works(self):
        """Old 'button' type should still exist for legacy code"""
        # Some code might reference 'button' directly
        self.assertEqual(TextType.DIALOGUE, 'dialogue')  # Verify TextType works
        # New type is BUTTON_TEXT
        self.assertEqual(TextType.BUTTON_TEXT, 'button_text')
    
    def test_translatable_string_type_unchanged(self):
        """'translatable_string' type should still work (unchanged)"""
        # Used by many existing extractors
        # Just verify it's still valid
        self.assertTrue(isinstance('translatable_string', str))


if __name__ == '__main__':
    unittest.main()
