"""RAR tests execute the real optional archiver when it is installed."""
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import pytest
from linguanova_next.packaging.rar_archive import rar_status, zip_to_rar, RarArchive
from linguanova_next.packaging.share_package_builder import SharePackageBuilder
from linguanova_next.packaging.share_package_validator import validate_archive
from linguanova_next.packaging.share_package_installation import install_copy, remove_owned
from linguanova_next.core.translation_job import TranslationJobRunner
from linguanova_next.util import file_hash
from support import FixtureProvider


def require_rar():
    if not rar_status()['available']:
        pytest.skip('Real RAR/WinRAR archiver not installed on the creator computer')


def test_missing_rar_preserves_last_valid_package(tmp_path, monkeypatch):
    monkeypatch.setenv('LINGUANOVA_NEXT_RAR_EXECUTABLE', str(tmp_path/'missing'/'Rar.exe'))
    path = tmp_path/'previous.rar'
    path.write_bytes(b'last-valid-output')
    with pytest.raises(ValueError, match='RAR requiere'):
        SharePackageBuilder().build([], path)
    assert path.read_bytes() == b'last-valid-output'


def test_real_rar_binary_unicode_paths_and_exact_copy(tmp_path):
    require_rar()
    files = {'game/tl/spanish_latam/texto.rpy': 'translate spanish_latam strings:\n    old "Hello"\n    new "Hola"\n'.encode(),
             'game/tl/spanish_latam/images/capítulo á/imagen.png': bytes(range(256))*8}
    manifest = {'package_id':'controlled-rar-binary-test', 'validation_level':'experimental_unverified',
                'files':[{'path':n,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for n,data in files.items()]}
    source = tmp_path/'source.zip'
    with zipfile.ZipFile(source,'w') as archive:
        for name,data in files.items(): archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps(manifest))
        archive.writestr('LEEME_INSTALACION.txt','Copy game/ into the root of the compatible fixture')
    target = tmp_path/'Traducción con espacios á.rar'
    result = zip_to_rar(source,target)
    assert result['valid'] and result['content_verified_against_zip']
    assert target.read_bytes().startswith(b'Rar!\x1a\x07\x01\x00')
    assert validate_archive(target)['valid']
    with RarArchive(target) as archive:
        for name,data in files.items(): assert archive.read(name)==data
    game = tmp_path/'Segunda copia á';(game/'game').mkdir(parents=True)
    unrelated = game/'game/tl/german/manual.rpy';unrelated.parent.mkdir(parents=True);unrelated.write_text('manual')
    persistent = game/'game/saves/persistent';persistent.parent.mkdir();persistent.write_bytes(b'player-choice')
    installed = install_copy(target,game,tmp_path/'backup')
    install_copy(target,game,tmp_path/'backup_update',previous_manifest=installed)
    removed = remove_owned(game,installed)
    assert len(removed['removed'])==len(files) and not removed['modified_or_foreign']
    assert unrelated.read_text()=='manual' and persistent.read_bytes()==b'player-choice'


def test_real_rar_builder_same_payload_as_zip(services,project,recipe,tmp_path):
    require_rar()
    job = services.create_job(project,'fr',options={'ui_recipe':recipe,'attempts':1})
    asyncio.run(TranslationJobRunner(services,job,provider_factory=FixtureProvider).run())
    directories = [services.data/'jobs'/job.job_id]
    builder = SharePackageBuilder()
    zipper = tmp_path/'review.zip';rar = tmp_path/'review.rar'
    builder.build(directories,zipper);builder.build(directories,rar)
    with zipfile.ZipFile(zipper) as first, RarArchive(rar) as second:
        assert set(first.namelist())==set(second.namelist())
        for name in first.namelist():assert first.read(name)==second.read(name)
