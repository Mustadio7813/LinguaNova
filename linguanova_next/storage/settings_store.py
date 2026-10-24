from pathlib import Path
from ..util import load_json, atomic_json


class SettingsStore:
    DEFAULT = {'schema_version': 1, 'target': 'es', 'profile': 'latam_neutro_sin_modismos',
               'provider': 'google', 'source': 'auto'}

    def __init__(self, root):
        self.path = Path(root)/'settings_next.json'

    def load(self):
        data = load_json(self.path, self.DEFAULT.copy())
        if data.get('schema_version') != 1:
            raise ValueError('Unsupported settings schema; keep original file for recovery')
        return self.DEFAULT | data

    def save(self, data):
        # Secrets are deliberately supplied by environment, never persisted.
        allowed = set(self.DEFAULT) | {'project', 'model', 'text_enabled', 'endpoint', 'output_mode'}
        atomic_json(self.path, self.DEFAULT | {k:v for k,v in data.items() if k in allowed})

    def import_legacy_copy(self, legacy_path):
        old = load_json(legacy_path, {})
        atomic_json(self.path.with_name('legacy_import_copy.json'), old)
        settings = old.get('translation_settings', {})
        self.save({'source': settings.get('source_language', 'auto'), 'provider': settings.get('engine', 'google')})
