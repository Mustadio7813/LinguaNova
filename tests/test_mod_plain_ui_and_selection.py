# -*- coding: utf-8 -*-
from pathlib import Path
import json


def test_mod_header_has_own_title_and_hint():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert 'if (index === 6) return appBackend.getTextWithDefault("mod_header_title", "MOD").toUpperCase()' in qml
    assert '"mod_header_hint"' in qml


def test_mod_has_independent_temporary_game_path():
    backend = Path("src/backend/app_backend.py").read_text(encoding="utf-8")
    assert "self._mod_project_path: str = \"\"" in backend
    assert "def setModProjectPath" in backend
    assert '"project_path": self._mod_project_path' in backend
    assert "last_input_directory" not in backend.split("def setModProjectPath", 1)[1].split("def _translation_job_snapshot", 1)[0]


def test_mod_qml_can_select_file_or_folder_and_shows_read_only_path():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert "id: modGameFileDialog" in qml
    assert "id: modGameFolderDialog" in qml
    assert "appBackend.setModProjectPath(raw)" in qml
    assert "text: appBackend.modProjectPath" in qml
    path_pos = qml.index("id: modProjectPathField")
    assert "readOnly: true" in qml[path_pos:path_pos + 800]


def test_generated_mod_name_is_clear():
    generator = Path("src/ui_mod/generator.py").read_text(encoding="utf-8")
    assert 'f"linguanova_mod_{game_name}_multilang.rpy"' in generator
    assert 'f"trampa_{game_name}_{suffix}.rpy"' not in generator


def test_spanish_mod_text_is_plain_language():
    data = json.loads(Path("locales/es.json").read_text(encoding="utf-8"))
    keys = [k for k in data if k.startswith("mod_")]
    joined = "\n".join(str(data[k]) for k in keys).lower()
    for banned in ("pipeline", "parser", "hook", "callback", "runtime", "trampa_"):
        assert banned not in joined
