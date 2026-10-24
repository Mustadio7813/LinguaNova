import asyncio
from dataclasses import asdict,replace
import itertools
import json
from pathlib import Path
import shutil
import threading
import zipfile
import pytest
from linguanova_next.core.translation_job import TranslationJobRunner
from linguanova_next.packaging.share_package_builder import SharePackageBuilder
from linguanova_next.packaging.share_package_validator import validate_zip
from linguanova_next.packaging.share_package_installation import install_copy,remove_owned
from linguanova_next.packaging.native_ui_export import build_native_ui
from linguanova_next.core.native_ui_policy import require_preferences_only
from linguanova_next.adapters.language_menu_adapter import installed_languages
from linguanova_next.util import load_json,file_hash,digest,atomic_json
from support import TARGETS,FixtureProvider,copy_fixture


@pytest.mark.parametrize('target,profile',TARGETS)
def test_real_coordinator_controlled_provider_native_export(services,project,recipe,target,profile):
    job=services.create_job(project,target,profile,options={'ui_recipe':recipe,'attempts':1})
    snapshot={p.relative_to(project).as_posix():file_hash(p) for p in project.rglob('*') if p.is_file()}
    result=asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
    directory=services.data/'jobs'/job.job_id
    assert result['processing']['numerator']==result['processing']['denominator']
    assert result['validated_translation']['numerator']>0
    player=directory/'published/game'
    source=(player/'zzz_linguanova_preferences_languages.rpy').read_text()
    assert job.renpy_id in source and 'renpy.save_persistent()' in source
    assert 'config.language = None' in source and 'key ' not in source
    assert not __import__('re').search(r'_preferences\.language\s*=(?!=)',source)
    assert (player/'zzz_linguanova_ocultar_fuentes.rpy').exists()
    assert (player/'tl'/job.renpy_id/'linguanova_next_strings.rpy').is_file()
    assert snapshot=={p.relative_to(project).as_posix():file_hash(p) for p in project.rglob('*') if p.is_file()}
    for action in load_json(directory/'inventory.json'):
        if action['original']=='Alex':
            services.review_entry(job.job_id,action['occurrence_id'],'preserve','',reason='Known character name in the controlled fixture',reviewer='fixture_author',editorial_approved=True)
    asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
    assert any(r.status=='preserved_approved' for r in TranslationJobRunner(services,job).store.results().values())


def test_multiple_languages_reproducible_share_copy_update_remove(services,project,recipe,tmp_path):
    directories=[]
    for target,profile in TARGETS:
        job=services.create_job(project,target,profile,options={'ui_recipe':recipe,'attempts':1})
        asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
        directories.append(services.data/'jobs'/job.job_id)
    builder=SharePackageBuilder()
    preview=builder.preview(directories)
    assert len(preview['destinations'])==6
    package=tmp_path/'traducción compartida.zip'
    package2=tmp_path/'same.zip'
    builder.build(directories,package);builder.build(directories,package2)
    assert file_hash(package)==file_hash(package2)
    assert validate_zip(package)['valid']
    with zipfile.ZipFile(package) as archive:
        assert len([n for n in archive.namelist() if n.endswith('preferences_languages.rpy')])==1
        assert all(n.startswith('game/') or n in ('manifest.json','LEEME_INSTALACION.txt') for n in archive.namelist())
        assert not any('game/game/' in n or 'cache' in n or 'settings' in n for n in archive.namelist())
    clean=tmp_path/'Segunda copia con á y espacios';shutil.copytree(project,clean)
    foreign=clean/'game/tl/german/manual.rpy';foreign.parent.mkdir(parents=True);foreign.write_text('translate german strings:\n    old "Other"\n    new "Andere"\n')
    save=clean/'game/saves/persistent';save.parent.mkdir();save.write_bytes(b'player-data')
    manifest=install_copy(package,clean,tmp_path/'backup')
    assert len(installed_languages(clean/'game'))==7
    install_copy(package,clean,tmp_path/'backup2',previous_manifest=manifest)
    removed=remove_owned(clean,manifest)
    assert not removed['modified_or_foreign'] and save.read_bytes()==b'player-data' and foreign.exists()
    assert all(not (clean/f['path']).exists() for f in manifest['files'])


def test_unknown_native_ui_is_explicitly_blocked(services,project,tmp_path):
    result=build_native_ui(project/'game',tmp_path/'stage',[],None)
    assert not result['preferences_only']
    with pytest.raises(ValueError):require_preferences_only(result,complete=True)
    assert not (tmp_path/'stage/zzz_linguanova_preferences_languages.rpy').exists()


def test_foreign_output_and_bad_zip_paths_rejected(services,project,recipe,tmp_path):
    job=services.create_job(project,options={'ui_recipe':recipe,'attempts':1})
    asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
    package=tmp_path/'package.zip';SharePackageBuilder().build([services.data/'jobs'/job.job_id],package)
    with zipfile.ZipFile(package) as z:manifest=json.loads(z.read('manifest.json'))
    foreign=project/manifest['files'][0]['path'];foreign.parent.mkdir(parents=True,exist_ok=True);foreign.write_text('foreign')
    with pytest.raises(ValueError,match='foreign'):install_copy(package,project,tmp_path/'backup')
    malicious=tmp_path/'bad.zip'
    with zipfile.ZipFile(malicious,'w') as z:z.writestr('../outside','bad')
    assert not validate_zip(malicious)['valid']


def test_cancelled_job_cannot_publish_late_reply(services,project,recipe):
    cancelled=threading.Event()
    class CancellingProvider(FixtureProvider):
        async def translate(self,*args,**kwargs):
            result=await super().translate(*args,**kwargs)
            cancelled.set();return result
    job=services.create_job(project,options={'ui_recipe':recipe,'attempts':1})
    runner=TranslationJobRunner(services,job,cancelled=cancelled,provider_factory=CancellingProvider)
    assert asyncio.run(runner.run()) is None
    assert load_json(runner.store.directory/'state.json')['status']=='paused'
    assert not (runner.store.directory/'published').exists()


@pytest.mark.parametrize('target,profile_id',TARGETS)
def test_complete_image_workflow_real_ocr_classic_reconstruction_and_review(services,project,recipe,target,profile_id):
    from linguanova_next.adapters.ocr_provider import TesseractProvider
    if not TesseractProvider().available()['available']:pytest.skip('Tesseract not installed')
    from linguanova_next.image.typography_profile import TypographyProfile
    job=services.create_job(project,target,profile_id,text_enabled=False,image_enabled=True,options={'ui_recipe':recipe,'attempts':1,'image_review_mode':'manual'})
    directory=services.data/'jobs'/job.job_id
    def run():return asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
    run();images=load_json(directory/'image_results.json')
    assert images and all(r['status']=='pending_region_translation_or_typography_review' for r in images.values())
    profile=TypographyProfile('fonts/DejaVuSans.ttf',file_hash(project/'game/fonts/DejaVuSans.ttf'),'DejaVu Sans',38,
                    color=(244,247,245,255),stroke_width=1,stroke_color=(17,28,34,255),shadow_offset=(2,2),
                    shadow_color=(0,0,0,180),evidence='identified',confidence=1,reviewer='controlled_fixture_author',
                    provenance='The fixture source drew this exact font/effects')
    for resource_id,resource in images.items():
        for item in resource['regions']:
            bounds=[75,25,405,130] if 'buttons/' in resource['path'] else [160,55,480,180]
            services.review_region(job.job_id,resource_id,item['region']['region_id'],{
                'recognized_text':'Continue','bounds':bounds,'typography':asdict(profile),
                'reviewer':'controlled_fixture_author','reason':'Known source geometry/typeface in authored fixture',
                'large_mask_approved':True})
    run();images=load_json(directory/'image_results.json')
    assert all(r['status']=='generated_pending_visual_review' for r in images.values()),images
    for resource_id in images:services.approve_image(job.job_id,resource_id,'Reviewed controlled sample: mask, effects and legibility','fixture_author')
    report=run();images=load_json(directory/'image_results.json')
    assert all(r['status']=='reviewed' and r['pixel_validation']['outside_mask_equal'] for r in images.values())
    assert report['visual_coverage']['numerator']==len(images)
    for resource in images.values():
        assert (directory/'published'/resource['output_path']).is_file()
        assert resource['output_path'].endswith(resource['path'])
