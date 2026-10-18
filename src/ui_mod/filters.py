# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — classify scanned strings that are program code or developer diagnostics.
"""Exclude code and debug strings from MOD translation.

Evidence (goodluke_thegame MOD, 2026-10-17): the previous scanner sent Python
source (``_DEVSB = {...}``), expressions (``"color" in h.who_args``,
``max(0, CONFIG[0] - PAD[0])``) and logging formats (``" | reason=%s"``,
``"(erro lendo rotas: %r)"``) to the engines, which "translated" identifiers
(``card``→``karta``, ``in``→``w``). Such strings are not player-visible text.
"""
from __future__ import annotations

import ast
import io
import re
import tokenize
from typing import Optional

_MARKED_CALL_NAMES = {"_", "__", "___", "_p"}


def unwrap_marked_literal(text: str) -> Optional[str]:
    """Return the literal of a whole-string ``_("...")`` expression, else None.

    Older extractors stored the full call as the source text; the player sees only
    the literal, so that literal is what must be translated.
    """
    candidate = (text or "").strip()
    if not candidate.endswith(")") or "(" not in candidate:
        return None
    try:
        node = ast.parse(candidate, mode="eval").body
    except (SyntaxError, ValueError):
        return None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _MARKED_CALL_NAMES
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return None

_DEBUG_FORMAT_RE = re.compile(r"%r|\{![rs]\}|\{[^{}]*!r\}|\b[A-Za-z_]\w*=%[-#0 +]*\d*(?:\.\d+)?[sdrifx]")
_CODE_LINE_RE = re.compile(
    r"^\s*(?:"
    r"(?:def|class|import|from|return|raise|elif|while|with|try|except|lambda)\b"
    r"|[A-Za-z_][\w.]*(?:\[[^\]]*\])?\s*(?:[+\-*/%|&]?=)(?!=)"
    r"|[\"'][^\"']*[\"']\s*:\s*[\"'#\w\[{(]"
    r"|[}\])],?\s*$"
    r")"
)



def _expression_is_code(text: str) -> bool:
    candidate = text.strip()
    if not candidate or "\n" in candidate or len(candidate) > 300:
        return False
    try:
        node = ast.parse(candidate, mode="eval").body
    except (SyntaxError, ValueError):
        return False
    # "helena.main01#110 fechado. À noite..." only parses because "#" starts a
    # comment; such strings are prose with an id prefix, not an expression.
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(candidate).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return False
    if any(tok.type == tokenize.COMMENT for tok in tokens):
        return False
    if isinstance(node, (ast.Constant, ast.Name)):
        return False
    # "yes or no", "A and B", "-1" are prose/UI, not code.
    if isinstance(node, (ast.BoolOp, ast.UnaryOp)) and all(
        isinstance(v, (ast.Name, ast.Constant)) for v in ast.walk(node) if isinstance(v, ast.expr) and v is not node
    ):
        return False
    # Prose such as "Save (1)", "Slot [2]" or "This is it" is also valid Python;
    # only code-shaped spelling (no space before "(" / "[", dotted names,
    # quoted operands, ==/!=) counts.
    tight_call = re.search(r"[\w\])]\(", candidate) is not None
    tight_index = re.search(r"[\w\])]\[", candidate) is not None
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and tight_call:
            return True
        if isinstance(sub, ast.Subscript) and tight_index:
            return True
        if isinstance(sub, ast.Attribute) and re.search(r"[A-Za-z_]\w*\.[A-Za-z_]", candidate):
            return True
        if isinstance(sub, (ast.Lambda, ast.Dict, ast.ListComp, ast.DictComp, ast.GeneratorExp)):
            return True
        if isinstance(sub, ast.Compare) and (
            any(isinstance(op, (ast.Eq, ast.NotEq)) for op in sub.ops)
            or any(isinstance(part, ast.Constant) and isinstance(part.value, str)
                   for part in [sub.left, *sub.comparators])
        ):
            return True
    return False


def code_exclusion_reason(text: str) -> Optional[str]:
    """Return why ``text`` is code/diagnostics, or None if it may be player-visible."""
    value = text or ""
    stripped = value.strip()
    if not stripped:
        return None
    if _DEBUG_FORMAT_RE.search(value):
        return "debug_format"
    lines = [line for line in value.splitlines() if line.strip()]
    if len(lines) >= 2:
        code_lines = sum(1 for line in lines if _CODE_LINE_RE.match(line))
        if code_lines * 2 >= len(lines):
            return "python_source"
    if _expression_is_code(stripped):
        return "python_expression"
    if "\n" in stripped and stripped[:1] in "[({" and stripped[-1:] in "])}":
        try:
            node = ast.parse(stripped, mode="eval").body
            if not isinstance(node, ast.Constant):
                return "python_expression"
        except (SyntaxError, ValueError):
            pass
    tokens = stripped.split()
    if 1 <= len(tokens) <= 4 and any(re.fullmatch(r"[A-Za-z]\w*_\w+", tok) for tok in tokens) \
            and all(re.fullmatch(r"[A-Za-z_]\w*", tok) for tok in tokens):
        return "identifier_list"
    if len(lines) == 1 and _CODE_LINE_RE.match(stripped) and re.search(r"=\s*[\[{(\"'\d]", stripped) \
            and not re.search(r"\s[^\W\d_]{2,}\s+[^\W\d_]{2,}\s+[^\W\d_]{2,}", stripped.split("=", 1)[1]):
        return "python_assignment"
    return None
