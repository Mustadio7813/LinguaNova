"""Explicit, hash-checked offline import/download with atomic activation."""
from pathlib import Path
import shutil
import tempfile
import urllib.request
from ..util import atomic_json, load_json, safe_join, file_hash
from .model_manifest import verify_model


class ModelInstallation:
    def __init__(self, root, manifest):
        self.root=Path(root)
        self.manifest=manifest
        self.root.mkdir(parents=True,exist_ok=True)

    def import_directory(self, source):
        verify_model(source,self.manifest)
        destination=self.root/self.manifest['revision']
        if destination.exists():
            verify_model(destination,self.manifest)
            return destination
        stage=Path(tempfile.mkdtemp(prefix='import-',dir=self.root))
        try:
            for item in self.manifest['files']:
                target=safe_join(stage,item['path']);target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(safe_join(source,item['path']),target)
            verify_model(stage,self.manifest)
            atomic_json(stage/'linguanova_model.json',self.manifest)
            stage.rename(destination)
            return destination
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def download(self, progress=None, cancelled=None):
        stage=Path(tempfile.mkdtemp(prefix='download-',dir=self.root))
        done=0
        try:
            for item in self.manifest['files']:
                target=safe_join(stage,item['path']);target.parent.mkdir(parents=True,exist_ok=True)
                url=f"https://huggingface.co/{self.manifest['repository']}/resolve/{self.manifest['revision']}/{item['path']}"
                with urllib.request.urlopen(url,timeout=60) as response,target.open('wb') as stream:
                    while chunk:=response.read(1024*1024):
                        if cancelled and cancelled.is_set():
                            raise RuntimeError('Model installation cancelled')
                        stream.write(chunk);done+=len(chunk)
                        if progress: progress(done,self.manifest['total_bytes'])
                if target.stat().st_size!=item['size'] or file_hash(target)!=item['sha256']:
                    raise ValueError('Downloaded model hash mismatch')
            return self.import_directory(stage)
        finally:
            shutil.rmtree(stage,ignore_errors=True)

    def activate(self, revision):
        if revision!=self.manifest['revision']:
            raise ValueError('Model version is not compatible with this extension')
        verify_model(self.root/revision,self.manifest)
        previous=load_json(self.root/'active.json',{})
        atomic_json(self.root/'active.json',{'revision':revision,'previous':previous.get('revision')})

    def rollback(self):
        current=load_json(self.root/'active.json',{})
        previous=current.get('previous')
        if not previous:
            raise ValueError('No previous activation to recover')
        self.activate(previous)
