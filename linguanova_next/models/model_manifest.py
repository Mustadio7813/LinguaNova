from pathlib import Path
from ..util import load_json, file_hash, safe_join


def verify_model(directory, manifest):
    if manifest.get('schema_version')!=1 or manifest.get('provider')!='diffusers-sdxl-inpaint':
        raise ValueError('Incompatible model schema/provider')
    root=Path(directory)
    for item in manifest['files']:
        path=safe_join(root,item['path'])
        if not path.is_file() or path.stat().st_size!=item['size'] or file_hash(path)!=item['sha256']:
            raise ValueError('Model file missing or hash mismatch: '+item['path'])
    return {'valid':True,'revision':manifest['revision'],'bytes':sum(x['size'] for x in manifest['files'])}
