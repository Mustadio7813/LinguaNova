from pathlib import Path
from ..util import load_json
from ..packaging.frozen_resources import resource_root
from .model_manifest import verify_model


def selected_manifest():
    return load_json(resource_root()/'linguanova_next/data/sdxl_inpainting_manifest.json')


class ModelRegistry:
    def __init__(self, root):
        self.root=Path(root)

    def active(self):
        state=load_json(self.root/'active.json',{})
        revision=state.get('revision')
        manifest=selected_manifest()
        if not revision:
            raise RuntimeError('No generative model activated; classical method remains available')
        if revision!=manifest['revision']:
            raise ValueError('Active model requires a different compatible worker')
        path=self.root/revision
        verify_model(path,manifest)
        return path,manifest
