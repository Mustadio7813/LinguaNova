"""Main worker OCR integration: real Tesseract/codecs and controlled provider."""
import json
import shutil
import sys
from pathlib import Path

import pytest

from src.core.pipeline.orchestrator import TranslationPipeline, PipelineResult, PipelineStage
from src.core.translator import TranslationEngine, TranslationManager, TranslationResult
from src.utils.config import ConfigManager
from src.core.native_image_pipeline import install_images
from linguanova_next.core.work_queue import WorkQueue, CancelledJob


@pytest.fixture
def native_project(tmp_path):
    root = Path(__file__).resolve().parents[1]
    project = tmp_path / "Juego con espacios á"
    shutil.copytree(root / "next_fixtures/native_slot_game", project)
    return project


def pipeline_for(tmp_path, project):
    config = ConfigManager(str(tmp_path / "config.json"))
    config.data_dir = str(tmp_path / "data")
    manager = TranslationManager(config_manager=config)
    pipeline = TranslationPipeline(config, manager)
    pipeline.configure(str(project), "french", "english", TranslationEngine.GOOGLE, auto_unren=False)
    pipeline.image_options = {"enabled": True, "image_sources": "all", "ocr_source": "eng"}
    return pipeline


def test_main_worker_finishes_after_real_ocr_and_installs_images(tmp_path, native_project):
    pipeline = pipeline_for(tmp_path, native_project)
    calls = []
    async def controlled(requests):
        calls.extend(requests)
        return [TranslationResult(r.text, "Continuer", r.source_lang, r.target_lang, r.engine, True) for r in requests]
    pipeline.translation_manager.translate_batch = controlled
    pipeline._run_pipeline = lambda: PipelineResult(True, "Text saved", PipelineStage.COMPLETED, {"total": 1}, str(native_project / "game/tl/french"))
    finished = []
    pipeline.finished.connect(finished.append)
    pipeline.run()
    assert len(finished) == 1
    report = finished[0].stats["images"]
    assert report["status"] == "completed", report
    assert report["counts"]["translated"] == 4, report
    assert calls and all(r.engine == pipeline.engine and r.target_lang == "fr" for r in calls)
    assert all((native_project / "game" / p).is_file() for p in report["installed"])
    assert (native_project / "game/tl/french/images/buttons/continue_normal.png").is_file()


def test_disabled_ocr_keeps_the_main_text_flow(tmp_path, native_project):
    pipeline = pipeline_for(tmp_path, native_project)
    pipeline.image_options["enabled"] = False
    original = PipelineResult(True, "Text saved", PipelineStage.COMPLETED)
    pipeline._run_pipeline = lambda: original
    finished = []
    pipeline.finished.connect(finished.append)
    pipeline.run()
    assert finished == [original] and original.stats is None


def test_missing_ocr_is_reported_without_claiming_full_success(tmp_path, native_project):
    pipeline = pipeline_for(tmp_path, native_project)
    pipeline.image_options["tesseract_executable"] = str(tmp_path / "missing-tesseract")
    pipeline._run_pipeline = lambda: PipelineResult(True, "Text saved", PipelineStage.COMPLETED)
    finished = []
    pipeline.finished.connect(finished.append)
    pipeline.run()
    assert finished[0].success and finished[0].stats["partial"]
    assert finished[0].stats["images"]["status"] == "blocked"
    assert not (native_project / "game/tl/french/images").exists()


def test_image_installation_rolls_back_a_cancelled_commit(tmp_path):
    stage = tmp_path / "stage/game/tl/french/images"
    stage.mkdir(parents=True)
    (stage / "a.png").write_bytes(b"new a")
    (stage / "b.png").write_bytes(b"new b")
    game = tmp_path / "receiver/game"
    target = game / "tl/french/images/a.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"original a")
    queue = WorkQueue()
    count = 0
    def check():
        nonlocal count
        count += 1
        if count == 2:
            raise CancelledJob()
    queue.check = check
    with pytest.raises(CancelledJob):
        install_images(stage.parents[3], game, tmp_path / "job", queue)
    assert target.read_bytes() == b"original a"
    assert not (target.parent / "b.png").exists()


def test_sources_are_python_310_syntax():
    import ast
    root = Path(__file__).resolve().parents[1]
    for name in ("start.py", "start_next.py", "src/core/native_image_pipeline.py", "src/backend/image_backend.py"):
        ast.parse((root / name).read_text(), feature_version=(3, 10))


def test_private_source_models_are_used_by_real_tesseract(tmp_path):
    from linguanova_next.adapters.ocr_provider import TesseractProvider
    provider = TesseractProvider()
    info = provider.available()
    private = tmp_path / "images/tessdata"
    private.mkdir(parents=True)
    shutil.copy2(Path(info['traineddata_directory']) / "eng.traineddata", private / "eng.traineddata")
    configured = TesseractProvider(component_root=private.parent / "components")
    assert Path(configured.available()['traineddata_directory']) == private
    assert configured.fingerprint('eng')['models'] == provider.fingerprint('eng')['models']


@pytest.mark.parametrize('compiled', [False, True])
def test_main_generator_respects_translation_owners_inside_rpa(tmp_path, native_project, compiled):
    sys.path.insert(0, str(Path(__file__).parent / 'next'))
    from test_ocr_resource_formats import rpa
    game = native_project / 'game'
    (game / 'continue.rpy').write_text('screen continue_button():\n    textbutton _("Continue") action NullAction()\n')
    if compiled:
        payload = (Path(__file__).parent / 'next/fixtures/ocr_scripts/existing_tl.rpyc').read_bytes()
        name = 'tl/french/previous.rpyc'
    else:
        payload = b'translate french strings:\n    old "Continue"\n    new "Continuer"\n'
        name = 'tl/french/previous.rpy'
    rpa(game / 'translation_owners.rpa', {name: payload})
    pipeline = pipeline_for(tmp_path, native_project)
    pipeline.config.translation_settings.output_mode = 'strings'
    assert pipeline._run_translate_command(str(native_project))
    generated = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (game / 'tl/french').rglob('*.rpy'))
    assert 'old "Continue"' not in generated


def test_image_only_game_runs_ocr_through_the_real_main_pipeline(tmp_path, native_project):
    game = native_project / 'game'
    for path in game.rglob('*.rpy'):
        path.unlink()
    (game / 'script.rpy').write_text('label start:\n    return\n')
    pipeline = pipeline_for(tmp_path, native_project)
    async def controlled(requests):
        return [TranslationResult(r.text, 'Continuer', r.source_lang, r.target_lang, r.engine, True) for r in requests]
    pipeline.translation_manager.translate_batch = controlled
    finished = []
    pipeline.finished.connect(finished.append)
    pipeline.run()
    assert finished[0].success, finished[0].message
    assert finished[0].stats['images']['counts']['translated'] == 4
    assert (game / 'tl/french/zzz_linguanova_images.rpy').is_file()
