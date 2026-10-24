import json
from pathlib import Path
import threading
import zipfile
import pytest
from linguanova_next.packaging.translation_backup import TranslationBackup
from linguanova_next.packaging.rar_archive import open_player_archive, rar_status
from linguanova_next.util import file_hash


def installed(project):
    names=['spanish_latam','french','portuguese','russian','english']
    for index,name in enumerate(names):
        root=project/'game/tl'/name
        (root/'gui/buttons').mkdir(parents=True)
        (root/'text.rpy').write_text(f'translate {name} strings:\n    old "Hello"\n    new "Translation {index}"\n',encoding='utf-8')
        # Exact distinct bytes prove the backup does not reuse one language's image.
        (root/'gui/buttons/play.png').write_bytes(b'controlled image '+name.encode())
    return names


@pytest.mark.parametrize('suffix',['zip','rar'])
def test_independent_five_language_backup_preserves_every_path_and_byte(project,tmp_path,suffix):
    if suffix=='rar' and not rar_status()['available']:pytest.skip('RAR executable unavailable')
    names=installed(project)
    save=project/'game/saves/persistent';save.parent.mkdir();save.write_bytes(b'private')
    before={str(p):file_hash(p) for p in project.rglob('*') if p.is_file()}
    destination=tmp_path/('all_five.'+suffix)
    result=TranslationBackup().build(project,destination)
    assert result['valid'] and set(result['languages'])==set(names)
    with open_player_archive(destination) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['kind']=='installed_translation_backup'
        for name in names:
            relative=f'game/tl/{name}/gui/buttons/play.png'
            assert archive.read(relative)==(project/relative).read_bytes()
        assert not any('game/game/' in n or 'saves/' in n for n in archive.namelist())
    assert before=={str(p):file_hash(p) for p in project.rglob('*') if p.is_file()}


def test_backup_failure_and_cancellation_preserve_previous_archive(project,tmp_path):
    destination=tmp_path/'backup.zip';destination.write_bytes(b'previous good archive')
    with pytest.raises(ValueError,match='game/tl'):TranslationBackup().build(project,destination)
    installed(project)
    with pytest.raises(ValueError,match='fuera'):TranslationBackup().build(project,project/'game/tl/backup.zip')
    event=threading.Event();event.set()
    from linguanova_next.core.work_queue import CancelledJob
    with pytest.raises(CancelledJob):TranslationBackup().build(project,destination,event)
    assert destination.read_bytes()==b'previous good archive'
