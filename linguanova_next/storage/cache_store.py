"""Exact content keys only; namespaces never cross into another profile."""
from pathlib import Path
import json
from ..util import digest, atomic_json, load_json

NAMESPACES = {'text', 'mod', 'composition'}


class CacheStore:
    def __init__(self, root):
        self.root = Path(root)/'cache_next'/'v2'

    def key(self, job, occurrence, provider, model='', namespace='text'):
        return digest({'target': job.target_identity, 'catalog': job.catalog_version,
                       'project':job.project_id,'dictionary':json.loads(job.options_json).get('dictionary',{}).get('snapshot_hash'),
                       'rules': job.rules_hash, 'glossary': job.glossary_hash,
                       'source': job.source_mode, 'source_hash': occurrence.source_hash,
                       'original': occurrence.original, 'context': occurrence.context,
                       'provider': provider, 'model': model, 'namespace': namespace})

    def path(self, namespace, key):
        if namespace not in NAMESPACES or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('Invalid cache identity')
        return self.root/namespace/(key+'.json')

    def get(self, namespace, key):
        envelope=load_json(self.path(namespace,key))
        if envelope is None:return None
        if not isinstance(envelope,dict) or envelope.get('namespace')!=namespace or envelope.get('key')!=key or digest(envelope.get('payload'))!=envelope.get('sha256'):
            raise ValueError('Cache integrity mismatch: '+str(self.path(namespace,key)))
        return envelope['payload']

    def put(self, namespace, key, value, accepted=False):
        if namespace in ('text', 'mod', 'composition') and not accepted:
            raise ValueError('Rejected candidates cannot enter accepted cache')
        atomic_json(self.path(namespace,key), {'schema_version':2,'namespace':namespace,'key':key,'sha256':digest(value),'payload':value})
