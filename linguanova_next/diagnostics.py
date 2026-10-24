"""Durable diagnostics shared by the UI, preflight and translation runner."""
import json
import os
from pathlib import Path
import re
import threading
import traceback
from datetime import datetime, timezone


class Diagnostics:
    def __init__(self, data):
        self.path = Path(data) / 'diagnostics' / 'errors.jsonl'
        self._lock = threading.Lock()

    @staticmethod
    def redact(message):
        text = str(message)
        for key, value in os.environ.items():
            if key.startswith('LINGUANOVA_NEXT_') and key.endswith('_KEY') and value:
                text = text.replace(value, '[credential]')
        text = re.sub(r'(?i)(authorization|api[_-]?key|token|password)([\s:=]+)[^\s,;]+', r'\1\2[credential]', text)
        return text

    def record(self, phase, exc, *, project='', resource='', job_id='', severity='error'):
        row = {'time': datetime.now(timezone.utc).isoformat(), 'severity': severity,
               'phase': phase, 'project': str(project), 'resource': str(resource), 'job_id': job_id,
               'exception': type(exc).__name__, 'message': self.redact(exc),
               'traceback': self.redact(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)))}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        return f"{phase}: {row['message']} · Registro: {self.path}"
