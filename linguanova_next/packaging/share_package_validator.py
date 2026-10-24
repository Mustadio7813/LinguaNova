from pathlib import Path
import zipfile
import json
import hashlib
from ..util import safe_relative


def validate_zip(path):
    with zipfile.ZipFile(path) as archive:
        return _validate_reader(archive)


def validate_archive(path):
    from .rar_archive import open_player_archive
    with open_player_archive(path) as archive:
        return _validate_reader(archive)


def _validate_reader(archive):
    errors=[]
    if archive:
        names=archive.namelist()
        if len(names)!=len(set(n.casefold() for n in names)):
            errors.append('Duplicate or case-colliding ZIP member')
        for name in names:
            try:safe_relative(name)
            except ValueError:errors.append('Unsafe archive path: '+name)
            if not (name.startswith('game/') or name in ('manifest.json','LEEME_INSTALACION.txt')):
                errors.append('Unexpected copy root: '+name)
            if name.startswith('game/game/'):
                errors.append('Nested game/game root')
        if 'manifest.json' not in names or 'LEEME_INSTALACION.txt' not in names:
            errors.append('Missing installation metadata')
            return {'valid':False,'errors':errors}
        manifest=json.loads(archive.read('manifest.json'))
        expected={x['path']:x for x in manifest['files']}
        if set(names)!=set(expected)|{'manifest.json','LEEME_INSTALACION.txt'}:
            errors.append('Manifest and actual player files differ')
        for name,item in expected.items():
            if name not in names:errors.append('Missing dependency: '+name);continue
            data=archive.read(name)
            if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
                errors.append('Hash mismatch: '+name)
        return {'valid':not errors,'errors':errors,'package_id':manifest['package_id'],
                'validation_level':manifest['validation_level'],'files':len(expected)}
