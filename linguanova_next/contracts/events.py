from dataclasses import dataclass, field
import time


@dataclass(frozen=True)
class JobEvent:
    job_id: str
    sequence: int
    kind: str
    message: str
    request_id: str = ''
    occurrence_id: str = ''
    resource_id: str = ''
    region_id: str = ''
    schema_version: int = 1
    timestamp: float = field(default_factory=time.time)
