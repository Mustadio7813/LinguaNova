"""Real main-window button -> main text pipeline -> OCR -> installed images.

Uses real Tesseract and the main LibreTranslate HTTP client with explicitly
controlled local responses, then opens the installed result in real Ren'Py.
"""
from pathlib import Path
import argparse,hashlib,html,json,os,shutil,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests/next')]


def verify(workspace,renpy,all_languages=False):
    workspace=Path(workspace).resolve()
    if workspace.exists():raise ValueError('Choose a fresh workspace')
    workspace.mkdir(parents=True)
    os.environ.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QML_DISABLE_DISK_CACHE='1',
        LINGUANOVA_PROJECT_ROOT=str(ROOT),XDG_DATA_HOME=str(workspace/'creator'))
    from support import copy_fixture
    from test_ocr_resource_formats import rpa,image_bytes,FORMATS
    from linguanova_next.adapters.resource_catalog import ResourceCatalog
    from linguanova_next.image.image_formats import decode
    from linguanova_next.util import atomic_json,file_hash
    project=copy_fixture(workspace)
    game=project/'game'
    members={}
    for suffix,fmt in FORMATS:
        members['images/native/native_'+suffix[1:]+suffix]=image_bytes(project,suffix,fmt)
    reference=game/'native_image_references.rpy'
    reference.write_text('\n'.join('image native_'+suffix[1:]+' = '+json.dumps('images/native/native_'+suffix[1:]+suffix) for suffix,fmt in FORMATS)+'\n')
    compiled=subprocess.run([str(renpy),str(project),'compile'],env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,text=True,timeout=60)
    assert compiled.returncode==0,compiled.stdout+compiled.stderr
    members['native_image_references.rpyc']=reference.with_suffix('.rpyc').read_bytes()
    reference.unlink();reference.with_suffix('.rpyc').unlink()
    rpa(game/'native_assets.rpa',members)
    receiver=workspace/'receiver';shutil.copytree(project,receiver)
    catalog=ResourceCatalog(game)
    source_hashes={name:hashlib.sha256(catalog.read(name)).hexdigest() for name in members if name.startswith('images/')}
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            calls.append(payload)
            def translate(value):
                mapping={'Continue':'Continuer','Start':'Commencer','Preferences':'Préférences','Quit':'Quitter','Return':'Retour',
                    'Welcome to our quiet village.':'Bienvenue dans notre paisible village.',
                    'Hello ':'Bonjour ', ', this is a controlled test.':', ceci est un test contrôlé.'}
                word={'fr':'Continuer','es':'Continuar','pt':'Continuar','ru':'Продолжить','en':'Continue'}[payload['target']]
                mapping['Continue']=word
                for old,new in mapping.items():value=value.replace(old,new)
                return value if value!=payload else value
            values=payload['q'];body=json.dumps({'translatedText':[translate(v) for v in values]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtQuick import QQuickItem
    from PyQt6.QtCore import QUrl,QCoreApplication,QEvent,QPointF
    from PyQt6.QtQml import QQmlApplicationEngine,QQmlExpression,qmlContext
    from PyQt6.QtTest import QTest
    from src.backend.app_backend import AppBackend
    from src.backend.editor_backend import EditorBackend
    from src.core.translator import TranslationEngine
    app=QApplication([]);backend=AppBackend(parent=app);backend.setUILanguage('es')
    backend.config.app_settings.unren_auto_download=False
    backend.config.translation_settings.request_delay=0
    backend.libretranslateUrl='http://127.0.0.1:'+str(server.server_port)
    backend.setSelectedEngine('libretranslate')
    backend.setSourceLanguage('auto');backend.setTargetLanguage('french')
    backend.images.sourceModel='auto'
    editor=EditorBackend(backend,parent=app);engine=QQmlApplicationEngine(app)
    engine.rootContext().setContextProperty('appBackend',backend);engine.rootContext().setContextProperty('editorBackend',editor)
    engine.addImportPath(str(ROOT/'src/gui/qml'));engine.load(QUrl.fromLocalFile(str(ROOT/'src/gui/qml/Main.qml')))
    assert len(engine.rootObjects())==1
    window=engine.rootObjects()[0];window.setWidth(1366);window.setHeight(900);window.show()
    backend.setProjectPath(str(project))
    finished=[];stages=[];logs=[];ocr_windows=[]
    backend.translationFinished.connect(lambda ok,message:finished.append({'success':ok,'message':message}))
    backend.logMessage.connect(lambda level,message:logs.append({'level':level,'message':message}))
    def stage_changed(stage,message):
        stages.append(stage)
        if stage=='images':ocr_windows.append(len([w for w in app.topLevelWindows() if w.isVisible()]))
    backend.stageChanged.connect(stage_changed)
    def evaluate(scope,code):
        expression=QQmlExpression(qmlContext(scope),scope,code);value=expression.evaluate()
        assert not expression.hasError(),expression.error().toString()
        return value
    try:
        QTest.qWait(350)
        button=window.findChild(QQuickItem,'nativeTranslateAll' if all_languages else 'mainTranslateButton');assert button
        evaluate(button,'clicked()')
        deadline=time.monotonic()+120
        while (len(finished)<(5 if all_languages else 1)) and time.monotonic()<deadline:QTest.qWait(100)
        atomic_json(workspace/'creator_log.json',logs)
        assert len(finished)==(5 if all_languages else 1) and all(v['success'] for v in finished),{'finished':finished,'log':logs[-15:]}
        report=backend.images.report
        atomic_json(workspace/'native_images.json',report)
        assert report['status']=='completed' and report['counts']['translated']==13,report
        assert 'images' in stages and ocr_windows and max(ocr_windows)==1,{'stages':stages,'windows':ocr_windows}
        evaluate(window,'completionDialog.close()')
        card=window.findChild(QQuickItem,'nativeOcrCard');assert card
        parent=card.parentItem()
        while parent:
            if parent.property('contentY') is not None and parent.property('contentHeight') is not None:
                point=card.mapToItem(parent,QPointF(0,0))
                parent.setProperty('contentY',max(0,min(parent.property('contentHeight')-parent.height(),parent.property('contentY')+point.y()-80)));break
            parent=parent.parentItem()
        QTest.qWait(150);assert window.grabWindow().save(str(workspace/'native_main.png'))
        package=workspace/'Traduccion_nativa.zip'
        backend.images.createPackage(str(package))
        deadline=time.monotonic()+30
        while backend.images.busy and time.monotonic()<deadline:QTest.qWait(100)
        assert package.is_file(),backend.images.status
        from linguanova_next.packaging.share_package_installation import install_copy
        install_copy(package,receiver,workspace/'backup')
        spec={'languages':['spanish','french','english','portuguese','russian'] if all_languages else ['french'],'images':[]}
        for resource in catalog.resources.values():
            if Path(resource.path).suffix.lower() not in {s for s,_ in FORMATS}:continue
            original=catalog.read(resource)
            local=receiver/'game/tl/french'/resource.path
            assert local.is_file(),str(local)
            spec['images'].append({'path':resource.path,'size':list(decode(original,Path(resource.path).suffix).frames[0].size),
                'hashes':dict({'Original':hashlib.sha256(original).hexdigest()},**{lang:file_hash(receiver/'game/tl'/lang/resource.path) for lang in spec['languages'] if (receiver/'game/tl'/lang/resource.path).is_file()})})
        assert source_hashes=={name:hashlib.sha256(ResourceCatalog(game).read(name)).hexdigest() for name in source_hashes}
        from verify_ocr_resources import ENGINE_SCRIPT
        (receiver/'game/zzzz_verify_ocr.rpy').write_text(ENGINE_SCRIPT)
        engine_report=workspace/'engine.json'
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',
            LINGUANOVA_ENGINE_SPEC=json.dumps(spec),LINGUANOVA_ENGINE_REPORT=str(engine_report))
        completed=subprocess.run([str(renpy),str(receiver),'--savedir',str(workspace/'saves')],env=env,capture_output=True,text=True,timeout=90)
        (workspace/'engine.log').write_text(completed.stdout+completed.stderr)
        actual=json.loads(engine_report.read_text()) if engine_report.is_file() else {}
        assert completed.returncode==0 and actual.get('success'),{'exit':completed.returncode,'engine':actual,'log':completed.stdout+completed.stderr}
        result={'success':True,'main_window_count_during_ocr':ocr_windows,'main_button_used':True,'secondary_ocr_window':False,
            'native_counts':report['counts'],'jobs':len(finished),'all_languages':all_languages,'engine':actual,'http_requests':len(calls),'provider':'main LibreTranslate client with controlled local responses',
            'archive_originals_unchanged':True,'compiled_windows_verified':False,'stages':stages}
        atomic_json(workspace/'acceptance.json',result)
        return result
    finally:
        backend.shutdown();engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);parser.add_argument('--renpy',required=True);parser.add_argument('--all-languages',action='store_true')
    args=parser.parse_args();result=verify(args.workspace,Path(args.renpy).resolve(),args.all_languages)
    print(json.dumps({'success':result['success'],'images':result['native_counts'],'engine_loads':len(result['engine']['loads']),'one_window':True},indent=2))
