import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import pytest
from linguanova_next.bootstrap import Services
from support import copy_fixture


@pytest.fixture
def services(tmp_path):
    return Services(data=tmp_path/'creator_state')


@pytest.fixture
def project(tmp_path):
    return copy_fixture(tmp_path)


@pytest.fixture
def recipe():
    from linguanova_next.util import load_json
    return load_json(Path(__file__).resolve().parents[2]/'linguanova_next/data/game_ui_profiles/controlled_fixture.json')
