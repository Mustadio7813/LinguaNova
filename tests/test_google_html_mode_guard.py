from types import SimpleNamespace

from src.core.translator import GoogleTranslator


def test_google_web_endpoints_force_disable_html_protection():
    cfg = SimpleNamespace(
        translation_settings=SimpleNamespace(
            use_multi_endpoint=True,
            enable_lingva_fallback=True,
            max_concurrent_threads=4,
            max_chars_per_request=1000,
            max_batch_size=50,
            aggressive_retry_translation=False,
            use_html_protection=True,
            request_delay=0.1,
        )
    )

    translator = GoogleTranslator(config_manager=cfg)

    assert translator.use_html_protection is False
