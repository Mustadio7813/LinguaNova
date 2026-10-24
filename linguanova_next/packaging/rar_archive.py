"""Optional genuine RAR creation/reading on the creator's computer only.

RAR/WinRAR is discovered, never downloaded or redistributed by this module.
The player receives final files and only needs an archive extractor.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from ..util import atomic_bytes, safe_join, safe_relative


def rar_status():
    explicit = os.environ.get('LINGUANOVA_NEXT_RAR_EXECUTABLE')
    candidates = [explicit] if explicit else [shutil.which('rar'), shutil.which('Rar.exe')]
    if not explicit:
        for name in ('ProgramFiles', 'ProgramFiles(x86)'):
            if os.environ.get(name):
                candidates.append(str(Path(os.environ[name]) / 'WinRAR/Rar.exe'))
    for value in candidates:
        if value and Path(value).is_file() and (os.name == 'nt' or os.access(value, os.X_OK)):
            return {'available': True, 'executable': str(Path(value).resolve()),
                    'reason': 'RAR disponible en el equipo creador'}
    return {'available': False, 'executable': '',
            'reason': 'RAR requiere RAR/WinRAR en el equipo creador. Usa ZIP o configura LINGUANOVA_NEXT_RAR_EXECUTABLE con la ruta de Rar.exe.'}


def _run(arguments, cwd=None):
    status = rar_status()
    if not status['available']:
        raise ValueError(status['reason'])
    env = os.environ.copy()
    env.pop('RAR', None)
    if getattr(__import__('sys'), 'frozen', False) and os.name != 'nt':
        if 'LD_LIBRARY_PATH_ORIG' in env:
            env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
        else:
            env.pop('LD_LIBRARY_PATH', None)
    result = subprocess.run([status['executable'], *arguments], cwd=cwd, env=env,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=300,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('RAR no completó la operación; código ' + str(result.returncode) + '. No se publicó el archivo nuevo.')
    return result.stdout


class RarArchive:
    """Read exact regular members without extracting paths onto the filesystem."""
    def __init__(self, path):
        import rarfile
        self.path = Path(path).resolve()
        self.archive = rarfile.RarFile(self.path)
        for info in self.archive.infolist():
            safe_relative(info.filename)
            if (not info.is_file() or info.is_symlink() or info.needs_password()
                    or getattr(info, 'file_redir', None)):
                self.close()
                raise ValueError('El paquete RAR solo admite archivos normales sin contraseña ni enlaces')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.archive.close()

    def namelist(self):
        return self.archive.namelist()

    def read(self, name):
        safe_relative(name)
        if name not in self.namelist():
            raise KeyError(name)
        # 'p' sends the exact member bytes to stdout; -inul suppresses banners.
        return _run(['p', '-cfg-', '-inul', '-p-', str(self.path), name])


def open_player_archive(path):
    if Path(path).suffix.lower() == '.rar':
        return RarArchive(path)
    return zipfile.ZipFile(path)


def zip_to_rar(source, destination):
    """Compress an already validated ZIP payload and verify every RAR byte."""
    from .share_package_validator import validate_zip, validate_archive
    status = rar_status()
    if not status['available']:
        raise ValueError(status['reason'])
    check = validate_zip(source)
    if not check['valid']:
        raise ValueError(check['errors'])
    destination = Path(destination).resolve()
    if destination.suffix.lower() != '.rar':
        raise ValueError('Choose a .rar output path')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='linguanova-rar-', dir=destination.parent) as temp:
        folder = Path(temp)
        payload = folder / 'payload'
        payload.mkdir()
        with zipfile.ZipFile(source) as archive:
            names = sorted(archive.namelist())
            for name in names:
                if '\n' in name or '\r' in name:
                    raise ValueError('RAR file lists cannot contain newline characters')
                path = safe_join(payload, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
                path.chmod(0o644)
                os.utime(path, (1767225600, 1767225600))
            # Unicode list is outside the payload; exact paths, no recursive glob.
            listing = folder / 'members.txt'
            listing.write_text('\n'.join(names) + '\n', encoding='utf-8')
            output = folder / 'package.rar'
            _run(['a', '-cfg-', '-ma5', '-m3', '-mt1', '-s-', '-ts-', '-r-',
                  '-ed', '-scfl', '-idq', str(output), '@' + str(listing)], cwd=payload)
            _run(['t', '-cfg-', '-inul', '-p-', str(output)])
            verdict = validate_archive(output)
            if not verdict['valid']:
                raise ValueError(verdict['errors'])
            with RarArchive(output) as rar:
                if set(rar.namelist()) != set(names):
                    raise ValueError('RAR changed the copyable file structure')
                for name in names:
                    if rar.read(name) != archive.read(name):
                        raise ValueError('RAR payload differs from validated ZIP: ' + name)
        atomic_bytes(destination, output.read_bytes())
    return verdict | {'path': str(destination), 'bytes': destination.stat().st_size,
                      'format': 'rar', 'content_verified_against_zip': True,
                      'reproducibility': 'External RAR version/platform dependent; payload hashes verified'}
