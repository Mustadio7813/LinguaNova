from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reasons: tuple = ()
    warnings: tuple = ()
    linguistic_review: str = 'unverified'


@dataclass(frozen=True)
class EntryResult:
    occurrence_id: str
    job_identity: str
    status: str
    candidate: str = ''
    written: str = ''
    reasons: tuple = ()
    flags: tuple = ()
    provider: str = ''
    model: str = ''
    request_id: str = ''
    output_path: str = ''
    provenance: str = 'provider'
    linguistic_review: str = 'unverified'
