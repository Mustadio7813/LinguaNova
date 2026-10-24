# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — regression guard for the isolated MOD subsystem.

from __future__ import annotations

import hashlib
import re
from pathlib import Path


# Baseline updated for the authorized 1.1.1 core hot-switch fix; the MOD
# must continue to leave that new core implementation untouched.
EXPECTED_MAIN_HOOK_SHA256 = "cb112d59634f56a9ee9a418565963ccaaaeeb252af91e6a33d3d5457e67dd9fc"


def test_mod_does_not_change_main_runtime_hook():
    # Git converts LF to CRLF on Windows checkouts (.gitattributes "text=auto"),
    # so the hash is taken over the LF form stored in the repository.
    data = Path("src/core/runtime_hook_template.py").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == EXPECTED_MAIN_HOOK_SHA256


def test_mod_package_never_imports_main_runtime_hook():
    root = Path("src/ui_mod")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*import\s+src\.core\.runtime_hook_template\b", text, re.MULTILINE)
        assert not re.search(r"^\s*from\s+src\.core\.runtime_hook_template\s+import\b", text, re.MULTILINE)


def test_mod_navigation_is_first_class_and_visible():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert 'navKey: "nav_mod"' in qml
    assert 'navFallback: "MOD"' in qml
    assert 'navGlyph: "🧩"' in qml
    assert "// #MOD" in qml
