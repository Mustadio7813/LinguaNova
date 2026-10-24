# -*- coding: utf-8 -*-
"""
Test to ensure Main.qml and all QML components load without syntax or binding errors.
"""
import os
import sys
import pytest
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine


def test_qml_loads_cleanly():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])

    from src.backend.app_backend import AppBackend
    backend = AppBackend(parent=app)
    backend.config.translation_settings.mod_target_language = "spanish"
    backend.config.translation_settings.mod_selected_engine = "google"

    engine = QQmlApplicationEngine(app)
    engine.rootContext().setContextProperty("appBackend", backend)
    from src.backend.editor_backend import EditorBackend
    # Parented so Python keeps it alive; an unowned object is collected at once
    # and the editor page would bind against null.
    editor_backend = EditorBackend(backend, parent=app)
    engine.rootContext().setContextProperty("editorBackend", editor_backend)

    qml_root = os.path.abspath("src/gui/qml")
    engine.addImportPath(qml_root)
    qml_path = os.path.join(qml_root, "Main.qml")

    errors = []
    def on_warnings(warnings):
        for w in warnings:
            errors.append(w.toString())

    engine.warnings.connect(on_warnings)
    engine.load(QUrl.fromLocalFile(qml_path))
    assert len(engine.rootObjects()) > 0, f"QML failed to load: {errors}"
    script_errors = [e for e in errors if "TypeError" in e or "ReferenceError" in e]
    assert not script_errors, "QML script errors:\n" + "\n".join(script_errors)
    root = engine.rootObjects()[0]
    target_combo = root.findChild(QObject, "modTargetCombo")
    engine_combo = root.findChild(QObject, "modEngineCombo")
    assert target_combo is not None and target_combo.property("currentValue") == "spanish"
    assert engine_combo is not None and engine_combo.property("currentValue") == "google"


def test_no_helper_receives_ui_trigger_as_argument():
    """
    `appBackend.uiTrigger` is a bool used only to re-evaluate bindings via the
    comma operator (`text: appBackend.uiTrigger, helper(...)`). Passing it as a
    function argument (`helper(appBackend.uiTrigger, ...)`) hands `true` to string
    helpers such as cleanModalTitle/cleanTitle and raises
    "TypeError: Property 'replace' of object true is not a function" at runtime.
    """
    import glob
    import re

    qml_root = os.path.join(os.path.dirname(__file__), "..", "src", "gui", "qml")
    offenders = []
    pattern = re.compile(r"\b([A-Za-z_][\w.]*)\(\s*appBackend\.uiTrigger\s*,")
    for path in glob.glob(os.path.join(qml_root, "**", "*.qml"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                for m in pattern.finditer(line):
                    # `(appBackend.uiTrigger, x)` grouping has no callee name before "("
                    if m.group(1):
                        offenders.append(f"{os.path.relpath(path, qml_root)}:{lineno}: {line.strip()[:120]}")
    assert not offenders, "uiTrigger passed as a function argument:\n" + "\n".join(offenders)


def test_removed_engines_have_no_ui():
    """Local LLM, Custom endpoint and the Hy-MT2 profile were removed (2026-10-17)."""
    qml = os.path.join(os.path.dirname(__file__), "..", "src", "gui", "qml", "Main.qml")
    with open(qml, encoding="utf-8") as fh:
        content = fh.read()
    for needle in ('"local_llm"', '"custom"', "localLlm", "customEndpoint", "hyMt2", "aiModelProfile",
                   "gguf", "llama", "localServer"):
        assert needle not in content, needle
