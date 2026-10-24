"""Atomic checkpoints and one durable, append-only audit stream per job."""
from pathlib import Path
import json
import os
import threading
from ..util import atomic_json, jsonable, load_json
from ..contracts.result import EntryResult


class ResultStore:
    def __init__(self, root, job):
        self.directory = Path(root)/'jobs'/job.job_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.job = job
        self._lock = threading.RLock()

    def create(self):
        path = self.directory/'job.json'
        existing = load_json(path)
        if existing and existing != jsonable(self.job):
            raise ValueError('Immutable job already exists with different identity')
        if not existing:
            atomic_json(path, self.job)

    def append(self, name, payload):
        if '/' in name or '\\' in name:
            raise ValueError('Audit stream must be local')
        with self._lock:
            with (self.directory/name).open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(jsonable(payload), ensure_ascii=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())

    def put_result(self, result):
        if result.job_identity != self.job.identity:
            raise ValueError('Result from another job')
        atomic_json(self.directory/'results'/f'{result.occurrence_id}.json', result)

    def results(self):
        return {p.stem: EntryResult(**load_json(p)) for p in sorted((self.directory/'results').glob('*.json'))}

    def state(self, **values):
        atomic_json(self.directory/'state.json', {'schema_version':1,'job_identity':self.job.identity,**values})
