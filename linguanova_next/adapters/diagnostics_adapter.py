from src.core.tl_parser import get_translation_stats


def legacy_stats(files, job_identity):
    # A read-only view, deliberately retaining the original counter semantics.
    return {'job_identity':job_identity,'legacy_counters':get_translation_stats(files),
            'note':'Legacy counters have a different inventory; not added to new metrics'}
