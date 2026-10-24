from dataclasses import asdict
from types import MappingProxyType
from ..linguistic.prompt_policy import build_prompt


class ReadView:
    def __init__(self, values):
        object.__setattr__(self,'_values',MappingProxyType(values))

    def __getattr__(self, key):
        try:
            return self._values[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key, value):
        raise TypeError('New-flow configuration is immutable')


class ConfigView(ReadView):
    def get_ui_text(self,key,default=''):
        return default

    def get_log_text(self,key,default=''):
        return default

    def __init__(self, job):
        # A fresh dataclass supplies compatible defaults, without loading or
        # writing the legacy ConfigManager or its settings file.
        from src.utils.config import TranslationSettings
        values = asdict(TranslationSettings())
        values.update(source_language=job.source_mode, target_language=job.target_language_id,
                      ai_custom_system_prompt=build_prompt(job), ai_retry_count=1,
                      max_concurrent_threads=2, enable_lingva_fallback=False,
                      enable_parallel_batch=False, use_multi_endpoint=False,
                      use_proxy=False)
        super().__init__({'translation_settings':ReadView(values)})
