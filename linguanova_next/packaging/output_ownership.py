"""Read-only ownership proofs that travel inside game/ on manual installation."""
from pathlib import Path
from ..util import load_json, safe_join, file_hash, digest, atomic_json


def known_owned_files(game):
    game=Path(game);owned={}
    for path in sorted((game/'linguanova_next_packages').glob('*.json')):
        data=load_json(path,{})
        if data.get('schema_version')!=1 or data.get('generator')!='linguanova_next':continue
        for item in data.get('files',[]):
            rel=item.get('path','')
            if not rel.startswith('game/'):continue
            target=safe_join(game.parent,rel)
            if item.get('owner')=='linguanova_next' and target.is_file() and file_hash(target)==item.get('sha256'):
                owned[rel]=item
    return owned


def prove_target_collisions(game,files):
    owned=known_owned_files(game);errors=[]
    for f in files:
        path=safe_join(Path(game).parent,f['path'])
        if path.exists() and file_hash(path)!=f['sha256'] and f['path'] not in owned:
            errors.append('Unknown or modified target file: '+f['path'])
    return errors


def write_ownership(stage,files,destinations):
    identity=digest({'files':files,'destinations':destinations})
    relative='game/linguanova_next_packages/'+identity+'.json'
    path=Path(stage)/relative
    atomic_json(path,{'schema_version':1,'generator':'linguanova_next','installation_id':identity,
                      'files':files,'destinations':destinations,
                      'note':'Metadata only; manual copy does not run validation or make backups'})
    return {'path':relative,'size':path.stat().st_size,'sha256':file_hash(path),'owner':'linguanova_next'}
