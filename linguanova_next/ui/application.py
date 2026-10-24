"""Normal Qt composition, including a new last card in original Utilities."""
import os
import sys
from PyQt6.QtCore import QUrl, QCoreApplication, QEvent, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlComponent
from PyQt6.QtQuick import QQuickItem, QQuickWindow
from ..packaging.frozen_resources import resource_root
from .backend import NextBackend


class ClassicHost:
    def __init__(self,backend,app):
        self.next=backend;self.app=app;self.engine=None;self.backend=None;self.window=None;self.card=None

    def open(self):
        if self.window:
            self.window.show();self.window.raise_();self.window.requestActivate();return
        if not getattr(sys,'frozen',False):
            os.environ.setdefault('LINGUANOVA_PROJECT_ROOT',str(resource_root()))
        from src.backend.app_backend import AppBackend
        from src.backend.editor_backend import EditorBackend
        self.backend=AppBackend(parent=self.app)
        self.editor=EditorBackend(self.backend,parent=self.app)
        self.engine=QQmlApplicationEngine(self.app)
        context=self.engine.rootContext()
        context.setContextProperty('appBackend',self.backend);context.setContextProperty('editorBackend',self.editor)
        context.setContextProperty('nextBackend',self.next)
        self.engine.addImportPath(str(resource_root()/'src/gui/qml'))
        self.engine.load(QUrl.fromLocalFile(str(resource_root()/'src/gui/qml/Main.qml')))
        if not self.engine.rootObjects():raise RuntimeError('Original Main.qml could not load')
        self.window=self.engine.rootObjects()[0]
        self.window.setProperty('navIndex',3)
        # The inspected base contains a Utilities ColumnLayout with this
        # localized heading. Append a NEW item via Qt's normal parent/layout
        # APIs, preserving all existing objects, methods and their order.
        title=self.backend.getTextWithDefault('ln_tools_title','Utilidades del proyecto')
        def walk(item):
            yield item
            for child in item.childItems():yield from walk(child)
        labels=[i for i in walk(self.window.contentItem()) if i.property('text')==title]
        if len(labels)!=1:raise RuntimeError('Inspected Utilities anchor was not unique; original UI left unchanged')
        column=labels[0].parentItem().parentItem().parentItem()
        if 'ColumnLayout' not in column.metaObject().className():raise RuntimeError('Inspected Utilities container differs')
        component=QQmlComponent(self.engine,QUrl.fromLocalFile(str(resource_root()/'linguanova_next/ui/ShareUtilityCard.qml')))
        self.card=component.createWithInitialProperties({'hostWindow':self.window},context)
        if not self.card:raise RuntimeError('\n'.join(e.toString() for e in component.errors()))
        self.card.setParent(column);self.card.setParentItem(column)
        self.window.show()

    def close(self):
        if self.backend and hasattr(self.backend,'shutdown'):self.backend.shutdown()


def run_gui(services,classic=False,smoke_output=None):
    os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Material')
    app=QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName('LinguaNova Next');app.setOrganizationName('LinguaNova')
    backend=NextBackend(services,parent=app)
    engine=QQmlApplicationEngine(app);engine.rootContext().setContextProperty('nextBackend',backend)
    engine.load(QUrl.fromLocalFile(str(resource_root()/'linguanova_next/ui/MainNext.qml')))
    if not engine.rootObjects():return 1
    window=engine.rootObjects()[0]
    host=ClassicHost(backend,app)
    backend.openClassicRequested.connect(host.open)
    backend.showWorkRequested.connect(lambda:(window.setProperty('pageIndex',0),window.show(),window.raise_()))
    backend.openShareRequested.connect(lambda:(window.setProperty('pageIndex',3),window.show(),window.raise_()))
    backend.openDictionaryRequested.connect(lambda:(window.setProperty('pageIndex',4),window.show(),window.raise_()))
    app.aboutToQuit.connect(backend.cancelJob);app.aboutToQuit.connect(host.close)
    if classic:window.hide();host.open()
    if smoke_output:
        from pathlib import Path
        from ..util import atomic_json
        from ..baseline import verify_baseline
        def capture_smoke():
            folder=Path(smoke_output);folder.mkdir(parents=True,exist_ok=True)
            saved=window.grabWindow().save(str(folder/'creator.png'))
            atomic_json(folder/'smoke.json',{'ui_loaded':True,'image_saved':saved,
                        'frozen':bool(getattr(sys,'frozen',False)),
                        'destinations':[x['id'] for x in services.registry.list_destinations()],
                        'baseline':verify_baseline(services.root),'inference_required':False})
            app.exit(0 if saved else 1)
        QTimer.singleShot(600,capture_smoke)
    code=app.exec()
    if host.engine:host.engine.deleteLater()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    return code
