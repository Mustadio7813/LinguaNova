"""Check live language labels and readable MOD controls in the actual QML UI.

Requires the desktop dependencies. Uses isolated settings and an offscreen Qt
window; changes all five interface languages without restarting the application.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def verify(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="linguanova-ui-") as settings:
        os.environ.update(
            QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
            QML_DISABLE_DISK_CACHE="1", LINGUANOVA_PROJECT_ROOT=str(ROOT),
            XDG_DATA_HOME=settings,
        )
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtQuick import QQuickItem
        from PyQt6.QtCore import QCoreApplication, QEvent, QUrl
        from PyQt6.QtQml import QQmlApplicationEngine, QQmlExpression, qmlContext
        from PyQt6.QtTest import QTest
        from src.backend.app_backend import AppBackend
        from src.backend.editor_backend import EditorBackend

        app = QApplication([])
        backend = AppBackend(parent=app)
        backend.setUILanguage("es")
        editor = EditorBackend(backend, parent=app)
        engine = QQmlApplicationEngine(app)
        engine.rootContext().setContextProperty("appBackend", backend)
        engine.rootContext().setContextProperty("editorBackend", editor)
        engine.addImportPath(str(ROOT / "src/gui/qml"))
        warnings = []
        engine.warnings.connect(lambda values: warnings.extend(v.toString() for v in values))
        engine.load(QUrl.fromLocalFile(str(ROOT / "src/gui/qml/Main.qml")))
        assert engine.rootObjects(), warnings
        window = engine.rootObjects()[0]
        window.setWidth(1366)
        window.setHeight(768)
        window.show()

        def evaluate(scope, source):
            expression = QQmlExpression(qmlContext(scope), scope, source)
            result = expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            return result

        def walk(item):
            yield item
            for child in item.childItems():
                yield from walk(child)

        def visible_labels(size):
            return {
                item.property("text") for item in walk(window.contentItem())
                if item.isVisible() and item.property("text")
                and item.property("font") is not None
                and item.property("font").pixelSize() == size
            }

        native = {"spanish": "Español", "english": "English", "portuguese": "Português",
                  "french": "Français", "russian": "Русский"}
        report = {"without_restart": True, "popups": {}, "warnings": warnings}
        try:
            QTest.qWait(300)
            target = window.findChild(QQuickItem, "modTargetCombo")
            motor = window.findChild(QQuickItem, "modEngineCombo")
            assert target.height() >= 44 and motor.height() >= 44
            report["mod_control_height"] = [target.height(), motor.height()]
            for popup in ("sourceLangPopup", "targetLangPopup"):
                window.setProperty("navIndex", 0)
                evaluate(window, popup + ".open()")
                report["popups"][popup] = {}
                for ui in ("es", "en", "fr", "pt", "ru"):
                    backend.setUILanguage(ui)
                    QTest.qWait(150)
                    assert evaluate(window, popup + ".x >= 0 && " + popup + ".x + " + popup + ".width <= root.width && " + popup + ".y >= 0 && " + popup + ".y + " + popup + ".height <= root.height"), (popup, ui, "popup outside window")
                    expected = json.loads((ROOT / "locales" / (ui + ".json")).read_text(encoding="utf-8"))["language_names"]
                    assert set(expected.values()) <= visible_labels(9), (popup, ui, visible_labels(9))
                    assert set(native.values()) <= visible_labels(10), (popup, ui, visible_labels(10))
                    model = target.property("model")
                    if hasattr(model, "toVariant"):
                        model = model.toVariant()
                    assert {v["name"] for v in model} == {v[:1].upper() + v[1:] for v in expected.values()}, (ui, model)
                    report["popups"][popup][ui] = expected
                    if popup == "targetLangPopup" and ui in ("es", "en"):
                        assert window.grabWindow().save(str(output / ("languages_" + ui + ".png")))
                evaluate(window, popup + ".close()")
            backend.setUILanguage("es")
            window.setProperty("navIndex", 6)
            QTest.qWait(150)
            # Scroll the MOD controls into view, then inspect their real popup.
            from PyQt6.QtCore import QPointF
            parent = target.parentItem()
            while parent:
                if parent.property("contentY") is not None and parent.property("contentHeight") is not None:
                    point = target.mapToItem(parent, QPointF(0, 0))
                    parent.setProperty("contentY", max(0, min(parent.property("contentHeight") - parent.height(), parent.property("contentY") + point.y() - 180)))
                    break
                parent = parent.parentItem()
            evaluate(target, "popup.open()")
            QTest.qWait(150)
            assert window.grabWindow().save(str(output / "mod_es.png"))
            # Existing Material dialogs report implicitWidth loops when changing
            # UI language, including in the unmodified supplied application.
            # Preserve those diagnostics; fail on any other QML warning.
            unexpected = [w for w in warnings if not (
                'QML Dialog: Binding loop detected for property "implicitWidth"' in w
                and ('/Main.qml:' in w or '/components/EditorPage.qml:' in w))]
            assert not unexpected, unexpected
            report["unexpected_warnings"] = unexpected
            report["success"] = True
        finally:
            backend.shutdown()
            engine.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        (output / "ui.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="ocr_evidence/ui")
    result = verify(parser.parse_args().output)
    print(json.dumps({"success": result["success"], "popups": 2, "interface_languages": 5,
                      "without_restart": result["without_restart"],
                      "preexisting_material_warnings": len(result["warnings"]),
                      "unexpected_warnings": result["unexpected_warnings"]}, indent=2))
