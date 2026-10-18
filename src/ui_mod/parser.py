# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — independent, read-only Ren'Py interface parser.
"""Static interface text parser used only by MOD.

It intentionally does NOT import or patch LinguaNova's normal Ren'Py parser.
The parser is conservative: it scans screen-language text and explicitly
marked translatable strings, then follows simple UI data variables referenced
by screens. Dialogue/say statements outside screens are deliberately ignored.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .protect import is_junk

@dataclass
class ModTextCandidate:
    text: str
    file_path: str
    line_number: int
    screen: str = ""
    source_kind: str = "rpy"
    confidence: str = "high"
    reason: str = ""


_SCREEN_RE = re.compile(r"^\s*screen\s+([A-Za-z_]\w*)\b.*:\s*(?:#.*)?$")
_MARKED_RE = re.compile(r"(?<![A-Za-z0-9_])(?:_|__|___|_p)\s*\(\s*(?P<q>['\"])(?P<body>(?:\\.|(?!\1).)*)\1", re.DOTALL)
_UI_STMT_RE = re.compile(
    r"^\s*(?:textbutton|text|tooltip|prompt)\s+(?P<expr>.+?)(?:\s+(?:action|style|xalign|yalign|color|size|at|if|sensitive|selected|alternate|hovered)\b.*)?$"
)
_ASSIGN_RE = re.compile(r"^\s*(?:(?:default|define)\s+|\$\s*)?([A-Za-z_]\w*)\s*=\s*(.*)$")
_SAY_RE = re.compile(r"^\s*(?:(?:[A-Za-z_]\w*)\s+)?(?P<expr>(?:['\"]).*(?:['\"]))\s*(?:with\b.*)?$")
_MENU_CHOICE_RE = re.compile(r"^\s*(?P<expr>(?:['\"]).*(?:['\"]))\s*:\s*$")
_PY_UI_CALL_RE = re.compile(r"\brenpy\.(?:say|notify|input|confirm|display_menu)\s*\(", re.I)
_QUOTED_RE = re.compile(r"(?P<q>['\"])(?P<body>(?:\\.|(?!\1).)*)\1", re.DOTALL)
_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_]\w*\b")
_IMAGE_EXT_RE = re.compile(r"\.(?:png|jpe?g|webp|gif|svg|avif|bmp|ico|ogg|opus|mp3|wav|flac|webm|mp4|mkv|avi|rpyc?|rpymc?)$", re.I)

_SCREEN_KEYWORDS = {
    "screen", "text", "textbutton", "button", "frame", "vbox", "hbox", "grid",
    "viewport", "window", "fixed", "use", "for", "if", "elif", "else", "python",
    "action", "style", "xalign", "yalign", "xpos", "ypos", "xsize", "ysize",
    "spacing", "padding", "margin", "at", "add", "imagebutton", "hotspot", "key",
    "null", "transform", "bar", "vbar", "hbar", "input", "timer", "drag", "draggroup",
    "modal", "tag", "zorder", "variant", "default", "define", "True", "False", "None",
}


def _indent(line: str) -> int:
    return len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip(" "))


def _decode_literal(quote: str, body: str) -> Optional[str]:
    try:
        return ast.literal_eval(quote + body + quote)
    except Exception:
        try:
            return bytes(body, "utf-8").decode("unicode_escape")
        except Exception:
            return None


def renpy_statement_string(quote: str, body: str) -> str:
    """Decode a say/menu string exactly as Ren'Py's lexer does (renpy/lexer.py ``string``).

    Runs of spaces/newlines collapse to one space; ``\\n`` is a newline; ``\\{``,
    ``\\[`` and ``\\%`` stay escaped as ``{{``, ``[[`` and ``%%``; ``\\uXXXX`` is decoded.
    The result is the string Ren'Py looks up in its translation table at runtime.
    """
    body = re.sub(r"[ \n]+", " ", body)

    def dequote(match):
        char = match.group(1)
        if char == "{":
            return "{{"
        if char == "[":
            return "[["
        if char == "%":
            return "%%"
        if char == "n":
            return "\n"
        if char[0] == "u" and match.group(2):
            return chr(int(match.group(2), 16))
        return char

    return re.sub(r"\\(u([0-9a-fA-F]{1,4})|.)", dequote, body)


def _first_statement_string(expr: str) -> Optional[str]:
    match = _QUOTED_RE.search(expr or "")
    if match is None:
        return None
    return renpy_statement_string(match.group("q"), match.group("body"))


def _iter_string_literals(expr: str) -> Iterable[str]:
    for match in _QUOTED_RE.finditer(expr or ""):
        value = _decode_literal(match.group("q"), match.group("body"))
        if value is not None:
            yield value


def _looks_like_ui_text(text: str) -> bool:
    s = (text or "").strip()
    if not s or len(s) > 600 or is_junk(s):
        return False
    if not any(ch.isalpha() for ch in s):
        return False
    if _IMAGE_EXT_RE.search(s):
        return False
    if ("/" in s or "\\" in s) and " " not in s and len(s) < 180:
        return False
    if s.startswith(("renpy.", "gui.", "config.", "persistent.")):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", s) and ("_" in s or "." in s):
        return False
    return True


def _balanced_delta(text: str) -> int:
    # Sufficient for the simple data containers we follow; quoted brackets are
    # harmless because only a non-zero result extends the collection window.
    return sum(text.count(ch) for ch in "([{") - sum(text.count(ch) for ch in ")]}")


class ModInterfaceParser:
    """Conservative parser for interface-facing text only."""

    def parse_text(self, content: str, file_path: str, source_kind: str = "rpy") -> List[ModTextCandidate]:
        lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        candidates: List[ModTextCandidate] = []
        screen_blocks: List[Tuple[str, int, int]] = []
        global_variable_refs: Set[str] = set()
        current_screen = ""
        screen_indent = -1
        screen_start = -1

        # Pass 1: locate screens and direct screen-language strings.
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            sm = _SCREEN_RE.match(line)
            if sm:
                if current_screen:
                    screen_blocks.append((current_screen, screen_start, idx - 1))
                current_screen = sm.group(1)
                screen_indent = _indent(line)
                screen_start = idx
                continue

            if current_screen and _indent(line) <= screen_indent and not line.lstrip().startswith(("#", "$")):
                screen_blocks.append((current_screen, screen_start, idx - 1))
                current_screen = ""
                screen_indent = -1
                screen_start = -1

            if not current_screen:
                say_match = _SAY_RE.match(line) or _MENU_CHOICE_RE.match(line)
                if say_match:
                    # Say/menu strings are Ren'Py statements, not Python: decode them
                    # like Ren'Py so they match its translation table exactly.
                    value = _first_statement_string(say_match.group("expr"))
                    if value is not None and _looks_like_ui_text(value):
                        candidates.append(ModTextCandidate(value, file_path, idx, "__global_ui__", source_kind, "high", "say_or_menu_literal"))
                else:
                    variable_say = re.match(r"^\s*(?:[A-Za-z_]\w*\s+)?([A-Za-z_]\w*)\s*$", line)
                    if variable_say:
                        global_variable_refs.add(variable_say.group(1))
                continue

            # Explicit UI statements.
            um = _UI_STMT_RE.match(line)
            if um:
                expr = um.group("expr")
                marked = list(_MARKED_RE.finditer(expr))
                if marked:
                    for mm in marked:
                        value = _decode_literal(mm.group("q"), mm.group("body"))
                        if value is not None and _looks_like_ui_text(value):
                            candidates.append(ModTextCandidate(value, file_path, idx, current_screen, source_kind, "high", "screen_marked"))
                else:
                    first = next(iter(_iter_string_literals(expr)), None)
                    if first is not None and _looks_like_ui_text(first):
                        candidates.append(ModTextCandidate(first, file_path, idx, current_screen, source_kind, "high", "screen_literal"))

            # Marked strings anywhere inside the screen expression tree.
            for mm in _MARKED_RE.finditer(line):
                value = _decode_literal(mm.group("q"), mm.group("body"))
                if value is not None and _looks_like_ui_text(value):
                    candidates.append(ModTextCandidate(value, file_path, idx, current_screen, source_kind, "high", "screen_marked"))

        if current_screen:
            screen_blocks.append((current_screen, screen_start, len(lines)))

        # Pass 2: explicitly marked strings are translatable wherever they
        # occur, including dialogue helpers and Python-embedded UI data.
        line_to_screen: Dict[int, str] = {}
        for name, start, end in screen_blocks:
            for n in range(start, end + 1):
                line_to_screen[n] = name
        for idx, line in enumerate(lines, 1):
            if idx in line_to_screen or line.lstrip().startswith("#"):
                continue
            if _PY_UI_CALL_RE.search(line):
                for value in _iter_string_literals(line):
                    if _looks_like_ui_text(value):
                        candidates.append(ModTextCandidate(value, file_path, idx, "__global_ui__", source_kind, "high", "python_ui_call"))
            for mm in _MARKED_RE.finditer(line):
                value = _decode_literal(mm.group("q"), mm.group("body"))
                if value is not None and _looks_like_ui_text(value):
                    candidates.append(ModTextCandidate(value, file_path, idx, "__global_ui__", source_kind, "high", "marked_global_ui"))

        # Pass 3: follow simple literal variables referenced by screens or
        # dialogue statements, retaining screen context where it is known.
        referenced_by_screen: Dict[str, Set[str]] = {}
        for identifier in global_variable_refs:
            referenced_by_screen.setdefault(identifier, set()).add("__global_ui__")
        for name, start, end in screen_blocks:
            for screen_line in lines[start - 1:end]:
                for ident in _IDENTIFIER_RE.findall(screen_line):
                    if ident not in _SCREEN_KEYWORDS and not ident.startswith("renpy"):
                        referenced_by_screen.setdefault(ident, set()).add(name)

        if referenced_by_screen:
            i = 0
            while i < len(lines):
                line = lines[i]
                am = _ASSIGN_RE.match(line)
                if not am or am.group(1) not in referenced_by_screen:
                    i += 1
                    continue
                var_name = am.group(1)
                expr_lines = [am.group(2)]
                delta = _balanced_delta(am.group(2))
                j = i + 1
                while delta > 0 and j < len(lines) and j - i < 80:
                    expr_lines.append(lines[j])
                    delta += _balanced_delta(lines[j])
                    j += 1
                expr = "\n".join(expr_lines)
                for value in _iter_string_literals(expr):
                    if not _looks_like_ui_text(value):
                        continue
                    for screen_name in sorted(referenced_by_screen[var_name]):
                        candidates.append(ModTextCandidate(
                            value, file_path, i + 1, screen_name, source_kind,
                            "medium", f"screen_data:{var_name}"
                        ))
                i = max(j, i + 1)

        # Exact de-duplication inside one source while retaining first/best location.
        seen: Set[Tuple[str, str]] = set()
        out: List[ModTextCandidate] = []
        for candidate in candidates:
            key = (candidate.text, candidate.screen)
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
        return out
