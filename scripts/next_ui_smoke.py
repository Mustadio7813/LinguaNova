"""Headless Qt source smoke check; screenshots are creator UI evidence only."""
from pathlib import Path
import os,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ.setdefault('QSG_RHI_BACKEND','software');os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Material')
os.environ.setdefault('QML_DISABLE_DISK_CACHE','1')
# Isolate smoke-test settings without changing protected sources.
TEST_DATA=Path(tempfile.mkdtemp(prefix='linguanova-ui-'))
os.environ['XDG_DATA_HOME']=str(TEST_DATA);os.environ['LINGUANOVA_PROJECT_ROOT']=str(ROOT)
os.environ['LINGUANOVA_NEXT_DATA']=str(TEST_DATA/'next')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer,QUrl,QCoreApplication,QEvent
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtQuick import QQuickWindow
from linguanova_next.bootstrap import Services
from linguanova_next.ui.backend import NextBackend
from linguanova_next.ui.application import ClassicHost


def main():
    app=QApplication([]);backend=NextBackend(Services(),parent=app);engine=QQmlApplicationEngine(app)
    engine.rootContext().setContextProperty('nextBackend',backend)
    engine.load(QUrl.fromLocalFile(str(ROOT/'linguanova_next/ui/MainNext.qml')))
    if not engine.rootObjects():raise RuntimeError('New QML failed to load')
    window=engine.rootObjects()[0];host=ClassicHost(backend,app);state={'error':None}
    def fail(exc):state['error']=str(exc);app.quit()
    def capture():
        try:
            window.grabWindow().save(str(ROOT/'next_evidence/creator_ui.png'))
            window.setProperty('pageIndex',3)
            QTimer.singleShot(250,capture_share)
        except Exception as exc:fail(exc)
    def capture_share():
        try:
            def walk(item):
                yield item
                for child in item.childItems():yield from walk(child)
            boxes=[item for item in walk(window.contentItem()) if item.objectName()=='shareArchiveFormat']
            assert len(boxes)==1, 'Archive format selector must be present'
            boxes[0].setProperty('currentIndex',1)
            state['format_box']=boxes[0]
            QTimer.singleShot(200,capture_rar)
        except Exception as exc:fail(exc)
    def capture_rar():
        try:
            item=state['format_box'].parentItem()
            while item:
                if item.property('contentY') is not None:
                    item.setProperty('contentY',max(0,item.property('contentHeight')-item.height()));break
                item=item.parentItem()
            QTimer.singleShot(150,save_rar)
        except Exception as exc:fail(exc)
    def save_rar():
        try:
            window.grabWindow().save(str(ROOT/'next_evidence/share_rar_option.png'))
            print('RAR format selector rendered; availability explanation visible')
            host.open()
            print('ADDED CARD',host.card.objectName(),host.card.parentItem().metaObject().className())
            assert host.card.parentItem().childItems()[-1]==host.card
            QTimer.singleShot(400,scroll)
        except Exception as exc:fail(exc)
    def scroll():
        try:
            item=host.card.parentItem()
            while item:
                if item.property('contentY') is not None:
                    item.setProperty('contentY',max(0,item.property('contentHeight')-item.height()));break
                item=item.parentItem()
            QTimer.singleShot(200,finish)
        except Exception as exc:fail(exc)
    def finish():
        try:
            host.window.grabWindow().save(str(ROOT/'next_evidence/classic_utilities_added_card.png'))
            print('QML source and extended classic loaded; MOD UI patch loaded')
        finally:app.quit()
    QTimer.singleShot(500,capture);app.exec();host.close()
    if host.engine:host.engine.deleteLater()
    engine.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    if state['error']:raise RuntimeError(state['error'])


if __name__=='__main__':main()
