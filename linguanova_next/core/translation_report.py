from collections import Counter
import math


def metric(numerator,denominator):
    if denominator==0:
        return {'numerator':numerator,'denominator':0,'percent':None,'display':'No aplicable'}
    value=math.floor(10000*numerator/denominator)/100
    return {'numerator':numerator,'denominator':denominator,'percent':value,'display':f'{numerator}/{denominator} ({value:.2f} %)'}


def summarize(entries,results,visual=None):
    statuses=Counter(r.status for r in results.values())
    accepted=sum(r.status=='accepted' and bool(r.written) for r in results.values())
    preserved=sum(r.status=='preserved_approved' and bool(r.written) for r in results.values())
    changed=sum(bool(results.get(o.occurrence_id)) and bool(results[o.occurrence_id].written) and results[o.occurrence_id].written!=o.original for o in entries)
    translatable=sum(o.publishable for o in entries)
    return {'schema_version':1,'status_counts':dict(statuses),
            'processing':metric(len(results),len(entries)),
            'textual_change':metric(changed,len(entries)),
            'validated_translation':metric(accepted,translatable),
            'inventory_resolution':metric(accepted+preserved,len(entries)),
            'visual_coverage':visual or metric(0,0),
            'runtime_routes':{'observed':[],'unverified':'No real game execution attached'},
            'editorial_review':'Required; automatic validation is not editorial certification'}
