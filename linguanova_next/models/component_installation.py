"""Explicit offline component import for optional inference runtimes."""
from pathlib import Path
import shutil
import tempfile
from ..util import load_json, file_hash, digest, safe_join, atomic_json
from ..packaging.frozen_resources import data_root


def verify_component(source,manifest):
    if manifest.get('schema_version')!=1 or manifest.get('type') not in ('tesseract','inference'):
        raise ValueError('Unsupported creator component')
    if manifest.get('type')=='inference' and manifest.get('protocol_version')!=1:
        raise ValueError('Incompatible inference worker protocol')
    files={f['path']:f for f in manifest['files']}
    if manifest['executable'] not in files or not manifest.get('license_notices'):
        raise ValueError('Component needs an owned executable and license notices')
    for relative,item in files.items():
        path=safe_join(source,relative)
        if not path.is_file() or path.is_symlink() or path.stat().st_size!=item['size'] or file_hash(path)!=item['sha256']:
            raise ValueError('Component file/hash mismatch: '+relative)
    for notice in manifest['license_notices']:
        if notice not in files:raise ValueError('Missing component license notice')
    return True


class ComponentInstallation:
    def __init__(self,root=None):
        self.root=Path(root or data_root()/'components')

    def import_directory(self,source):
        source=Path(source);manifest=load_json(source/'component_manifest.json')
        if not manifest:raise ValueError('component_manifest.json not found')
        verify_component(source,manifest)
        kind=manifest['type'];revision=digest(manifest)
        parent=self.root/kind;parent.mkdir(parents=True,exist_ok=True)
        target=parent/revision
        if not target.exists():
            stage=Path(tempfile.mkdtemp(prefix='import-',dir=parent))
            try:
                for f in manifest['files']:
                    dest=safe_join(stage,f['path']);dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(safe_join(source,f['path']),dest)
                atomic_json(stage/'component_manifest.json',manifest)
                verify_component(stage,manifest);stage.rename(target)
            finally:
                if stage.exists():shutil.rmtree(stage)
        old=load_json(parent/'active.json',{})
        atomic_json(parent/'active.json',{'revision':revision,'previous':old.get('revision')})
        return {'type':kind,'version':manifest.get('version'),'revision':revision}

    def resolve(self,kind):
        if kind not in ('tesseract','inference'):raise ValueError('Unknown component')
        state=load_json(self.root/kind/'active.json',{})
        revision=state.get('revision','')
        if not revision or len(revision)!=64:raise RuntimeError('Creator component not installed: '+kind)
        folder=self.root/kind/revision
        manifest=load_json(folder/'component_manifest.json')
        if digest(manifest)!=revision:raise ValueError('Component activation changed')
        verify_component(folder,manifest)
        executable=safe_join(folder,manifest['executable'])
        return manifest|{'executable':str(executable),'sha256':file_hash(executable)}
