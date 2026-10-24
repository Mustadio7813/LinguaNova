from dataclasses import dataclass
from pathlib import Path
from ..util import load_json
from ..packaging.frozen_resources import resource_root


@dataclass(frozen=True)
class Destination:
    language_id: str
    name: str
    locale: str
    renpy_id: str
    profile_id: str = ''
    profile_version: str = '1'
    direction: str = 'ltr'


class LanguageRegistry:
    def __init__(self, catalog=None):
        self.catalog = catalog or load_json(resource_root()/'linguanova_next/data/languages.json')
        if self.catalog['schema_version'] != 1:
            raise ValueError('Unsupported language catalog')
        self.version = self.catalog['catalog_version']

    def list_destinations(self):
        return [x.copy() for x in self.catalog['languages'] if x.get('enabled', False)]

    def list_profiles(self):
        return [x.copy() for x in self.catalog['languages'][0]['profiles']]

    def resolve_profile(self, language, profile=None):
        item = next((x for x in self.list_destinations() if x['id']==language), None)
        if not item:
            raise ValueError('Destination is not enabled: '+language)
        if language=='es':
            profile = profile or 'latam_neutro_sin_modismos'
            p = next((p for p in item['profiles'] if p['id']==profile), None)
            if not p:
                raise ValueError('Unknown Spanish profile')
            return Destination(language, p['name'], p['locale'], p['renpy_id'], p['id'], p['version'])
        if profile:
            raise ValueError('Spanish profiles only apply to Spanish')
        return Destination(language,item['name'],item['locale'],item['renpy_id'])

    def legacy_identity(self, alias):
        return {'alias':alias, 'profile_id':None, 'variant':'unknown', 'provenance':'legacy'}
