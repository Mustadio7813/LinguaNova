import dataclasses
import json
from pathlib import Path
import subprocess
import sys
import pytest
from linguanova_next.baseline import verify_baseline
from linguanova_next.core.language_registry import LanguageRegistry
from linguanova_next.storage.cache_store import CacheStore
from linguanova_next.contracts.entry import Occurrence
from linguanova_next.util import digest
from support import TARGETS


def test_base_integrity():
    result=verify_baseline(Path(__file__).resolve().parents[2])
    assert result['valid'] and result['protected_count']==283


def test_lightweight_imports():
    code='import sys; import linguanova_next.contracts.job, linguanova_next.baseline; assert not any(n in sys.modules for n in ["PyQt6", "torch", "cv2", "aiohttp", "google.genai"])'
    subprocess.run([sys.executable,'-c',code],check=True)


def test_exactly_five_base_destinations():
    registry=LanguageRegistry()
    assert [x['id'] for x in registry.list_destinations()]==['es','fr','pt','ru','en']
    assert len(registry.list_profiles())==2
    assert registry.resolve_profile('es').renpy_id=='spanish_latam'
    with pytest.raises(ValueError):registry.resolve_profile('ja')
    assert registry.legacy_identity('spanish')['variant']=='unknown'


@pytest.mark.parametrize('target,profile',TARGETS)
def test_job_immutable_roundtrip_and_resume(services,project,target,profile):
    job=services.create_job(project,target,profile,provider='google')
    assert services.load_job(job.job_id)==job
    assert services.validate_resume(job)
    with pytest.raises(dataclasses.FrozenInstanceError):job.target_locale='en'
    (project/'game/script.rpy').write_text('label start:\n    "Changed source"\n')
    with pytest.raises(ValueError,match='changed'):services.validate_resume(job)


def test_cache_namespaces_profiles_and_context(services,project):
    a=services.create_job(project,'es','latam_neutro_sin_modismos')
    b=services.create_job(project,'es','espana_estandar_sin_modismos')
    e=Occurrence.create('script.rpy',2,'Hello','label start','dialogue','sourcehash')
    c=CacheStore(services.data)
    ka=c.key(a,e,'google');kb=c.key(b,e,'google')
    assert ka!=kb and ka!=c.key(a,dataclasses.replace(e,context='different'),'google')
    assert ka!=c.key(a,e,'bing') and ka!=c.key(a,e,'google',namespace='mod')
    with pytest.raises(ValueError):c.put('text',ka,{'text':'rejected'})
    c.put('text',ka,{'text':'Hola'},accepted=True)
    assert c.get('text',kb) is None and c.get('mod',ka) is None


def test_synthetic_catalog_scaling_does_not_enable_production():
    base=LanguageRegistry().catalog
    synthetic=json.loads(json.dumps(base))
    synthetic['languages'] += [{'id':'synthetic_'+str(i),'name':'Test','locale':'test','renpy_id':'test_'+str(i),'enabled':False} for i in range(134)]
    assert len(synthetic['languages'])==139
    assert len(LanguageRegistry(synthetic).list_destinations())==5
    assert len(LanguageRegistry().list_destinations())==5


def test_secret_settings_rejected(services,project):
    with pytest.raises(ValueError,match='credentials'):
        services.create_job(project,options={'provider':{'api_key':'do-not-save'}})
