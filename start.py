"""One source launcher for the main app. Python 3.10+, standard library only.

No ensurepip inside the venv: recover an incomplete environment with the host
pip --python option, then the official PyPA bootstrap as a last resort.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import traceback
import urllib.request
import venv

MINIMUM_PYTHON = (3, 10)


def checked(command, log, *, cwd=None):
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace')
    with Path(log).open('a', encoding='utf-8') as stream:
        stream.write('\n$ ' + subprocess.list2cmdline([str(x) for x in command]) + '\n' + result.stdout)
    if result.returncode:
        raise RuntimeError('Falló la preparación del programa. Detalle completo: ' + str(log))
    return result


def works(python, expression):
    try:
        return subprocess.run([str(python), '-c', expression], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def ensure_pip(python, log, host=None):
    python, host = str(python), str(host or sys.executable)
    if works(python, 'import pip._internal.cli.main'):
        return
    try:
        checked([host, '-m', 'pip', '--python', python, 'install', '--upgrade', '--ignore-installed', 'pip'], log)
        return
    except RuntimeError:
        pass
    # Avoid the failing venv.ensurepip route, including on Python 3.14+.
    with tempfile.TemporaryDirectory(prefix='linguanova-pip-') as temporary:
        script = Path(temporary) / 'get-pip.py'
        with urllib.request.urlopen('https://bootstrap.pypa.io/get-pip.py', timeout=45) as response:
            script.write_bytes(response.read())
        checked([python, str(script)], log)


def prepare(root, *, environment=None, requirements=None):
    root = Path(root).resolve()
    if sys.version_info < MINIMUM_PYTHON:
        raise RuntimeError('LinguaNova requiere Python 3.10 o superior. No se exige una versión menor concreta.')
    environment = Path(environment or root / '.venv')
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    requirements = Path(requirements or root / 'requirements.txt')
    log = root / 'inicio_error.log'
    if not works(python, 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'):
        # Keep existing user environments; repair in place instead of deleting.
        print('Preparando LinguaNova con Python ' + sys.version.split()[0] + '…', flush=True)
        venv.EnvBuilder(with_pip=False).create(environment)
    ensure_pip(python, log)
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / 'linguanova-requirements.sha256'
    installed = marker.read_text().strip() if marker.is_file() else ''
    smoke = 'import PyQt6,aiohttp,requests,charset_normalizer,orjson,py3langid,openai,google.genai,unrpa,rich,yaml,fontTools,PIL,numpy,cv2,resvg_py,defusedxml,rarfile'
    if installed != fingerprint or not works(python, smoke):
        print('Preparando las dependencias de la aplicación principal. Se necesita Internet…', flush=True)
        checked([str(python), '-m', 'pip', 'install', '-r', str(requirements)], log, cwd=root)
        if not works(python, smoke):
            raise RuntimeError('Una dependencia no pudo cargarse. Consulta ' + str(log))
        marker.write_text(fingerprint, encoding='ascii')
    return python


def main(argv=None):
    root = Path(__file__).resolve().parent
    python = prepare(root)
    print('Abriendo LinguaNova: texto e imágenes en la misma ventana…', flush=True)
    return subprocess.run([str(python), str(root / 'run.py'), *(sys.argv[1:] if argv is None else argv)], cwd=root).returncode


def launch():
    try:
        return main()
    except Exception:
        log = Path(__file__).resolve().parent / 'inicio_error.log'
        with log.open('a', encoding='utf-8') as stream:
            traceback.print_exc(file=stream)
        print('No se pudo iniciar LinguaNova. Consulta: ' + str(log), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(launch())
