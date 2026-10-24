from dataclasses import dataclass
from ..util import digest


@dataclass(frozen=True)
class Occurrence:
    occurrence_id: str
    resource_id: str
    path: str
    line: int
    original: str
    context: str
    kind: str
    source_hash: str
    provenance: str = 'base_parser'
    publishable: bool = True
    block_id: str = ''
    character: str = ''

    @classmethod
    def create(cls, path, line, original, context, kind, source_hash, **kwargs):
        key = digest([path, line, original, context])
        return cls(key, digest(path), path, int(line), original, context, kind, source_hash, **kwargs)


@dataclass(frozen=True)
class Candidate:
    occurrence_id: str
    text: str
    provider: str
    model: str
    source_language: str
    request_id: str
    job_identity: str
    attempt: int = 1
