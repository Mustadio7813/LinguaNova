from dataclasses import dataclass

PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class WorkerMessage:
    request_id: str
    kind: str
    payload: dict
    schema_version: int = PROTOCOL_VERSION

    def validate(self, request_id):
        if self.schema_version != PROTOCOL_VERSION or self.request_id != request_id:
            raise ValueError('Worker protocol/correlation mismatch')
        if self.kind not in ('progress', 'result', 'error', 'cancelled', 'request'):
            raise ValueError('Unknown worker message')
