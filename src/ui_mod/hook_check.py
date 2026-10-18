# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — stand-in for the parts of Ren'Py the generated hook touches.
"""Execute a generated hook against a minimal imitation of Ren'Py.

Used before publishing (catches syntax errors, NameError, a crash while
registering strings) and by the tests. It reproduces only the behaviour the hook
relies on, copied from Ren'Py's source: ``StringTranslator.add`` raises on a
duplicate ``old`` (renpy/translation/__init__.py) and ``translate_string`` looks
up the whole string. It is NOT Ren'Py: screens and fonts are not rendered.
"""
from __future__ import annotations

import io
import json
import re
from types import SimpleNamespace
from typing import Dict, Optional

from .ui_mod_hook_template import python_body


class FakeStringTranslator:
    def __init__(self):
        self.translations: Dict[str, str] = {}

    def add(self, old, new, newloc):
        if old in self.translations:  # same rule as Ren'Py
            raise Exception('A translation for "{}" already exists.'.format(old))
        self.translations[old] = new

    def translate(self, old):
        return self.translations.get(old, old)


class _StringTables(dict):
    def __missing__(self, key):
        value = self[key] = FakeStringTranslator()
        return value


class FakeConfig:
    def __init__(self):
        self.replace_text = None
        self.say_menu_text_filter = None
        self.start_callbacks = []
        self.overlay_screens = []
        self.font_replacement_map = {}
        self.default_language = None
        self.rtl = False
        from collections import defaultdict
        self.language_callbacks = defaultdict(list)


def make_env(language: Optional[str] = None, files: Optional[Dict[str, object]] = None):
    """Return (namespace, config, translator, preferences) for exec-ing a hook body."""
    files = files or {}

    class Loader:
        @staticmethod
        def load(path):
            if path not in files:
                raise IOError(path)
            value = files[path]
            if not isinstance(value, (bytes, str)):
                value = json.dumps(value)
            return io.BytesIO(value.encode("utf-8") if isinstance(value, str) else value)

    translator = SimpleNamespace(strings=_StringTables(), languages=set())
    preferences = SimpleNamespace(language=language)
    logged = []
    renpy = SimpleNamespace(
        game=SimpleNamespace(preferences=preferences, script=SimpleNamespace(translator=translator)),
        loader=Loader, log=logged.append, get_screen=lambda name: None,
    )
    config = FakeConfig()
    namespace = {"config": config, "renpy": renpy, "persistent": SimpleNamespace(), "_log": logged}
    return namespace, config, translator, preferences


def run_hook(rpy_text: str, language: Optional[str] = None, files=None, preexisting=None):
    """Exec the hook, optionally pre-fill native tables, run start callbacks."""
    namespace, config, translator, preferences = make_env(language, files)
    for lang, entries in (preexisting or {}).items():
        for old, new in entries.items():
            translator.strings[lang].add(old, new, None)
    exec(compile(python_body(rpy_text), "linguanova_mod_hook", "exec"), namespace, namespace)
    for callback in list(config.start_callbacks):
        callback()
    return namespace, config, translator, preferences


def displayed(translator, preferences, text: str) -> str:
    """What Ren'Py would show for ``text``: native string table, whole string."""
    return translator.strings[preferences.language].translate(text) if preferences.language else text


_TRANSLATE_RE = re.compile(r"^translate\s+(\S+)\s+python\s*:\s*$", re.M)


def check_hook(rpy_text: str) -> Dict[str, int]:
    """Self-check before publishing; raises on any problem."""
    namespace, config, translator, _ = run_hook(rpy_text)
    if not callable(config.replace_text):
        raise RuntimeError("Generated MOD hook did not install config.replace_text")
    if not config.start_callbacks:
        raise RuntimeError("Generated MOD hook did not register its start callback")
    config.replace_text("LinguaNova MOD self-check")
    embedded = namespace.get("_lnmod_embedded", {})
    registered = namespace.get("_lnmod_registered", {})
    for language, data in embedded.items():
        added, kept = registered.get(language, (0, 0))
        if added + kept != len(data.get("mapping", {})):
            raise RuntimeError(f"String registration incomplete for {language}")
    for name in _TRANSLATE_RE.findall(rpy_text):
        if name != "None" and not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            raise RuntimeError(f"Invalid language name in translate block: {name}")
    if "screen lnmod_language_panel():" not in rpy_text:
        raise RuntimeError("Language panel missing")
    return {lang: sum(registered.get(lang, (0, 0))) for lang in embedded}
