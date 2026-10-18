# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — regression guard for the isolated MOD subsystem.

from __future__ import annotations

import hashlib
import re
from pathlib import Path


EXPECTED_MAIN_HOOK_SHA256 = "bee504f9327f240b7714949615b4077a5687feb7583e00ab9fa7e5f08782132a"


def test_mod_does_not_change_main_runtime_hook():
    data = Path("src/core/runtime_hook_template.py").read_bytes()
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
