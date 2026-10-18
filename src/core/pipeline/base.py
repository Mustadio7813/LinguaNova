# -*- coding: utf-8 -*-
"""
Pipeline base types: PipelineStage, PipelineResult, PipelineWorker.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class PipelineStage(Enum):
    """Pipeline aşamaları"""
    IDLE = "idle"
    VALIDATING = "validating"
    UNRPA = "unrpa"
    GENERATING = "generating"
    PARSING = "parsing"
    TRANSLATING = "translating"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class PipelineResult:
    """Pipeline sonucu"""
    success: bool
    message: str
    stage: PipelineStage
    stats: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class PipelineWorker(QThread):
    """Pipeline için QThread wrapper"""

    stage_changed = pyqtSignal(str, str)
    progress_updated = pyqtSignal(int, int, str)
    log_message = pyqtSignal(str, str)
    finished = pyqtSignal(object)
    show_warning = pyqtSignal(str, str)

    def __init__(self, pipeline: Any, parent: Optional[QObject] = None) -> None:
        """Initializes the background worker and migrates pipeline thread affinity."""
        super().__init__(parent)
        self.pipeline = pipeline
        # Qt Thread Affinity: Move pipeline QObject to this worker thread
        if hasattr(self.pipeline, "moveToThread"):
            self.pipeline.moveToThread(self)

        self.pipeline.stage_changed.connect(self.stage_changed)
        self.pipeline.progress_updated.connect(self.progress_updated)
        self.pipeline.log_message.connect(self.log_message)
        self.pipeline.finished.connect(self._on_finished)
        self.pipeline.show_warning.connect(self.show_warning)

    def _on_finished(self, result: PipelineResult) -> None:
        """Propagates pipeline completion result."""
        self.finished.emit(result)

    def run(self) -> None:
        """Executes pipeline processing in the worker thread."""
        self.pipeline.run()

    def stop(self) -> None:
        """Signals the underlying pipeline to abort execution."""
        self.pipeline.stop()
