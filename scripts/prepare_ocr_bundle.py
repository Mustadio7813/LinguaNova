"""Prepare the Windows OCR runtime for the main PyInstaller distribution.

Copy the complete installed runtime (including dependency DLLs, data, notices)
into components/tesseract. No interpreter is needed by the receiving user.
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def prepare(source=None):
    if sys.platform != 'win32':
        raise RuntimeError('Prepare a Windows distribution on Windows, using its Tesseract build.')
    choices = [Path(source)] if source else []
    if shutil.which('tesseract'):
        choices.append(Path(shutil.which('tesseract')).parent)
    choices += [Path(os.environ[k]) / 'Tesseract-OCR' for k in ('ProgramFiles', 'ProgramFiles(x86)') if os.environ.get(k)]
    directory = next((p for p in choices if (p / 'tesseract.exe').is_file()), None)
    if directory is None:
        raise RuntimeError('Instala Tesseract con el botón Instalar OCR del programa o indica --source SU_CARPETA. Después vuelve a compilar.')
    target = ROOT / 'components/tesseract'
    if directory.resolve() != target.resolve():
        shutil.copytree(directory, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('unins*', 'uninstall*'))
    executable = target / 'tesseract.exe'
    completed = subprocess.run([str(executable), '--list-langs'], capture_output=True, text=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=20)
    if completed.returncode or not (target / 'tessdata/eng.traineddata').is_file():
        raise RuntimeError('El OCR copiado no funciona o falta el modelo eng: ' + completed.stdout + completed.stderr)
    print('OCR completo preparado: ' + str(target))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source')
    prepare(parser.parse_args().source)
