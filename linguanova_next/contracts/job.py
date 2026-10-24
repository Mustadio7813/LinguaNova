"""Immutable authority for a textual translation job."""
from dataclasses import dataclass, asdict
from ..util import digest


@dataclass(frozen=True)
class TranslationJob:
    schema_version: int
    job_id: str
    project_id: str
    base_manifest_hash: str
    target_language_id: str
    target_locale: str
    renpy_id: str
    profile_id: str
    profile_version: str
    catalog_version: str
    glossary_hash: str
    rules_hash: str
    sources_hash: str
    project_path: str
    source_mode: str = 'auto'
    provider_id: str = 'google'
    model: str = ''
    text_enabled: bool = True
    output_mode: str = 'native'
    revision: int = 1
    options_json: str = '{}'
    glossary_json: str = '{}'

    def __post_init__(self):
        if self.schema_version != 1 or not self.job_id or not self.renpy_id.isidentifier():
            raise ValueError('Invalid job identity')
        if self.output_mode not in ('native', 'mod'):
            raise ValueError('Unknown output mode')
        if not self.text_enabled:
            raise ValueError('Text translation must be enabled')

    @property
    def identity(self):
        return digest(asdict(self))

    @property
    def target_identity(self):
        return (self.target_language_id, self.target_locale, self.renpy_id, self.profile_id, self.profile_version)
