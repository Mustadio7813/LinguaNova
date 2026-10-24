from collections import Counter
from ..core.translation_report import metric


def visual_audit(resources,results):
    states=Counter(v.get('status','uncertain') for v in results.values())
    reviewed=sum(v.get('status')=='reviewed' for v in results.values())
    exported=sum(v.get('status') in ('reviewed','exported_automatic') for v in results.values())
    return {'counts':dict(states),'coverage':metric(exported,len(resources)),
            'human_reviewed_coverage':metric(reviewed,len(resources)),
            'automatic_exports':states.get('exported_automatic',0),
            'same_language_preserved':states.get('preserved_source_language',0),
            'no_detection_is_not_no_text':True,'unobserved_runtime_resources':'not verified'}
