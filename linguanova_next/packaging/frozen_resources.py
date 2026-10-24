"""Read-only bundled assets and persistent creator-owned paths are distinct."""
import os
import sys
from pathlib import Path


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))


def data_root():
    override = os.environ.get('LINGUANOVA_NEXT_DATA')
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData/Local'))/'LinguaNova/next'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'LinguaNova/next'


def model_root():
    return data_root()/'models'
