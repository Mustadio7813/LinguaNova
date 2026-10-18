# -*- coding: utf-8 -*-
"""
Tests for PipelineWorker (QThread lifecycle and signal routing).
"""

import time
import pytest
from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication
from src.core.pipeline.base import PipelineWorker, PipelineResult, PipelineStage


class DummyPipeline(QObject):
    stage_changed = pyqtSignal(str, str)
    progress_updated = pyqtSignal(int, int, str)
    log_message = pyqtSignal(str, str)
    finished = pyqtSignal(object)
    show_warning = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.should_stop = False
        self.ran = False

    def run(self):
        self.ran = True
        self.stage_changed.emit("parsing", "Extracting strings")
        self.progress_updated.emit(50, 100, "Halfway")
        self.log_message.emit("info", "Processing...")
        self.show_warning.emit("Warning", "Check this")

        while not self.should_stop:
            time.sleep(0.01)

        result = PipelineResult(
            success=True,
            message="Stopped cleanly",
            stage=PipelineStage.SAVING,
        )
        self.finished.emit(result)

    def stop(self):
        self.should_stop = True


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app


def test_pipeline_worker_signals_and_lifecycle(qapp):
    pipeline = DummyPipeline()
    worker = PipelineWorker(pipeline)

    received_stages = []
    received_progress = []
    received_logs = []
    received_warnings = []
    received_results = []

    worker.stage_changed.connect(lambda s, msg: received_stages.append((s, msg)))
    worker.progress_updated.connect(lambda cur, tot, txt: received_progress.append((cur, tot, txt)))
    worker.log_message.connect(lambda lvl, msg: received_logs.append((lvl, msg)))
    worker.show_warning.connect(lambda t, msg: received_warnings.append((t, msg)))
    worker.finished.connect(lambda res: received_results.append(res))

    worker.start()
    assert worker.isRunning()

    # Allow worker thread to run dummy workload
    for _ in range(50):
        qapp.processEvents()
        if pipeline.ran and len(received_stages) > 0:
            break
        time.sleep(0.02)

    assert pipeline.ran is True
    assert len(received_stages) >= 1
    assert received_stages[0] == ("parsing", "Extracting strings")
    assert len(received_progress) >= 1
    assert received_progress[0] == (50, 100, "Halfway")
    assert len(received_logs) >= 1
    assert len(received_warnings) >= 1

    # Signal stop and wait for worker thread to finish
    worker.stop()
    finished = worker.wait(3000)
    assert finished is True
    assert not worker.isRunning()

    # Process pending events for the finished signal
    qapp.processEvents()
    assert len(received_results) == 1
    assert received_results[0].success is True
