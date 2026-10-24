"""Real base providers by composition; Gemini gets a new profile-aware client."""
import asyncio
import json
import os
import uuid
from ..contracts.entry import Candidate
from ..linguistic.prompt_policy import build_prompt
from ..util import load_json
from ..packaging.frozen_resources import resource_root
from .config_view import ConfigView


class ProviderError(RuntimeError):
    pass


class ProviderAdapter:
    def __init__(self, job, provider_id=None):
        self.job = job
        self.provider_id = provider_id or job.provider_id
        self.options = json.loads(job.options_json)
        self.model = self.options.get('provider_models',{}).get(self.provider_id,job.model if self.provider_id==job.provider_id else '')
        self.model = self.model or {'openai':'gpt-4o-mini','deepseek':'deepseek-chat','gemini':'gemini-2.5-flash'}.get(self.provider_id,self.provider_id+'-base-1.1.2')
        self.client = None
        self.status_callback = None
        self.capabilities = load_json(resource_root()/'linguanova_next/data/provider_capabilities.json')
        self.capability()

    def set_status_callback(self,callback):
        self.status_callback=callback
        if self.client and self.provider_id!='gemini':self.client.status_callback=callback

    def capability(self):
        item = self.capabilities['providers'].get(self.provider_id)
        if not item or self.job.target_language_id not in item['targets']:
            raise ProviderError('Unsupported provider/destination; no implicit English fallback')
        if item.get('test_only') and not self.options.get('allow_test_provider'):
            raise ProviderError('Pseudo is exclusively for explicitly identified tests')
        return item

    async def _load(self):
        if self.client:
            return
        from src.core.translators.base import TranslationEngine
        self.enum = TranslationEngine.OPENAI if self.provider_id=='deepseek' else TranslationEngine(self.provider_id)
        if self.provider_id == 'gemini':
            from google import genai
            key = os.environ.get('LINGUANOVA_NEXT_GEMINI_KEY')
            if not key:
                raise ProviderError('Missing LINGUANOVA_NEXT_GEMINI_KEY')
            self.client = genai.Client(api_key=key)
            return
        from src.core.translators import GoogleTranslator, BingTranslator, DeepLTranslator, LibreTranslateTranslator, PseudoTranslator
        config = ConfigView(self.job)
        classes = {'google':GoogleTranslator,'bing':BingTranslator,'deepl':DeepLTranslator,'pseudo':PseudoTranslator}
        kwargs = {'config_manager':config}
        key = os.environ.get('LINGUANOVA_NEXT_'+self.provider_id.upper()+'_KEY','')
        if self.provider_id == 'libretranslate':
            endpoint = self.options.get('endpoint')
            if not endpoint:
                raise ProviderError('LibreTranslate requires an explicitly configured endpoint')
            self.client = LibreTranslateTranslator(base_url=endpoint,api_key=key,config_manager=config)
        elif self.provider_id in ('openai','deepseek'):
            if not key:
                raise ProviderError('Missing LINGUANOVA_NEXT_'+self.provider_id.upper()+'_KEY')
            from src.core.ai_translator import OpenAITranslator
            # DeepSeek uses its existing OpenAI-compatible API, with the same
            # mandatory profile prompt in this new immutable configuration.
            endpoint = self.options.get('endpoint') or ('https://api.deepseek.com' if self.provider_id=='deepseek' else None)
            model = self.model or ('deepseek-chat' if self.provider_id=='deepseek' else 'gpt-4o-mini')
            self.client = OpenAITranslator(api_key=key, model=model, base_url=endpoint, **kwargs)
        else:
            if self.provider_id=='deepl' and not key:
                raise ProviderError('Missing LINGUANOVA_NEXT_DEEPL_KEY')
            if key:
                kwargs['api_key']=key
            self.client = classes[self.provider_id](**kwargs)
            # Supported public setting. No fallback client is attached: a
            # different provider must pass through this adapter and validation.
            self.client.set_proxy_enabled(False)
        if self.status_callback:self.client.status_callback=self.status_callback

    async def translate(self, occurrence, source_language=None, attempt=1):
        await self._load()
        request_id = uuid.uuid4().hex
        source = source_language or self.job.source_mode
        from ..dictionary.term_protection import protect_terms,restore_terms
        protected_terms,term_map=protect_terms(occurrence.original,json.loads(self.job.glossary_json))
        if self.provider_id == 'gemini':
            from google.genai import types
            from src.core.syntax_guard import protect_renpy_syntax, restore_renpy_syntax
            protected, placeholders = protect_renpy_syntax(protected_terms)
            response = await self.client.aio.models.generate_content(
                model=self.model or 'gemini-2.5-flash',
                contents='Source language: '+source+'\n'+protected,
                config=types.GenerateContentConfig(system_instruction=build_prompt(self.job), temperature=0.2))
            text = restore_renpy_syntax(response.text or '', placeholders)
        else:
            from src.core.translators.base import TranslationRequest
            # Provider APIs get base codes. Region identity remains in metadata
            # and mandatory profile instructions; MT requires editorial review.
            metadata = {'job_identity':self.job.identity, 'target_locale':self.job.target_locale,
                        'profile_id':self.job.profile_id, 'profile_version':self.job.profile_version,
                        'context':occurrence.context, 'original_text':protected_terms,
                        'glossary':json.loads(self.job.glossary_json), 'request_id':request_id}
            req = TranslationRequest(protected_terms, source, self.job.target_language_id, self.enum, metadata)
            result = await self.client.translate_single(req)
            if not result.success:
                from ..diagnostics import Diagnostics
                detail=Diagnostics.redact(result.error or 'sin detalle del proveedor')[:350]
                raise ProviderError('Provider returned failure; engine='+self.provider_id+' · '+detail)
            if result.target_lang != req.target_lang:
                raise ProviderError('Provider response target mismatch')
            text = result.translated_text
        text=restore_terms(text,term_map)
        return Candidate(occurrence.occurrence_id,text,self.provider_id,self.model,source,request_id,self.job.identity,attempt)

    async def close(self):
        if self.client:
            if self.provider_id=='gemini':
                await self.client.aio.aclose()
                self.client.close()
            else:
                await self.client.close()
            self.client=None
