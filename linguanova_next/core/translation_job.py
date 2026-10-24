"""New end-to-end job authority. Nothing mutates a protected source file."""
import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import threading
from ..contracts.entry import Occurrence, Candidate
from ..contracts.result import EntryResult, ValidationResult
from ..contracts.events import JobEvent
from ..adapters.extraction_adapter import ExtractionAdapter, game_directory, source_manifest
from ..adapters.provider_adapter import ProviderAdapter
from ..adapters.runtime_export_adapter import export_runtime
from ..adapters.font_adapter import runtime_font_export
from ..adapters.language_menu_adapter import protect_resources
from ..storage.result_store import ResultStore
from ..storage.cache_store import CacheStore
from ..linguistic.profile_validator import validate
from ..packaging.staging import Staging
from ..packaging.native_ui_export import build_native_ui
from ..packaging.package_manifest import output_manifest
from ..packaging.package_validator import validate_output
from ..util import atomic_json, atomic_bytes, load_json, digest, file_hash, jsonable, safe_join
from .job_lock import JobLock
from .work_queue import WorkQueue, CancelledJob
from .coverage_audit import audit
from .residual_review import unresolved


class TranslationJobRunner:
    def __init__(self, services, job, callback=None, cancelled=None, provider_factory=ProviderAdapter):
        self.services,self.job=services,job
        self.store=ResultStore(services.data,job)
        self.options=json.loads(job.options_json)
        self.queue=WorkQueue(self.options.get('concurrency',2),cancelled or threading.Event())
        self.callback=callback or (lambda event:None)
        self.providers={}
        self.provider_factory=provider_factory
        self.cache=CacheStore(services.data)
        event_file=self.store.directory/'events.jsonl'
        self.sequence=sum(1 for _ in event_file.open()) if event_file.exists() else 0
        self.reviews=load_json(self.store.directory/'reviews.json',{})
        self.dictionary=services.job_dictionary(job)
        self.dictionary_scopes={oid:entity for entity in self.dictionary['analysis']['entities']
                                if entity['kind']=='character' for oid in entity['occurrence_ids']}

    def event(self,kind,message,**ids):
        self.sequence+=1
        event=JobEvent(self.job.job_id,self.sequence,kind,message,**ids)
        self.store.append('events.jsonl',event)
        self.callback(event)

    async def translate_entry(self,entry,source_language=None):
        namespace='mod' if self.job.output_mode=='mod' else 'text'
        names=[self.job.provider_id]+self.options.get('fallback_providers',[])
        final_candidate=None
        final_verdict=ValidationResult(False,('provider_failure',))
        for name in names:
            self.queue.check()
            if name not in self.providers:
                self.providers[name]=self.provider_factory(self.job,name)
                if hasattr(self.providers[name],'set_status_callback'):
                    def status(level,message,engine=name):
                        safe=self.services.diagnostics.redact(message)
                        if level.lower() in ('warning','error'):
                            safe=self.services.diagnostics.record('Proveedor · '+engine,RuntimeError(safe),
                                project=self.job.project_path,job_id=self.job.job_id,severity=level.lower())
                        self.event('ProviderStatus',safe)
                    self.providers[name].set_status_callback(status)
            provider=self.providers[name]
            key=self.cache.key(self.job,entry,name,getattr(provider,'model',self.job.model),namespace)
            cached=self.cache.get(namespace,key)
            if cached:
                verdict=validate(self.job,entry.original,cached['text'],entry.context)
                if verdict.accepted:
                    return Candidate(entry.occurrence_id,cached['text'],name,cached.get('model',''),source_language or self.job.source_mode,
                                     'cache:'+key,self.job.identity),verdict
            for attempt in range(1,int(self.options.get('attempts',2))+1):
                try:
                    candidate=await self.queue.call(provider.translate,entry,source_language,attempt)
                    self.queue.check()
                    if candidate.job_identity!=self.job.identity or candidate.occurrence_id!=entry.occurrence_id:
                        raise ValueError('Provider correlation mismatch')
                    verdict=validate(self.job,entry.original,candidate.text,entry.context)
                    final_candidate,final_verdict=candidate,verdict
                    self.event('TranslationCandidate',entry.original[:100],request_id=candidate.request_id,occurrence_id=entry.occurrence_id)
                    if verdict.accepted:
                        self.cache.put(namespace,key,{'text':candidate.text,'provider':candidate.provider,'model':candidate.model},accepted=True)
                        return candidate,verdict
                    self.event('ValidationRejected',', '.join(verdict.reasons),request_id=candidate.request_id,occurrence_id=entry.occurrence_id)
                except CancelledJob:
                    raise
                except Exception as exc:
                    final_verdict=ValidationResult(False,('provider_failure:'+type(exc).__name__,))
                    message=self.services.diagnostics.record('Traducción · '+name,exc,project=self.job.project_path,
                                            resource=entry.path,job_id=self.job.job_id)
                    self.event('ProviderFailure',message,occurrence_id=entry.occurrence_id)
        return final_candidate,final_verdict

    def dictionary_result(self,entry):
        entity=self.dictionary_scopes.get(entry.occurrence_id)
        if not entity:return None
        choice=self.dictionary['choices'].get(entity['id'])
        text=choice['text'] if choice else entry.original
        preserve=not choice or choice['decision']=='preserve'
        verdict=validate(self.job,entry.original,text,entry.context,allow_preserve=preserve,proper_name=preserve)
        return EntryResult(entry.occurrence_id,self.job.identity,
            ('preserved_approved' if preserve else 'accepted') if verdict.accepted else 'rejected_validation',
            candidate=text,reasons=verdict.reasons,flags=verdict.warnings,provider='project_dictionary',
            provenance='character_declaration_rule' if not choice else 'target_dictionary_decision')

    def reviewed_result(self,entry):
        action=self.reviews.get(entry.occurrence_id)
        if not action:return None
        if action.get('job_identity')!=self.job.identity or action.get('source_hash')!=entry.source_hash:
            raise ValueError('Review belongs to another source/job revision')
        text=entry.original if action['decision']=='preserve' else action.get('text','')
        verdict=validate(self.job,entry.original,text,entry.context,allow_preserve=action['decision']=='preserve')
        if not verdict.accepted:
            return EntryResult(entry.occurrence_id,self.job.identity,'rejected_validation',candidate=text,reasons=verdict.reasons,
                               flags=verdict.warnings,provider='human_review',provenance='review_action')
        return EntryResult(entry.occurrence_id,self.job.identity,'preserved_approved' if action['decision']=='preserve' else 'accepted',
                           candidate=text,flags=verdict.warnings,provider='human_review',provenance='review_action',
                           linguistic_review='approved' if action.get('editorial_approved') else 'unverified')

    async def text_results(self,entries):
        previous=self.store.results();results={};iterator=iter(entries)
        async def worker():
            for entry in iterator:
                self.queue.check()
                review=self.reviewed_result(entry)
                if review:
                    result=review
                elif self.dictionary_result(entry) is not None:
                    result=self.dictionary_result(entry)
                elif not entry.publishable:
                    result=EntryResult(entry.occurrence_id,self.job.identity,'extraction_omission',reasons=('review_candidate_not_automatically_translatable',))
                elif entry.occurrence_id in previous and previous[entry.occurrence_id].status in ('accepted','preserved_approved'):
                    result=replace(previous[entry.occurrence_id],written='',output_path='')
                    if not validate(self.job,entry.original,result.candidate,entry.context,allow_preserve=result.status=='preserved_approved',
                                    proper_name=result.status=='preserved_approved' and entry.occurrence_id in self.dictionary_scopes and result.provider=='project_dictionary').accepted:
                        raise ValueError('Resumed result no longer passes its validation rules')
                else:
                    candidate,verdict=await self.translate_entry(entry)
                    reasons=verdict.reasons
                    status='accepted' if verdict.accepted else 'source_copy' if 'source_copy_unresolved' in reasons else 'provider_failure' if any(r.startswith('provider_failure') for r in reasons) else 'rejected_validation'
                    result=EntryResult(entry.occurrence_id,self.job.identity,status,candidate.text if candidate else '',reasons=reasons,
                                       flags=verdict.warnings,provider=candidate.provider if candidate else '',model=candidate.model if candidate else '',
                                       request_id=candidate.request_id if candidate else '',linguistic_review=verdict.linguistic_review)
                self.store.put_result(result);results[entry.occurrence_id]=result
                self.event('EntryApproved' if result.status in ('accepted','preserved_approved') else 'EntryPending',result.status,occurrence_id=entry.occurrence_id)
        await asyncio.gather(*(worker() for _ in range(int(self.options.get('concurrency',2)))))
        return results

    async def images(self,game,stage):
        # This application translates script text only.
        return {}, []

    async def run(self):
        job=self.job;self.store.create()
        game=game_directory(job.project_path)
        with JobLock(game):
            self.services.validate_resume(job)
            self.event('JobCreated','Job identity fixed: '+job.target_locale)
            self.store.state(status='running')
            try:
                entries=[Occurrence(**row) for row in self.dictionary['analysis']['inventory']] if job.text_enabled else []
                diagnostics=self.dictionary['analysis']['diagnostics']
                self.event('DictionaryReady','Análisis previo verificado: '+str(len(self.dictionary['analysis']['entities']))+' términos/nombres')
                # Explicit review can admit an omitted occurrence or classify a
                # preservation without rewriting the baseline parser's filters.
                entries=[replace(o,publishable=(self.reviews[o.occurrence_id]['decision']!='preserve'))
                         if o.occurrence_id in self.reviews else o for o in entries]
                atomic_json(self.store.directory/'inventory.json',entries)
                atomic_json(self.store.directory/'extraction_diagnostics.json',diagnostics)
                self.event('ExtractionCompleted',str(len(entries))+' textual occurrences')
                results=await self.text_results(entries)
                staging=Staging(self.store.directory/'published')
                with staging as stage:
                    stage_game=stage/'game';stage_game.mkdir()
                    results,written,export_warnings=export_runtime(game,stage,job,entries,results)
                    image_results,image_limits={},[]
                    from ..packaging.image_codecs_template import write_image_codecs
                    write_image_codecs(stage_game)
                    self.queue.check()
                    destination=asdict(self.services.registry.resolve_profile(job.target_language_id,job.profile_id or None))
                    destination['renpy_id']=job.renpy_id
                    ui=build_native_ui(game,stage_game,[destination],self.options.get('ui_recipe'))
                    protect_resources(stage_game)
                    fonts=runtime_font_export(game,stage,job,list(written.values()),self.options,self.services.diagnostics)
                    for warning in fonts.get('warnings',[]):self.event('FontWarning',warning)
                    report,results=audit(job,entries,results,written)
                    limitations=['No integration test against an attached real game',
                                 'Editorial review is separate from automatic translation validation']+export_warnings
                    if diagnostics:limitations.append('Extraction diagnostics require creator review')
                    if not ui.get('preferences_only'):limitations.append('Native Preferences integration blocked: '+ui.get('reason','unknown game'))
                    if any(r.status not in ('accepted','preserved_approved') for r in results.values()):limitations.append('Unresolved textual entries remain')
                    if any(r.linguistic_review!='approved' for r in results.values()):limitations.append('Some accepted entries lack editorial approval')
                    if fonts['status']=='font_coverage_unverified':limitations.append('Runtime font coverage is not verified')
                    # Creator details (absolute paths, masks, diagnostics) do not
                    # enter the player manifest assembled by SharePackageBuilder.
                    manifest=output_manifest(stage,job,destination,limitations,ui,fonts,image_results)
                    verdict=validate_output(stage,manifest)
                    if not verdict['valid']:raise ValueError('Player output validation failed: '+str(verdict['errors']))
                    self.queue.check()
                    atomic_json(stage/'output_manifest.json',manifest)
                    atomic_json(stage/'coverage_report.json',report)
                    staging.publish()
                for result in results.values():self.store.put_result(result)
                atomic_json(self.store.directory/'output_manifest.json',manifest)
                atomic_json(self.store.directory/'coverage_report.json',report)
                pending=list(unresolved(entries,results))
                atomic_bytes(self.store.directory/'unresolved_entries.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in pending).encode())
                atomic_bytes(self.store.directory/'preserved_entries.jsonl',''.join(json.dumps(jsonable(r),ensure_ascii=False)+'\n' for r in results.values() if r.status=='preserved_approved').encode())
                self.store.state(status='completed_experimental',pending=len(pending),limitations=limitations)
                self.event('JobCompleted','Output generated; '+str(len(pending))+' textual entries pending')
                return report
            except CancelledJob:
                self.store.state(status='paused',cause='cancelled');self.event('JobPaused','Cancelled; previous published output preserved')
                return None
            except Exception as exc:
                message=self.services.diagnostics.record('Trabajo · ejecución',exc,project=job.project_path,job_id=job.job_id)
                self.store.state(status='failed',cause=type(exc).__name__);self.event('JobFailed',message)
                raise
            finally:
                for provider in self.providers.values():
                    try:await provider.close()
                    except Exception as exc:
                        message=self.services.diagnostics.record('Proveedor · cierre',exc,project=job.project_path,job_id=job.job_id,severity='warning')
                        self.event('ProviderCloseWarning',message)
