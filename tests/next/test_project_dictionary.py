import asyncio
import json
import shutil
import threading
from pathlib import Path
import pytest
from linguanova_next.bootstrap import Services
from linguanova_next.core.translation_job import TranslationJobRunner
from linguanova_next.dictionary.service import read_verified
from linguanova_next.dictionary.analysis import inventory_manifest
from linguanova_next.storage.cache_store import CacheStore
from linguanova_next.util import atomic_json, digest, load_json
from support import FixtureProvider


def prepare(services,project,target='es',profile=None):
    return services.dictionary.prepare(project,services.registry.resolve_profile(target,profile))


def test_source_analysis_reused_across_languages_and_decisions_are_separate(services,project,monkeypatch):
    first=prepare(services,project)
    assert not first['reused']
    term=next(e for e in first['snapshot']['analysis']['entities'] if e['source']=='Preferences')
    services.dictionary.save_choice(first,term['id'],'translate','Ajustes','UI terminology for this project')
    spanish=prepare(services,project)
    french=prepare(services,project,'fr')
    spain=prepare(services,project,'es','espana_estandar_sin_modismos')
    assert spanish['reused'] and french['reused'] and spain['reused']
    assert spanish['snapshot']['choices'][term['id']]['text']=='Ajustes'
    assert french['snapshot']['choices']==spain['snapshot']['choices']=={}
    assert spanish['snapshot']['source_key']==french['snapshot']['source_key']
    def no_rescan(*args,**kwargs):raise AssertionError('Unchanged game must reuse analysis')
    monkeypatch.setattr('linguanova_next.dictionary.service.analyze',no_rescan)
    assert prepare(services,project,'pt')['reused']


def test_path_identity_changes_and_source_updates_invalidate_analysis(services,project,tmp_path):
    first=prepare(services,project)
    second_project=tmp_path/'other game';shutil.copytree(project,second_project)
    other=prepare(services,second_project)
    assert other['snapshot']['project_id']!=first['snapshot']['project_id']
    script=project/'game/script.rpy'
    script.write_text(script.read_text()+'\ndefine rose = Character("Rose")\n',encoding='utf-8')
    changed=prepare(services,project)
    assert not changed['reused'] and changed['changed_files']==1
    assert any(e['source']=='Rose' for e in changed['snapshot']['analysis']['entities'])
    assert inventory_manifest(project/'game')


def test_source_revision_does_not_reuse_unreviewed_old_dictionary_choices(services,project):
    original=prepare(services,project)
    term=next(e for e in original['snapshot']['analysis']['entities'] if e['source']=='Preferences')
    services.dictionary.save_choice(original,term['id'],'translate','Ajustes','Verified for the original source revision')
    assert prepare(services,project)['snapshot']['choices']
    path=project/'game/script.rpy';path.write_text(path.read_text()+'\n# A changed game revision\n',encoding='utf-8')
    revised=prepare(services,project)
    assert revised['stale_choices']==1 and revised['snapshot']['choices']=={}


def test_names_are_scoped_to_declarations_not_homonyms_or_dialogue(services,project,recipe):
    path=project/'game/names.rpy'
    path.write_text('define rose = Character("Rose")\nlabel garden:\n    "A rose grows here."\n    "Rose"\n    return\n',encoding='utf-8')
    job=services.create_job(project,options={'ui_recipe':recipe,'attempts':1})
    runner=TranslationJobRunner(services,job,provider_factory=FixtureProvider)
    from linguanova_next.contracts.entry import Occurrence
    entries=[Occurrence(**e) for e in runner.dictionary['analysis']['inventory']]
    declaration=next(e for e in entries if e.original=='Rose' and 'Character(' in e.context)
    word=next(e for e in entries if e.original=='A rose grows here.')
    dialogue=next(e for e in entries if e.original=='Rose' and 'Character(' not in e.context)
    assert runner.dictionary_result(declaration).status=='preserved_approved'
    assert runner.dictionary_result(word) is None and runner.dictionary_result(dialogue) is None
    assert 'Rose' not in json.loads(job.glossary_json)
    report=asyncio.run(runner.run())
    assert report['processing']['denominator']==len(entries)
    assert report['validated_translation']['numerator'] < report['validated_translation']['denominator']
    assert report['status_counts'].get('preserved_approved',0)==0  # native old/new conflict is reported, not a global preservation
    assert any(r.status=='duplicate' for r in runner.store.results().values())


def test_declared_long_name_preserves_spelling_in_russian_without_translation_credit(services,project,recipe):
    (project/'game/name.rpy').write_text('define c = Character("Christopher Smith")\n',encoding='utf-8')
    job=services.create_job(project,'ru',options={'ui_recipe':recipe,'attempts':1})
    runner=TranslationJobRunner(services,job,provider_factory=FixtureProvider)
    report=asyncio.run(runner.run())
    result=next(r for r in runner.store.results().values() if r.candidate=='Christopher Smith')
    assert result.status=='preserved_approved' and result.written=='Christopher Smith'
    assert report['validated_translation']['numerator']<report['validated_translation']['denominator']


def test_missing_ocr_is_a_visible_preflight_failure_before_translating(services,project):
    with pytest.raises(ValueError,match='OCR no disponible'):
        services.create_job(project,image_enabled=True,options={'tesseract_executable':str(project/'missing-tesseract')})
    assert services.jobs()==[]


def test_dictionary_corruption_blocks_job_before_any_provider_call(services,project):
    prepared=prepare(services,project)
    path=services.data/'dictionaries'/prepared['snapshot']['project_id']/'native.json'
    raw=load_json(path);raw['payload']['analysis']['entities']=[];atomic_json(path,raw)
    before=len(FixtureProvider.calls)
    with pytest.raises(ValueError,match='Integridad'):services.create_job(project)
    assert len(FixtureProvider.calls)==before and services.jobs()==[]
    diagnostics=services.diagnostics.path.read_text()
    assert 'Diccionario' in diagnostics and str(project/'game') in diagnostics


def test_snapshot_tampering_cannot_resume_and_choices_freeze_per_job(services,project):
    prepared=prepare(services,project)
    term=next(e for e in prepared['snapshot']['analysis']['entities'] if e['source']=='Preferences')
    original_job=services.create_job(project)
    services.dictionary.save_choice(prepared,term['id'],'translate','Ajustes','UI term')
    updated=services.create_job(project)
    assert original_job.glossary_hash!=updated.glossary_hash
    assert json.loads(updated.glossary_json)['Preferences']=='Ajustes'
    assert 'Preferences' not in json.loads(original_job.glossary_json)
    assert services.validate_resume(original_job)
    path=services.data/'jobs'/original_job.job_id/'dictionary_snapshot.json'
    raw=load_json(path);raw['target']['locale']='fr';atomic_json(path,raw)
    with pytest.raises(ValueError,match='Diccionario'):services.validate_resume(original_job)


def test_invalid_encoding_and_cancellation_do_not_write_successful_jobs(services,project):
    (project/'game/bad.rpy').write_bytes(b'label bad:\n    "\xff"\n')
    with pytest.raises(ValueError,match='UTF-8'):services.create_job(project)
    assert services.jobs()==[]
    (project/'game/bad.rpy').unlink()
    from linguanova_next.core.work_queue import CancelledJob
    cancelled=threading.Event();cancelled.set()
    with pytest.raises(CancelledJob):services.create_job(project,cancelled=cancelled)
    assert services.jobs()==[]


def test_cache_corruption_and_cross_project_reuse_are_blocked(services,project,tmp_path):
    from linguanova_next.contracts.entry import Occurrence
    job=services.create_job(project)
    e=Occurrence.create('s.rpy',2,'Hello','say','dialogue','same')
    cache=CacheStore(services.data);key=cache.key(job,e,'google')
    cache.put('text',key,{'text':'Hola'},accepted=True)
    assert cache.get('text',key)['text']=='Hola'
    raw=load_json(cache.path('text',key));raw['payload']['text']='Wrong language';atomic_json(cache.path('text',key),raw)
    with pytest.raises(ValueError,match='integrity'):cache.get('text',key)
    different=tmp_path/'another';shutil.copytree(project,different)
    assert cache.key(services.create_job(different),e,'google')!=key


def test_dictionary_ui_starts_empty_even_when_analysis_is_saved(services,project):
    prepare(services,project)
    from linguanova_next.ui.backend import NextBackend
    backend=NextBackend(services)
    assert json.loads(backend.dictionaryJson)=={}
    job=services.create_job(project);backend.loadJob(job.job_id)
    assert json.loads(backend.dictionaryJson)['project']==str(project/'game')
    backend.selectDictionaryContext(str(project),'fr','')
    assert json.loads(backend.dictionaryJson)=={}
    assert json.loads(NextBackend(Services(data=services.data)).dictionaryJson)=={}
