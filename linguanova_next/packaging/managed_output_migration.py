from pathlib import Path
import shutil
from ..util import load_json, file_hash, safe_join, atomic_json


def migrate_owned_staging(stage,ownership,relative_paths,backup):
    """Remove only prior generated, unchanged files from an output copy."""
    stage=Path(stage);backup=Path(backup)
    moved=[]
    for rel in relative_paths:
        item=next((i for i in ownership.get('files',[]) if i['path']==rel),None)
        path=safe_join(stage,rel)
        if not item or item.get('owner')!='linguanova_next' or not path.is_file() or file_hash(path)!=item['sha256']:
            raise ValueError('Unknown or modified output cannot be migrated: '+rel)
        target=safe_join(backup,rel);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target);path.unlink();moved.append(rel)
    atomic_json(backup/'migration.json',{'files':moved,'recover':'copy these files back to the same relative paths'})
    return moved
