# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — the engines' internal fallbacks keep the requested languages.
#
# SIMULATED: network methods are replaced by recorders; the engines' routing code
# (unchanged main code) runs for real. No request leaves the machine.
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from src.core.translator import TranslationEngine, TranslationRequest
from src.core.translators.google import GoogleTranslator
from src.core.translators.services import BingTranslator, DeepLTranslator
from src.ui_mod.engine_support import request_code
from src.ui_mod.languages import all_languages, resolve_language


def _reqs(n, sl, tl, engine=TranslationEngine.GOOGLE):
    return [TranslationRequest(text=f"Texto número {i}", source_lang=sl, target_lang=tl, engine=engine) for i in range(n)]


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.mark.parametrize("lang", ["spanish", "english", "portuguese", "french", "russian"])
def test_google_batch_fallbacks_keep_source_and_target(lang):
    tl = resolve_language(lang).api
    g = GoogleTranslator(config_manager=None)
    seen = []

    async def no_separator(batch):
        return None

    async def batchexecute(texts, sl, target):
        seen.append(("batchexecute", sl, target))
        return None                       # fail → next family

    async def clients5(text, sl, target):
        seen.append(("clients5", sl, target))
        return "ok"

    g._try_batch_separator = no_separator
    g._translate_via_batchexecute_batch = batchexecute
    g._translate_via_clients5 = clients5
    g._router.best_family_for_batch = lambda: g._router.FAMILY_BATCHEXECUTE
    order = iter([g._router.FAMILY_BATCHEXECUTE, g._router.FAMILY_CLIENTS5])
    g._router.best_family_for_batch = lambda: next(order, g._router.FAMILY_CLIENTS5)
    _run(g._multi_q(_reqs(3, "pt", tl)))
    assert seen and {(sl, t) for _, sl, t in seen} == {("pt", tl)}
    assert {name for name, _, _ in seen} >= {"batchexecute", "clients5"}


def test_google_lingva_fallback_keeps_languages():
    g = GoogleTranslator(config_manager=None)
    urls = []

    class Resp:
        status = 200
        async def json(self):
            return {"translation": "ok"}
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    class Session:
        def get(self, url, timeout=None):
            urls.append(url)
            return Resp()

    async def session():
        return Session()

    g._get_session = session
    g.lingva_instances = ["https://lingva.example"]
    _run(g._translate_via_lingva("Olá", "pt", "pl"))
    assert urls and "/api/v1/pt/pl/" in urls[0]


@pytest.mark.parametrize("lang,expected", [
    ("spanish", "es"), ("english", "en"), ("portuguese", "pt"),
    ("french", "fr"), ("russian", "ru"),
])
def test_bing_sends_mapped_codes_and_fallback_gets_identical_requests(lang, expected):
    api = resolve_language(lang).api
    b = BingTranslator()
    sent = []

    async def fail(indices, texts, src, tgt, raw, errors):
        sent.append((src, tgt))
        for i in indices:
            errors[i] = ("HTTP 503", False)

    class Fallback:
        _engine = TranslationEngine.GOOGLE
        received = []
        async def translate_batch(self, requests):
            Fallback.received.extend(requests)
            return [SimpleNamespace(success=True, translated_text="ok", original_text=r.text, confidence=0.5) for r in requests]

    b._translate_indices = fail
    b.fallback_translator = Fallback()
    out = _run(b.translate_batch(_reqs(2, "pt", api, TranslationEngine.BING)))
    assert sent == [("pt", expected)]
    assert {(r.source_lang, r.target_lang) for r in Fallback.received} == {("pt", api)}
    assert all(r.success for r in out)


def test_deepl_receives_mod_codes_for_all_documented_targets():
    d = DeepLTranslator.__new__(DeepLTranslator)
    for lang in all_languages():
        code = request_code(TranslationEngine.DEEPL, lang, "target")
        assert d._map_lang(code, True) == code
