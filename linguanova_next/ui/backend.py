"""Qt adapter for the new services. Worker signals cross to the UI thread."""
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import threading
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, QUrl
from ..util import load_json, atomic_json, jsonable


class NextBackend(QObject):
    changed=pyqtSignal()
    activity=pyqtSignal(str)
    _finished=pyqtSignal(object)
    openClassicRequested=pyqtSignal()
    showWorkRequested=pyqtSignal()
    openShareRequested=pyqtSignal()
    openDictionaryRequested=pyqtSignal()

    def __init__(self,services,parent=None):
        super().__init__(parent)
        self.services=services;self.current_id='';self._busy=False;self._error='';self._summary={};self._activity=[]
        self.cancelled=threading.Event();self.thread=None
        self._dictionary={};self._prepared=None;self._selection=None
        self._finished.connect(self._on_finished)
        self.activity.connect(self._on_activity)

    @pyqtProperty(bool,notify=changed)
    def busy(self):return self._busy
    @pyqtProperty(str,notify=changed)
    def error(self):return self._error
    @pyqtProperty(str,notify=changed)
    def currentJob(self):return self.current_id
    @pyqtProperty(str,notify=changed)
    def summaryJson(self):return json.dumps(self._summary,ensure_ascii=False)
    @pyqtProperty(str,notify=changed)
    def jobsJson(self):return json.dumps(self.services.jobs(),ensure_ascii=False)
    @pyqtProperty(str,notify=changed)
    def dictionaryJson(self):return json.dumps(self._dictionary,ensure_ascii=False)
    @pyqtProperty(str,notify=changed)
    def diagnosticPath(self):return str(self.services.diagnostics.path)
    @pyqtProperty(str,notify=changed)
    def rarStatusJson(self):
        from ..packaging.rar_archive import rar_status
        return json.dumps(rar_status(),ensure_ascii=False)
    @pyqtProperty(str,notify=changed)
    def activityText(self):return '\n'.join(self._activity[-200:])
    @pyqtProperty(str,notify=changed)
    def reviewJson(self):
        if not self.current_id:return '[]'
        directory=self.services.data/'jobs'/self.current_id
        results={p.stem:load_json(p) for p in (directory/'results').glob('*.json')}
        rows=[]
        for entry in load_json(directory/'inventory.json',[]):
            r=results.get(entry['occurrence_id'],{})
            rows.append({**entry,'result':r,'status':r.get('status','missing'),'candidate':r.get('candidate',''),
                         'reasons':r.get('reasons',[]),'flags':r.get('flags',[])})
        return json.dumps(rows,ensure_ascii=False)
    @pyqtProperty(str,notify=changed)
    def settingsJson(self):return json.dumps(self.services.settings.load(),ensure_ascii=False)
    @pyqtProperty(str,notify=changed)
    def modelInfoJson(self):
        from ..models.model_registry import selected_manifest
        m=selected_manifest();active=load_json(self.services.data/'models/active.json',{})
        return json.dumps({'model':m['model_id'],'revision':m['revision'],'bytes':m['total_bytes'],
                           'requirements':'Optional worker; experimental CUDA >=8 GiB free / CPU ~32 GiB advisory',
                           'active':active.get('revision','none'),'inference':'not verified on this machine'},ensure_ascii=False)

    def _on_activity(self,text):
        self._activity.append(text);self.changed.emit()

    def _on_finished(self,result):
        self._busy=False;self._error=result.get('error','')
        if 'summary' in result:self._summary=result['summary'] or {}
        if 'created_job' in result:
            try:
                job=self.services.load_job(result['created_job'])
                self.current_id=job.job_id
                self._set_dictionary(job)
                self._summary={'job_id':job.job_id,'destination':job.target_locale,'profile':job.profile_id,
                    'provider':job.provider_id,'text':job.text_enabled,'dictionary':self._dictionary}
            except Exception as exc:self._fail('Trabajo · preparar vista',exc)
        if 'prepared_dictionary' in result:
            self._prepared=result['prepared_dictionary']
            self._dictionary=self.services.dictionary.view(self._prepared)
            self.current_id='';self._summary={'status':'dictionary_changed_create_new_job'}
        if 'batch_jobs' in result:
            rows=result['batch_jobs']
            self._summary={'batch':rows,'next_step':'Revisa el texto de cada trabajo y selecciona los destinos en Utilidades'}
            if rows:
                try:
                    job=self.services.load_job(rows[-1]['job_id']);self.current_id=job.job_id;self._set_dictionary(job)
                except Exception as exc:self._fail('Lote · cargar resultado',exc)
        self.changed.emit()

    def _run(self,fn,operation='Operación',result_key='summary'):
        if self._busy:raise RuntimeError('Wait for or cancel the active operation')
        self._busy=True;self._error='';self.cancelled=threading.Event();self.changed.emit()
        def work():
            try:self._finished.emit({result_key:fn()})
            except Exception as exc:
                from ..core.work_queue import CancelledJob
                if isinstance(exc,CancelledJob):
                    self._finished.emit({'summary':{'status':'cancelled','operation':operation}})
                else:
                    message=self.services.diagnostics.record(operation,exc,job_id=self.current_id)
                    self._finished.emit({'error':message})
        self.thread=threading.Thread(target=work,name='LinguaNovaNextWorker',daemon=True);self.thread.start()

    def _fail(self,operation,exc):
        self._error=self.services.diagnostics.record(operation,exc,job_id=self.current_id)
        self.changed.emit()

    def _set_dictionary(self,job):
        self._prepared={'snapshot':self.services.job_dictionary(job),
                        **json.loads(job.options_json)['dictionary']['statistics']}
        self._dictionary=self.services.dictionary.view(self._prepared)

    @pyqtSlot(str,str,str)
    def selectDictionaryContext(self,project,target,profile):
        selection=(self.localPath(project),target,profile)
        if selection!=self._selection and not self.busy:
            self._selection=selection;self._dictionary={};self._prepared=None
            self.current_id='';self._summary={};self.changed.emit()

    @pyqtSlot(str)
    def prepareDictionary(self,payload):
        try:
            p=json.loads(payload)
            destination=self.services.registry.resolve_profile(p['target'],p.get('profile') or None)
            self._run(lambda:self.services.dictionary.prepare(self.localPath(p['project']),destination,
                            p.get('mode','native'),self.cancelled,lambda text:self.activity.emit(text)),
                      'Diccionario · preparación','prepared_dictionary')
        except Exception as exc:self._fail('Diccionario · preparación',exc)

    @pyqtSlot(str)
    def saveDictionaryChoice(self,payload):
        try:
            if self.busy or self._prepared is None:raise ValueError('Prepara el Diccionario y espera a que termine')
            p=json.loads(payload)
            self.services.dictionary.save_choice(self._prepared,p['id'],p['decision'],p['text'],p['reason'])
            snapshot=self._prepared['snapshot']
            destination=self.services.registry.resolve_profile(snapshot['target']['language_id'],snapshot['target']['profile_id'] or None)
            self._prepared=self.services.dictionary.prepare(snapshot['canonical_game'],destination,snapshot['analysis']['mode'])
            self._dictionary=self.services.dictionary.view(self._prepared)
            self.current_id='';self._summary={'status':'dictionary_changed_create_new_job'}
            self.activity.emit('Diccionario guardado para este idioma/perfil. Crea otro trabajo para aplicar la decisión; los trabajos anteriores mantienen su identidad.')
            self.changed.emit()
        except Exception as exc:self._fail('Diccionario · guardar decisión',exc)

    @pyqtSlot()
    def clearDictionaryView(self):
        if not self.busy:
            self._dictionary={};self._prepared=None;self.changed.emit()

    @pyqtSlot()
    def showDictionary(self):self.openDictionaryRequested.emit()

    @pyqtSlot(result=str)
    def listDestinations(self):return json.dumps(self.services.registry.list_destinations(),ensure_ascii=False)
    @pyqtSlot(result=str)
    def listSpanishProfiles(self):return json.dumps(self.services.registry.list_profiles(),ensure_ascii=False)
    @pyqtSlot(result=str)
    def listProviders(self):
        from ..packaging.frozen_resources import resource_root
        providers=load_json(resource_root()/'linguanova_next/data/provider_capabilities.json')['providers']
        return json.dumps([{'id':k,**v} for k,v in providers.items()],ensure_ascii=False)
    @pyqtSlot(str,result=str)
    def createJob(self,payload):
        try:
            if self.busy:raise ValueError('The active job is immutable; wait or cancel before creating another')
            p=json.loads(payload);options=p.get('options',{})
            if p.get('recipe_path'):
                path=Path(self.localPath(p['recipe_path']))
                if not path.is_file():raise ValueError('No existe la receta de Preferencias: '+str(path))
                options['ui_recipe']=load_json(path)
            self.current_id='';self._dictionary={};self._prepared=None
            def work():
                job=self.services.create_job(self.localPath(p['project']),p.get('target','es'),p.get('profile') or None,
                    p.get('provider','google'),p.get('source','auto'),p.get('model',''),p.get('text_enabled',True),
                    p.get('mode','native'),options,
                    cancelled=self.cancelled,progress=lambda text:self.activity.emit(text))
                return job.job_id
            self._summary={'status':'preparing_dictionary','destination':p.get('target','es')}
            self._run(work,'Trabajo · creación','created_job')
            return ''
        except Exception as exc:self._fail('Trabajo · creación',exc);return ''

    @pyqtSlot(str)
    def translateFiveLanguages(self,payload):
        try:
            p=json.loads(payload);options=p.get('options',{})
            if p.get('recipe_path'):
                path=Path(self.localPath(p['recipe_path']))
                if not path.is_file():raise ValueError('No existe la receta: '+str(path))
                options['ui_recipe']=load_json(path)
            self.current_id='';self._dictionary={};self._prepared=None
            def work():
                from ..core.translation_job import TranslationJobRunner
                from ..dictionary.analysis import check_cancelled
                jobs=[]
                for destination in self.services.registry.list_destinations():
                    check_cancelled(self.cancelled)
                    target=destination['id'];profile=(p.get('spanish_profile') or 'latam_neutro_sin_modismos') if target=='es' else None
                    job=self.services.create_job(self.localPath(p['project']),target,profile,p.get('provider','google'),
                        p.get('source','auto'),p.get('model',''),p.get('text_enabled',True),
                        p.get('mode','native'),options,
                        cancelled=self.cancelled,progress=lambda text:self.activity.emit(text))
                    self.activity.emit('Lote · '+job.target_locale+' · '+job.job_id)
                    report=asyncio.run(TranslationJobRunner(self.services,job,cancelled=self.cancelled,
                        callback=lambda e:self.activity.emit(f'{e.kind}: {e.message}')).run())
                    jobs.append({'job_id':job.job_id,'destination':job.target_locale,'report':report})
                    check_cancelled(self.cancelled)
                return jobs
            self._run(work,'Lote · cinco idiomas','batch_jobs')
        except Exception as exc:self._fail('Lote · cinco idiomas',exc)

    @pyqtSlot(str)
    def startJob(self,job_id):
        try:
            job=self.services.load_job(job_id);self.current_id=job_id
            from ..core.translation_job import TranslationJobRunner
            def work():
                runner=TranslationJobRunner(self.services,job,callback=lambda e:self.activity.emit(f'{e.sequence} · {e.kind}: {e.message}'),cancelled=self.cancelled)
                return asyncio.run(runner.run())
            self._run(work,'Trabajo · traducción')
        except Exception as exc:self._fail('Trabajo · traducción',exc)

    @pyqtSlot()
    def cancelJob(self):self.cancelled.set();self.activity.emit('Cancellation requested; late replies will be discarded')
    @pyqtSlot(str)
    def loadJob(self,job_id):
        try:
            if self.busy:raise ValueError('Cannot change the active review while a job is running')
            job=self.services.load_job(job_id);self.current_id=job_id;self._set_dictionary(job)
            self._summary=load_json(self.services.data/'jobs'/job_id/'coverage_report.json',{})
            self._error='';self.changed.emit()
        except Exception as exc:self._fail('Trabajo · cargar',exc)
    @pyqtSlot(str)
    def reviewEntry(self,payload):
        try:
            if self.busy:raise ValueError('Pause the job before reviewing')
            p=json.loads(payload)
            self.services.review_entry(self.current_id,p['occurrence_id'],p['decision'],p.get('text',''),p['reason'],p.get('reviewer','Usuario'),p.get('editorial_approved',False))
            self.activity.emit('Review recorded; resume to validate and export this decision');self.changed.emit()
        except Exception as exc:self._fail('Revisión textual',exc)

