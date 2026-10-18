import json
from pathlib import Path

from src.core.translator import TranslationEngine, TranslationManager, TranslationResult


def test_save_cache_persists_empty_cache_to_disk(tmp_path: Path) -> None:
    cache_file = tmp_path / "translation_cache.json"
    manager = TranslationManager()

    manager._cache[("deepl", "auto", "tr", "About")] = TranslationResult(
        original_text="About",
        translated_text="Hakkinda",
        source_lang="auto",
        target_lang="tr",
        engine=TranslationEngine.DEEPL,
        success=True,
    )
    manager.save_cache(str(cache_file))

    manager._cache.clear()
    manager.save_cache(str(cache_file))

    written = json.loads(cache_file.read_text(encoding="utf-8"))
    assert written == {}
