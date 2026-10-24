from ..util import digest
from ..version import VERSION


def share_manifest(outputs,files,ui,limitations,revision=1):
    descriptor={'schema_version':1,'project_id':outputs[0]['project_id'],
                'sources_hash':outputs[0]['sources_hash'],'destinations':[o['destination'] for o in outputs],
                'files':files,'revision':revision,'generator_version':VERSION,
                'compatibility':{'renpy':'Requires exact-game verification; source .rpy only',
                                 'copy_installation':'not_verified_on_real_game'},
                'native_ui':{k:v for k,v in ui.items() if k in ('preferences_only','recipe_id','visual_review','persistence_review','forbidden')},
                'limitations':sorted(set(limitations)),'validation_level':'experimental_unverified',
                'ownership':'Only files explicitly listed below belong to this package; no player data included',
                'provenance':[{'job_id':o['job_id'],'job_identity':o['job_identity']} for o in outputs]}
    descriptor['package_id']=digest(descriptor)
    return descriptor
