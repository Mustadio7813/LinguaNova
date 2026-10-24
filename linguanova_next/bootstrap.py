"""Service composition; importing this module never starts Qt or a model."""
from pathlib import Path
import json
import uuid
from .baseline import require_baseline
from .contracts.job import TranslationJob
from .core.language_registry import LanguageRegistry
from .adapters.extraction_adapter import game_directory, source_manifest
from .storage.settings_store import SettingsStore
from .storage.result_store import ResultStore
from .packaging.frozen_resources import resource_root, data_root
from .util import atomic_json, load_json, digest, file_hash, canonical, jsonable


def rules_hash(root):
    root=Path(root)
    folders=('adapters','core','linguistic','image','bridge','contracts','models','packaging','dictionary','storage')
    paths=sorted({p.relative_to(root).as_posix() for folder in folders for p in (root/'linguanova_next'/folder).glob('*.py')})
    paths+=['linguanova_next/bootstrap.py','linguanova_next/util.py','linguanova_next/diagnostics.py','linguanova_next/version.py','linguanova_next/data/profiles/es_419.json',
            'linguanova_next/data/profiles/es_ES.json','linguanova_next/data/provider_capabilities.json']
    return digest({p:file_hash(root/p) for p in paths})



class Services:
    def __init__(self,root=None,data=None):
        self.root=Path(root or resource_root())
        self.data=Path(data or data_root()).resolve()
        self.base_hash=require_baseline(self.root)
        self.registry=LanguageRegistry()
        self.settings=SettingsStore(self.data)
        from .diagnostics import Diagnostics
        from .dictionary.service import DictionaryService
        self.diagnostics=Diagnostics(self.data)
        self.dictionary=DictionaryService(self.data,self.diagnostics)

    def create_job(self,project,target='es',profile=None,provider='google',source='auto',model='',
                   text_enabled=True,output_mode='native',
                   options=None,glossary=None,*,cancelled=None,progress=None):
        game=game_directory(project)
        options=json.loads(json.dumps(options or {}));glossary=dict(glossary or {})
        if 'dictionary' in options:raise ValueError('Dictionary identity is created by the preflight only')
        if not text_enabled:raise ValueError('Activa la traducción de texto')
        if not 1<=int(options.get('concurrency',2))<=8 or not 1<=int(options.get('attempts',2))<=3:
            raise ValueError('Concurrency must be 1..8 and attempts 1..3')
        forbidden={'api_key','key','password','token','secret'}
        def check(value):
            if isinstance(value,dict):
                if any(str(k).lower() in forbidden for k in value):raise ValueError('Supply credentials through environment variables only')
                for v in value.values():check(v)
            elif isinstance(value,list):
                for v in value:check(v)
        check(options)
        if not all(isinstance(k,str) and isinstance(v,str) and k.strip() and v.strip() for k,v in glossary.items()):raise ValueError('Glossary must map nonempty source strings to required strings')
        dest=self.registry.resolve_profile(target,profile)
        sources=source_manifest(game)
        prepared=self.dictionary.prepare(game,dest,output_mode,cancelled,progress)
        snapshot=prepared['snapshot']
        for key,value in self.dictionary.glossary(snapshot).items():
            if key in glossary and glossary[key]!=value:raise ValueError('Conflicting glossary decision: '+key)
            glossary[key]=value
        if sources!=source_manifest(game):raise ValueError('El juego cambió durante la preparación; crea el trabajo otra vez')
        options['dictionary']={'snapshot_hash':digest(snapshot),'statistics':{k:v for k,v in prepared.items() if k!='snapshot'}}
        snapshot_hash=digest(sources)
        job=TranslationJob(1,uuid.uuid4().hex,snapshot['project_id'],self.base_hash,dest.language_id,dest.locale,dest.renpy_id,
                           dest.profile_id,dest.profile_version,self.registry.version,digest(glossary),rules_hash(self.root),
                           snapshot_hash,str(game.parent),source,provider,model,bool(text_enabled),
                           output_mode,1,canonical(options),canonical(glossary))
        from .adapters.provider_adapter import ProviderAdapter
        ProviderAdapter(job).capability()
        from .dictionary.analysis import check_cancelled
        check_cancelled(cancelled)
        store=ResultStore(self.data,job);store.create()
        atomic_json(store.directory/'source_manifest.json',sources)
        atomic_json(store.directory/'dictionary_snapshot.json',snapshot)
        store.state(status='created')
        self.settings.save({'target':target,'profile':dest.profile_id,'provider':provider,'source':source,'project':str(game.parent),
                            'model':model,'text_enabled':text_enabled,'output_mode':output_mode})
        return job

    def job_dictionary(self,job):
        from .dictionary.service import project_identity
        path=self.data/'jobs'/job.job_id/'dictionary_snapshot.json'
        if not path.is_file():raise ValueError('Falta el Diccionario congelado del trabajo: '+str(path))
        snapshot=load_json(path)
        identity=json.loads(job.options_json).get('dictionary',{})
        dest=self.registry.resolve_profile(job.target_language_id,job.profile_id or None)
        from dataclasses import asdict
        if digest(snapshot)!=identity.get('snapshot_hash') or snapshot['project_id']!=project_identity(game_directory(job.project_path))[0] or snapshot['target']!=asdict(dest):
            raise ValueError('El Diccionario del trabajo no coincide con su proyecto, destino o huella')
        return snapshot

    def load_job(self,job_id):
        if not job_id.isalnum():raise ValueError('Invalid job id')
        data=load_json(self.data/'jobs'/job_id/'job.json')
        if not data:raise ValueError('Job not found')
        for legacy in ('image_enabled','ocr_source','image_method'):
            data.pop(legacy,None)
        return TranslationJob(**data)

    def validate_resume(self,job):
        if require_baseline(self.root)!=job.base_manifest_hash or rules_hash(self.root)!=job.rules_hash:
            raise ValueError('Baseline or rules changed: create a new job')
        dest=self.registry.resolve_profile(job.target_language_id,job.profile_id or None)
        if job.target_identity!=(dest.language_id,dest.locale,dest.renpy_id,dest.profile_id,dest.profile_version) or self.registry.version!=job.catalog_version:
            raise ValueError('Catalog/profile changed: create a new job')
        if digest(json.loads(job.glossary_json))!=job.glossary_hash:
            raise ValueError('Glossary identity changed')
        self.job_dictionary(job)
        if digest(source_manifest(game_directory(job.project_path)))!=job.sources_hash:
            raise ValueError('Project sources/assets/installed translations changed: create a new job')
        return True

    def jobs(self):
        rows=[]
        for p in sorted((self.data/'jobs').glob('*/job.json'),key=lambda x:x.stat().st_mtime,reverse=True):
            job=load_json(p);state=load_json(p.parent/'state.json',{})
            rows.append({'job_id':job['job_id'],'target':job['target_locale'],'profile_id':job['profile_id'],
                         'project':job['project_path'],'state':state.get('status','unknown'),'has_output':(p.parent/'output_manifest.json').exists()})
        return rows

    def review_entry(self,job_id,occurrence_id,decision,text,reason,reviewer='Usuario',editorial_approved=False):
        if decision not in ('correct','preserve','approve'):raise ValueError('Unknown review decision')
        job=self.load_job(job_id);self.validate_resume(job)
        store=ResultStore(self.data,job)
        occurrence=next((o for o in load_json(store.directory/'inventory.json',[]) if o['occurrence_id']==occurrence_id),None)
        if not occurrence or not reason.strip() or not reviewer.strip():raise ValueError('Review needs an existing ID, reviewer and contextual reason')
        action={'job_identity':job.identity,'occurrence_id':occurrence_id,'source_hash':occurrence['source_hash'],
                'decision':decision,'text':text,'reason':reason,'reviewer':reviewer,'editorial_approved':bool(editorial_approved)}
        data=load_json(store.directory/'reviews.json',{});data[occurrence_id]=action
        atomic_json(store.directory/'reviews.json',data);store.append('review_actions.jsonl',action)
        return action

    def review_region(self,job_id,resource_id,region_id,decision):
        job=self.load_job(job_id);self.validate_resume(job);store=ResultStore(self.data,job)
        images=load_json(store.directory/'image_results.json',{})
        resource=images.get(resource_id)
        region=next((x for x in (resource or {}).get('regions',[]) if x['region']['region_id']==region_id),None)
        if not region:raise ValueError('Unknown image/region identity')
        if not decision.get('reviewer') or not decision.get('reason'):raise ValueError('Region review requires reviewer and reason')
        from .image.typography_profile import TypographyProfile
        profile=TypographyProfile(**decision['typography']);profile.validate()
        decision=dict(decision,job_identity=job.identity,image_hash=resource['image_hash'],approved=True)
        reviews=load_json(store.directory/'image_reviews.json',{})
        target=reviews.setdefault(resource_id,{'regions':{}})
        target['regions'][region_id]=decision
        if decision.get('large_mask_approved'):
            target['large_mask_approved']=True
        atomic_json(store.directory/'image_reviews.json',reviews);store.append('review_actions.jsonl',{'region_id':region_id,**decision})
        return decision

    def approve_image(self,job_id,resource_id,reason,reviewer='Usuario'):
        job=self.load_job(job_id);store=ResultStore(self.data,job)
        resource=load_json(store.directory/'image_results.json',{}).get(resource_id,{})
        path=Path(resource.get('candidate_path',''))
        if not reason.strip() or not path.is_file() or file_hash(path)!=resource.get('candidate_hash'):
            raise ValueError('No current composed image to approve')
        reviews=load_json(store.directory/'image_reviews.json',{})
        target=reviews.setdefault(resource_id,{'regions':{}})
        target.update(final_image_hash=file_hash(path),final_reviewer=reviewer,final_reason=reason)
        atomic_json(store.directory/'image_reviews.json',reviews)
        store.append('review_actions.jsonl',{'resource_id':resource_id,'final_image_hash':file_hash(path),'reason':reason,'reviewer':reviewer})
