from src.core.translator import GoogleTranslator, TranslationEngine, TranslationRequest


def test_google_preprotected_request_skips_reprotect():
    translator = GoogleTranslator(config_manager=None)
    placeholders = {"⟦RLPHABC123_0⟧": "[player]"}

    req = TranslationRequest(
        text="Merhaba ⟦RLPHABC123_0⟧",
        source_lang="en",
        target_lang="tr",
        engine=TranslationEngine.GOOGLE,
        metadata={
            "preprotected": True,
            "placeholders": placeholders,
            "original_text": "Merhaba [player]",
        },
    )

    protected_text, prepared_placeholders, use_html = translator._prepare_request_protection(req)

    assert protected_text == req.text
    assert prepared_placeholders is placeholders
    assert use_html is False


def test_google_non_preprotected_request_uses_token_protection():
    translator = GoogleTranslator(config_manager=None)

    req = TranslationRequest(
        text="Merhaba [player]",
        source_lang="en",
        target_lang="tr",
        engine=TranslationEngine.GOOGLE,
        metadata={},
    )

    protected_text, placeholders, use_html = translator._prepare_request_protection(req)

    assert protected_text != req.text
    assert placeholders
    assert use_html is False
