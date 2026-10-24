import asyncio
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from linguanova_next.linguistic.profile_validator import validate
from linguanova_next.contracts.entry import Occurrence, Candidate
from linguanova_next.contracts.result import EntryResult
from linguanova_next.contracts.ocr_messages import RegionResponse
from linguanova_next.bridge.ocr_translation_bridge import OcrTranslationBridge
from linguanova_next.core.work_queue import WorkQueue, CancelledJob
from linguanova_next.core.coverage_audit import audit
from linguanova_next.core.translation_report import metric
from linguanova_next.util import digest


def test_contextual_regional_rules_and_shared_vocabulary(services,project):
    latam=services.create_job(project,'es')
    spain=services.create_job(project,'es','espana_estandar_sin_modismos')
    assert not validate(latam,'You can come.','Vosotros podéis venir.').accepted
    assert not validate(spain,'You can come.','Vos tenés permiso.').accepted
    assert validate(latam,'Good morning','Buenos días').accepted
    assert validate(spain,'Good morning','Buenos días').accepted
    assert not validate(latam,'Hello [name]','Hola').accepted
    assert not validate(latam,'{b}{i}Hi{/i}{/b}','{i}{b}Hola{/i}{/b}').accepted
    assert not validate(latam,'Hello','Hello').accepted
    assert validate(latam,'Alex','Alex',allow_preserve=True).accepted


def test_audit_readonly_identity_and_overlapping_flags(services,project,tmp_path):
    job=services.create_job(project)
    entries=[Occurrence.create('a.rpy',i,x,'ctx','dialogue','h') for i,x in enumerate(['Hello','Name','Blocked'])]
    results={entries[0].occurrence_id:EntryResult(entries[0].occurrence_id,job.identity,'accepted','Hola',written='Hola'),
             entries[1].occurrence_id:EntryResult(entries[1].occurrence_id,job.identity,'preserved_approved','Name',written='Name'),
             entries[2].occurrence_id:EntryResult(entries[2].occurrence_id,job.identity,'rejected_validation','Blocked',flags=('source_copy',))}
    before={p.relative_to(services.data).as_posix():p.read_bytes() for p in services.data.rglob('*') if p.is_file()}
    report,read=audit(job,entries,results,{'Hello':'Hola','Name':'Name'})
    after={p.relative_to(services.data).as_posix():p.read_bytes() for p in services.data.rglob('*') if p.is_file()}
    assert before==after and len(read)==3
    assert report['inventory_resolution']['numerator']==2 and report['inventory_resolution']['denominator']==3
    assert sum(report['status_counts'].values())==3
    wrong=results.copy();wrong[entries[0].occurrence_id]=replace(results[entries[0].occurrence_id],job_identity='other')
    with pytest.raises(ValueError):audit(job,entries,wrong,{})
    assert metric(999999,1000000)['percent']<100 and metric(0,0)['percent'] is None


def test_ocr_bridge_source_destination_and_cancellation(services,project):
    job=services.create_job(project,'es',source='auto')
    queue=WorkQueue();calls=[]
    async def translate(entry,source):
        calls.append((source,job.target_identity))
        c=Candidate(entry.occurrence_id,'Hola','fixture','test',source,'request',job.identity)
        return c,validate(job,entry.original,c.text)
    bridge=OcrTranslationBridge(job,translate,queue)
    resource=SimpleNamespace(resource_id='resource',image_hash='image')
    region=SimpleNamespace(region_id='region',text='こんにちは',source_language='ja',bounds=(0,0,100,30),confidence=.98)
    request=bridge.request(resource,region)
    with pytest.raises(ValueError):bridge.accept(RegionResponse(replace(request,target_locale='es-ES'),'Hola','accepted','fixture'))
    response=asyncio.run(bridge.translate(request))
    assert calls[0][0]=='ja' and response.request.target_locale=='es-419'
    bridge.require_current(response,resource)
    with pytest.raises(ValueError):bridge.accept(response)
    queue.cancelled.set()
    with pytest.raises(CancelledJob):bridge.require_current(response,resource)


def test_reject_mislabeled_content(services,project):
    job=services.create_job(project,'ru')
    verdict=validate(job,'Some original content','This response remains entirely in the English language.')
    assert not verdict.accepted and 'target_script_mismatch' in verdict.reasons


def test_lock_is_cross_process(project):
    from linguanova_next.core.job_lock import JobLock
    import subprocess,sys
    with JobLock(project):
        result=subprocess.run([sys.executable,'-c','from linguanova_next.core.job_lock import JobLock; import sys; lock=JobLock(sys.argv[1]); lock.__enter__()',str(project)],capture_output=True)
        assert result.returncode!=0 and b'Another new-flow job' in result.stderr
    with JobLock(project):pass
