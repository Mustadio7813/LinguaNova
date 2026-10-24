"""Build the single Windows application with its OCR runtime, Python 3.10+."""
from pathlib import Path
import os
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from start import prepare,checked


def main():
    if os.name!='nt':raise RuntimeError('La distribución Windows debe compilarse en Windows.')
    if sys.version_info<(3,10):raise RuntimeError('Se necesita Python 3.10 o superior.')
    if struct.calcsize('P')*8!=64:raise RuntimeError('Para compilar esta distribución Windows se necesita Python de 64 bits.')
    python=prepare(ROOT)
    log=ROOT/'compilacion_error.log'
    checked([str(python),'-m','pip','install','PyInstaller>=6.12,<7'],log,cwd=ROOT)
    checked([str(python),str(ROOT/'scripts/prepare_ocr_bundle.py')],log,cwd=ROOT)
    checked([str(python),'-m','PyInstaller','--noconfirm','--clean',str(ROOT/'LinguaNova.spec')],log,cwd=ROOT)
    print('Distribuye TODA la carpeta dist/LinguaNova. El destinatario no necesita Python ni pip.')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)
