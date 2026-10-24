from collections import defaultdict


def unresolved(entries, results):
    for o in entries:
        r=results.get(o.occurrence_id)
        if not r or r.status not in ('accepted','preserved_approved') or not r.written:
            yield {'occurrence_id':o.occurrence_id,'path':o.path,'line':o.line,'context':o.context,
                   'original':o.original,'candidate':r.candidate if r else '',
                   'status':r.status if r else 'missing','reasons':r.reasons if r else ['no_result'],
                   'provenance':o.provenance}


def group_by_cause(rows):
    groups=defaultdict(list)
    for r in rows:
        groups[r['status']].append(r)
    return dict(groups)
