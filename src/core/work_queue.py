# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova serial work queue.
"""Thread-safe append-only queue for long-running LinguaNova jobs.

Submitting a new job never cancels, replaces, or interrupts the active job.
The active job completes first; queued jobs are dispatched in FIFO order.
Only an explicit user stop/shutdown path may request cancellation.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import threading
from typing import Any, Deque, Dict, Optional, Tuple


@dataclass(frozen=True)
class WorkItem:
    sequence: int
    kind: str
    payload: Dict[str, Any]


class SerialWorkQueue:
    """FIFO queue with exactly one active item and no submit-time cancellation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pending: Deque[WorkItem] = deque()
        self._active: Optional[WorkItem] = None
        self._sequence = 0

    def submit(self, kind: str, payload: Dict[str, Any]) -> Tuple[WorkItem, bool]:
        """Submit work. Returns ``(item, start_now)``.

        Crucial invariant: if another item is active, it is left untouched and
        the new item is appended to the queue.
        """
        if not kind:
            raise ValueError("work kind must not be empty")
        with self._lock:
            self._sequence += 1
            item = WorkItem(self._sequence, kind, dict(payload))
            if self._active is None:
                self._active = item
                return item, True
            self._pending.append(item)
            return item, False

    def complete_active(self) -> Optional[WorkItem]:
        """Finish the current item and promote the next FIFO item, if any."""
        with self._lock:
            self._active = None
            if self._pending:
                self._active = self._pending.popleft()
            return self._active

    @property
    def active(self) -> Optional[WorkItem]:
        with self._lock:
            return self._active

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._active is not None

    def snapshot(self) -> Tuple[Optional[WorkItem], Tuple[WorkItem, ...]]:
        with self._lock:
            return self._active, tuple(self._pending)
