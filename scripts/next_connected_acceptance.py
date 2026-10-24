"""Drive the shipped QML actions: five targets, real OCR, review, ZIP and RAR.

HTTP translation responses are controlled fixture data, never live MT evidence.
No product methods are replaced. Each action uses the shipped UI/backend.
"""
import argparse
from dataclasses import asdict,replace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests/next'))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QML_DISABLE_DISK_CACHE','1')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Material')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl,QMetaObject,Qt,QCoreApplication,QEvent
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtQuick import QQuickWindow
from linguanova_next.bootstrap import Services
from linguanova_next.ui.backend import NextBackend
from linguanova_next.image.typography_profile import TypographyProfile
from linguanova_next.packaging.rar_archive import open_player_archive,rar_status
from linguanova_next.util import atomic_json,load_json,file_hash,safe_join
from support import TRANSLATIONS


def acceptance(workspace,rar=False):
    workspace=Path(workspace).resolve()
    if workspace.exists():raise ValueError('Choose a new test workspace')
    workspace.mkdir(parents=True)
    project=workspace/'Proyecto con espacios y á'
    shutil.copytree(ROOT/'next_fixtures/native_slot_game',project,
                    ignore=shutil.ignore_patterns('*.rpyc','cache','saves','log.txt','traceback.txt'))
    (project/'game/names.rpy').write_text('define nora = Character("Nora")\n',encoding='utf-8')
    before={p.relative_to(project).as_posix():file_hash(p) for p in project.rglob('*') if p.is_file()}
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):return
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append(payload)
            index={'es':0,'fr':2,'pt':3,'ru':4,'en':5}[payload['target']]
            texts=[]
            for text in payload['q']:
                result=TRANSLATIONS.get(text,[text]*6)[index]
                if text.startswith('Hello ') and ', this is a controlled test.' in text:
                    translated=TRANSLATIONS['Hello [player_name], this is a controlled test.'][index]
                    prefix,suffix=translated.split('[player_name]')
                    result=prefix+text[len('Hello '):text.index(', this is a controlled test.')]+suffix
                texts.append(result)
            data=json.dumps({'translatedText':texts},ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
            self.end_headers();self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
    os.environ['LINGUANOVA_NEXT_DATA']=str(workspace/'creator_data')
    app=QApplication.instance() or QApplication([])
    services=Services(data=workspace/'creator_data');backend=NextBackend(services,parent=app)
    engine=QQmlApplicationEngine(app)
    engine.rootContext().setContextProperty('nextBackend',backend)
    qml_errors=[]
    engine.warnings.connect(lambda errors:qml_errors.extend(e.toString() for e in errors))
    engine.load(QUrl.fromLocalFile(str(ROOT/'linguanova_next/ui/MainNext.qml')))
    if not engine.rootObjects():raise RuntimeError('MainNext.qml failed to load')
    window=engine.rootObjects()[0]
    backend.showWorkRequested.connect(lambda:window.setProperty('pageIndex',0))
    backend.openDictionaryRequested.connect(lambda:window.setProperty('pageIndex',4))
    backend.openShareRequested.connect(lambda:window.setProperty('pageIndex',3))
    def events():app.processEvents()
    def widget(name):
        def walk(item):
            yield item
            for child in item.childItems():yield from walk(child)
        matches=[item for item in walk(window.contentItem()) if item.objectName()==name]
        if len(matches)!=1:raise AssertionError('Expected one QML control: '+name+'; found '+str(len(matches)))
        return matches[0]
    def set_value(name,value,prop='text'):
        assert widget(name).setProperty(prop,value),(name,prop)
        events()
    def click(name):
        button=widget(name)
        assert button.property('enabled'),'Disabled shipped action: '+name
        QMetaObject.invokeMethod(button,'clicked',Qt.ConnectionType.DirectConnection)
        events()
    def finish(timeout=90):
        deadline=time.monotonic()+timeout
        while backend.busy:
            events()
            if time.monotonic()>deadline:raise TimeoutError('UI action timed out')
            time.sleep(.01)
        events()
        assert not backend.error,backend.error
    def capture(name):
        for _ in range(3):events();time.sleep(.05)
        assert window.grabWindow().save(str(workspace/(name+'.png')))
    try:
        events()
        assert json.loads(backend.dictionaryJson)=={}
        set_value('projectPath',str(project))
        provider_ids=[p['id'] for p in json.loads(backend.listProviders())]
        set_value('translationProvider',provider_ids.index('libretranslate'),'currentIndex')
        set_value('providerEndpoint','http://127.0.0.1:'+str(server.server_port))
        set_value('preferencesRecipe',str(ROOT/'linguanova_next/data/game_ui_profiles/controlled_fixture.json'))
        set_value('enableOcr',True,'checked')
        set_value('manualOcrReview',True,'checked')
        click('prepareDictionary');finish()
        assert any(e['source']=='Nora' for e in json.loads(backend.dictionaryJson)['entries'])
        capture('dictionary')
        window.setProperty('pageIndex',0)
        click('translateFiveLanguages');finish(120)
        jobs=json.loads(backend.summaryJson)['batch']
        assert len(jobs)==5 and {j['destination'] for j in jobs}=={'es-419','fr','pt','ru','en'}
        reports=[]
        style=TypographyProfile('fonts/DejaVuSans.ttf',file_hash(project/'game/fonts/DejaVuSans.ttf'),'DejaVu Sans',38,
                    color=(244,247,245,255),stroke_width=1,stroke_color=(17,28,34,255),shadow_offset=(2,2),
                    shadow_color=(0,0,0,180),evidence='identified',confidence=1,reviewer='fixture_author',
                    provenance='Exact source font/effects of this controlled fixture')
        for item in jobs:
            backend.loadJob(item['job_id']);events()
            directory=services.data/'jobs'/item['job_id']
            for entry in load_json(directory/'inventory.json'):
                if entry['original'] in ('Alex','LINGUANOVA FIXTURE','LinguaNova Controlled Fixture'):
                    backend.reviewEntry(json.dumps({'occurrence_id':entry['occurrence_id'],'decision':'preserve',
                        'reason':'Authored fixture title/name only','reviewer':'fixture_author'}));events()
            images=list(load_json(directory/'image_results.json').values())
            assert len(images)==4
            window.setProperty('pageIndex',2);events()
            for index,resource in enumerate(images):
                set_value('ocrImageSelect',index,'currentIndex')
                for region_index,row in enumerate(resource['regions']):
                    set_value('ocrRegionSelect',region_index,'currentIndex')
                    click('prepareOcrRegion')
                    draft=json.loads(widget('ocrRegionEditor').property('text'))
                    button='buttons/' in resource['path']
                    chosen=style if button else replace(style,size=42,color=(255,255,255,255),stroke_color=(0,0,0,255),shadow_color=(0,0,0,0),shadow_offset=(0,0))
                    draft.update(recognized_text='Continue',bounds=[75,18,405,126] if button else [160,55,480,185],
                        typography=asdict(chosen),reviewer='fixture_author',reason='Known fixture geometry/typeface',large_mask_approved=True)
                    set_value('ocrRegionEditor',json.dumps(draft))
                    click('saveOcrRegion')
                    assert not backend.error,backend.error
            click('resumeTranslationJob');finish()
            images=list(load_json(directory/'image_results.json').values())
            assert all(r['status']=='generated_pending_visual_review' for r in images),images
            for index,resource in enumerate(images):
                set_value('ocrImageSelect',index,'currentIndex')
                set_value('ocrFinalReason','Controlled fixture assertion: mask, original font and effects; no commercial-game approval')
                click('approveOcrImage')
                assert not backend.error,backend.error
            click('resumeTranslationJob');finish()
            final=load_json(directory/'image_results.json')
            assert all(r['status']=='reviewed' and r['pixel_validation']['outside_mask_equal'] for r in final.values())
            reports.append({'job_id':item['job_id'],'destination':item['destination'],
                'dictionary_reused':json.loads(services.load_job(item['job_id']).options_json)['dictionary']['statistics']['reused'],
                'coverage':load_json(directory/'coverage_report.json')})
        capture('ocr_reviewed')
        # Recognition is source-only: exactly four OCR cache entries serve all five targets.
        assert len(list((services.data/'cache_next/v2/ocr').glob('*.json')))==4
        window.setProperty('pageIndex',3);events()
        for item in jobs:
            name='shareJob_'+item['job_id'];set_value(name,True,'checked')
            QMetaObject.invokeMethod(widget(name),'toggled',Qt.ConnectionType.DirectConnection);events()
        click('previewShare')
        formats=['zip','rar'] if rar else ['zip']
        archives=[]
        for suffix in formats:
            set_value('shareArchiveFormat',1 if suffix=='rar' else 0,'currentIndex')
            destination=workspace/('Cinco_idiomas.'+suffix)
            set_value('shareOutput',str(destination));click('exportShare');finish()
            with open_player_archive(destination) as archive:
                manifest=json.loads(archive.read('manifest.json'))
                assert len(manifest['destinations'])==5
                for dest in manifest['destinations']:
                    for resource in images:
                        assert 'game/tl/'+dest['renpy_id']+'/'+resource['path'] in archive.namelist()
            archives.append(str(destination))
        # Exercise the recipient's manual copy, then the independent backup controls.
        installed=workspace/'Copia receptora';shutil.copytree(project,installed)
        with open_player_archive(archives[0]) as archive:
            for name in archive.namelist():
                if not name.startswith('game/'):continue
                path=safe_join(installed,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(name))
        backups=[]
        set_value('backupProject',str(installed))
        for suffix in formats:
            set_value('backupFormat',1 if suffix=='rar' else 0,'currentIndex')
            destination=workspace/('Respaldo_independiente.'+suffix)
            set_value('backupOutput',str(destination));click('exportIndependentBackup');finish()
            with open_player_archive(destination) as archive:
                assert len(json.loads(archive.read('manifest.json'))['destinations'])==5
                for name in archive.namelist():
                    if name.startswith('game/tl/'):assert archive.read(name)==safe_join(installed,name).read_bytes()
            backups.append(str(destination))
        capture('utilities')
        assert before=={p.relative_to(project).as_posix():file_hash(p) for p in project.rglob('*') if p.is_file()}
        assert json.loads(NextBackend(Services(data=services.data)).dictionaryJson)=={}
        assert not qml_errors,qml_errors
        result={'passed':True,'ui_actions':'shipped QML clicked/toggled handlers and QObject slots',
            'translation':'controlled local HTTP responses; NOT a live translation provider',
            'ocr':'real Tesseract','restoration':'real OpenCV Telea and Pillow composition',
            'targets':reports,'http_requests':len(requests),'ocr_cache_entries':4,
            'source_files_unchanged':True,'fresh_dictionary_view_empty':True,
            'packages':archives,'independent_backups':backups,'qml_warnings':qml_errors}
        atomic_json(workspace/'acceptance.json',result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return result
    finally:
        server.shutdown();server.server_close();server_thread.join(timeout=5)
        window.close();engine.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True);parser.add_argument('--rar',action='store_true')
    args=parser.parse_args()
    if args.rar and not rar_status()['available']:raise SystemExit(rar_status()['reason'])
    acceptance(args.workspace,args.rar)
