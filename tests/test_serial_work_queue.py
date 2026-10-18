# -*- coding: utf-8 -*-
from src.core.work_queue import SerialWorkQueue


def test_new_requests_queue_without_stopping_active_job():
    q = SerialWorkQueue()
    first, start_first = q.submit("translation", {"id": 1})
    second, start_second = q.submit("mod_generate", {"id": 2})
    third, start_third = q.submit("translation", {"id": 3})

    assert start_first is True
    assert start_second is False
    assert start_third is False
    assert q.active == first
    assert q.pending_count == 2

    assert q.complete_active() == second
    assert q.pending_count == 1
    assert q.complete_active() == third
    assert q.pending_count == 0
    assert q.complete_active() is None

def test_backend_submit_path_never_stops_active_work():
    from pathlib import Path

    source = Path("src/backend/app_backend.py").read_text(encoding="utf-8")
    submit_block = source.split("    def _submit_work", 1)[1].split("    def _dispatch_work_item", 1)[0]
    assert "stopTranslation" not in submit_block
    assert "stop_translation" not in submit_block
    assert "pipeline.stop" not in submit_block

    start_block = source.split("    def startTranslation", 1)[1].split("    def _start_pipeline_translation", 1)[0]
    assert 'self._submit_work("translation"' in start_block
    assert "if self._is_translating" not in start_block

