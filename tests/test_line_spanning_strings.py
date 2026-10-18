# -*- coding: utf-8 -*-
"""
Regression tests for dialogue that continues on the next physical line (v2.8.17).

Ren'Py lets a plain string span physical lines:

    ply "I'm just disgusted with such a man. When he had a beautiful woman beside him,
        but instead he made out with another woman! Tch, it makes me sick."

Its lexer reads that as one string and collapses the newline plus the
continuation's indentation into a single space. The parser only knew the
triple-quoted form, so the opening line matched no pattern and the entire line
of dialogue was dropped — 325 lines in FunTanariZ 1.12 alone.
"""

import pytest

from src.core.parser import RenPyParser


@pytest.fixture(scope="module")
def parser():
    return RenPyParser()


def _texts(parser, tmp_path, source, name="script.rpy"):
    script = tmp_path / name
    script.write_text(source, encoding="utf-8")
    return [e.get("text") for e in parser.extract_text_entries(str(script))]


class TestUnterminatedStringDetection:
    @pytest.mark.parametrize("line", [
        '    ply "a line that keeps going',
        '    "narration that wraps',
        '    menu_label "choice text',
    ])
    def test_open_double_quote_is_detected(self, parser, line):
        assert parser._has_unterminated_string(line) is True

    @pytest.mark.parametrize("line", [
        '    ply "a complete line."',
        "    # don't join this comment",
        "        Oyun her basladiginda dili Turkish'ye cevir.",   # prose apostrophe
        "    value = compute(a, b)  # it's fine",
        '    ply "escaped quote \\" inside"',
        '    text = """docstring start',
    ])
    def test_non_openers_are_ignored(self, parser, line):
        assert parser._has_unterminated_string(line) is False


class TestJoining:
    def test_wrapped_dialogue_is_extracted_as_one_line(self, parser, tmp_path):
        texts = _texts(parser, tmp_path, (
            'label test:\n\n'
            '    hayu "Before."\n\n'
            '    ply "I am disgusted with such a man. When he had a beautiful woman beside him, \n'
            '        but instead he made out with another! Tch, it makes me sick."\n\n'
            '    hayu "After."\n'
        ))
        joined = next((t for t in texts if t.startswith("I am disgusted")), None)
        assert joined is not None, "the wrapped dialogue must be extracted"
        assert joined.endswith("it makes me sick.")
        # Ren'Py collapses the newline and indentation into a single space.
        assert "beside him, but instead" in joined
        assert "\n" not in joined
        assert "Before." in texts and "After." in texts

    def test_line_numbers_of_later_entries_are_unchanged(self, parser, tmp_path):
        script = tmp_path / "numbers.rpy"
        script.write_text(
            'label test:\n\n'
            '    ply "wrapped start\n'
            '        and end."\n\n'
            '    hayu "Later line."\n',
            encoding="utf-8",
        )
        entries = parser.extract_text_entries(str(script))
        later = next(e for e in entries if e.get("text") == "Later line.")
        assert later.get("line_number") == 6, "blanking consumed lines keeps numbering"

    def test_three_line_string_is_joined(self, parser, tmp_path):
        texts = _texts(parser, tmp_path, (
            'label test:\n'
            '    ply "one \n'
            '        two \n'
            '        three."\n'
        ))
        assert any(t == "one two three." for t in texts), texts

    def test_apostrophes_do_not_merge_unrelated_lines(self, parser, tmp_path):
        texts = _texts(parser, tmp_path, (
            'label test:\n'
            "    ply \"It's fine.\"\n"
            '    hayu "Separate line."\n'
        ))
        assert "It's fine." in texts
        assert "Separate line." in texts

    def test_docstrings_are_left_alone(self, parser, tmp_path):
        """Joining inside a triple-quoted block would corrupt the code around it."""
        texts = _texts(parser, tmp_path, (
            'init python:\n'
            '    def helper():\n'
            '        """\n'
            "        Bir aciklama satiri, Turkish'ye cevir.\n"
            '        """\n'
            '        pass\n'
            '\n'
            'label test:\n'
            '    ply "Real dialogue."\n'
        ))
        assert "Real dialogue." in texts

    def test_unclosed_string_at_eof_does_not_swallow_the_file(self, parser, tmp_path):
        """A malformed file must behave exactly as it did before."""
        texts = _texts(parser, tmp_path, (
            'label test:\n'
            '    hayu "Good line."\n'
            '    ply "never closed\n'
        ))
        assert "Good line." in texts

    def test_runaway_join_is_capped(self, parser):
        lines = ['    ply "opened'] + [f"        filler {i}" for i in range(60)]
        merged = parser._join_line_spanning_strings(lines)
        # With no closing quote the originals are restored untouched.
        assert merged[0] == lines[0]
        assert merged[1] == lines[1]
