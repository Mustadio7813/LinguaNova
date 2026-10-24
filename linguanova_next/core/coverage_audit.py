"""Pure, read-only reconciliation of inventoried entries and bytes on disk."""
from dataclasses import replace
from pathlib import Path
from ..contracts.result import EntryResult
from ..util import load_json
from .translation_report import summarize


def audit(job, entries, results, written_mapping):
    reconciled={}
    for o in entries:
        r=results.get(o.occurrence_id)
        if r and r.job_identity!=job.identity:
            raise ValueError('Audit cannot mix jobs/locales/revisions')
        if not r:
            r=EntryResult(o.occurrence_id,job.identity,'missing',reasons=('no_result',))
        actual=written_mapping.get(o.original,'')
        if r.status in ('accepted','preserved_approved'):
            if not actual or actual!=r.candidate:
                r=replace(r,status='write_error',written=actual,reasons=tuple(r.reasons)+('written_value_mismatch',))
            else:
                r=replace(r,written=actual)
        reconciled[o.occurrence_id]=r
    report=summarize(entries,reconciled)
    report['job_identity']=job.identity
    report['target_identity']=list(job.target_identity)
    return report,reconciled
