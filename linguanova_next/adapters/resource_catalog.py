"""Read-only virtual game tree: loose resources override indexed RPA members.

Archives are indexed once; only requested members are read/materialized. Scripts
are inspected as data, never imported or executed. Nothing is extracted to game/.
"""
from dataclasses import dataclass
import hashlib
import io
import pickle
import zlib
from pathlib import Path
import tempfile

from ..util import atomic_bytes, safe_relative
from ..core.work_queue import CancelledJob

SCRIPT_SUFFIXES = {'.rpy', '.rpym', '.rpyc', '.rpymc'}
FONT_SUFFIXES = {'.ttf', '.otf', '.ttc'}
EXCLUDED = {'saves', 'cache', '__pycache__', 'linguanova_mod_data',
            'linguanova_next_data', 'linguanova_next_packages'}


def _latin1_bytes(value, encoding='latin1', errors='strict'):
    if not isinstance(value,str) or encoding.lower().replace('-','') not in ('latin1','iso88591') or errors!='strict':
        raise pickle.UnpicklingError('Only Latin-1 byte reconstruction is permitted in RPA indexes')
    return value.encode('latin-1')


def _read_index(stream, header):
    from src.ui_mod.scanner import _SafeRpaUnpickler
    from src.utils.rpa_parser import _archive_index_xor
    class IndexUnpickler(_SafeRpaUnpickler):
        def find_class(self,module,name):
            if (module,name)==('_codecs','encode'):
                return _latin1_bytes
            return super().find_class(module,name)
    fields=header.decode('ascii').strip().split()
    if len(fields)<2:raise ValueError('Cabecera RPA desconocida')
    offset=int(fields[1],16)
    key=int(fields[2],16) if len(fields)>2 else 0
    stream.seek(0,2);size=stream.tell()
    if offset<len(header) or offset>=size:raise ValueError('Posición del índice RPA inválida')
    stream.seek(offset);raw=stream.read()
    for blob in ([raw,_archive_index_xor(raw,key)] if key else [raw]):
        for compressed in (True,False):
            try:
                data=zlib.decompress(blob) if compressed else blob
                return IndexUnpickler(io.BytesIO(data),encoding='latin1').load(),key
            except (ValueError,EOFError,pickle.UnpicklingError,zlib.error):
                continue
    raise ValueError('No se pudo leer el índice RPA')


@dataclass(frozen=True)
class Resource:
    path: str
    container: str
    chunks: tuple = ()
    key: int = 0
    origin: str = 'loose'


class ResourceCatalog:
    def __init__(self, game, workspace=None, include_translations=False, cancelled=None):
        self.game = Path(game).resolve()
        self.workspace = Path(workspace) if workspace else None
        self.cancelled = cancelled
        self.include_translations = include_translations
        self.resources = {}
        self.archive_members = {}
        self.diagnostics = []
        self._scan()

    def check(self):
        if self.cancelled is not None and self.cancelled.is_set():
            raise CancelledJob('Inventario de recursos cancelado')

    def _admit(self, name):
        safe_relative(name)
        parts = Path(name).parts
        return not any(p.startswith('.') or p.casefold() in EXCLUDED for p in parts) and (
            self.include_translations or parts[0].casefold() != 'tl')

    def _scan(self):
        loose = []
        archives = []
        for path in sorted(self.game.rglob('*')):
            self.check()
            rel = path.relative_to(self.game).as_posix()
            if not self._admit(rel):
                continue
            if path.is_symlink():
                raise ValueError('Recurso simbólico no admitido: ' + rel)
            if not path.is_file():
                continue
            (archives if path.suffix.casefold() == '.rpa' else loose).append((rel, path))
        # Ren'Py's default archive order is reverse alphabetical. setdefault
        # retains that winner. A loose file always wins over an archive member.
        for rel, archive in reversed(archives):
            try:
                self.archive_members[rel]=set()
                with archive.open('rb') as stream:
                    header = stream.readline(256)
                    if not header.endswith(b'\n'):
                        raise ValueError('Cabecera RPA inválida')
                    index, key = _read_index(stream, header)
                if not isinstance(index, dict):
                    raise ValueError('Índice RPA inválido')
                for raw_name, chunks in index.items():
                    self.check()
                    name = raw_name.decode('utf-8') if isinstance(raw_name, bytes) else raw_name
                    if not isinstance(name, str):
                        raise ValueError('Nombre de recurso RPA inválido')
                    name = name.replace('\\', '/')
                    try:
                        if not self._admit(name):
                            continue
                        self.archive_members[rel].add(name)
                        if not isinstance(chunks, (list, tuple)) or not chunks:
                            raise ValueError('Recurso RPA sin fragmentos')
                        self.resources.setdefault(name, Resource(name, str(archive), tuple(chunks), key, 'rpa'))
                    except ValueError as exc:
                        self.diagnostics.append({'path': rel, 'resource': name,
                            'status': 'archive_member_rejected', 'reason': str(exc)})
            except CancelledJob:
                raise
            except Exception as exc:
                self.diagnostics.append({'path': rel, 'status': 'archive_unverified',
                                         'cause': type(exc).__name__, 'reason': str(exc)[:400]})
        for rel, path in loose:
            self.resources[rel] = Resource(rel, str(path))

    def read(self, resource, max_bytes=1024 * 1024 * 1024):
        self.check()
        item = self.resources[resource] if isinstance(resource, str) else resource
        if item.origin == 'loose':
            if Path(item.container).stat().st_size > max_bytes:
                raise ValueError('Recurso demasiado grande: ' + item.path)
            return Path(item.container).read_bytes()
        parts = []
        total = 0
        archive_size = Path(item.container).stat().st_size
        with open(item.container, 'rb') as stream:
            for chunk in item.chunks:
                self.check()
                if not isinstance(chunk, (tuple, list)) or len(chunk) < 2:
                    raise ValueError('Fragmento RPA inválido: ' + item.path)
                offset, length = int(chunk[0]) ^ item.key, int(chunk[1]) ^ item.key
                prefix = chunk[2] if len(chunk) > 2 else b''
                if isinstance(prefix, str):
                    prefix = prefix.encode('latin-1')
                if not isinstance(prefix, bytes):
                    raise ValueError('Prefijo RPA inválido')
                # The RPA length counts disk bytes; a prefix is EXTRA data.
                disk_length = length
                total += length + len(prefix)
                if min(offset, disk_length) < 0 or offset + disk_length > archive_size or total > max_bytes:
                    raise ValueError('Tamaño/posición RPA inválidos: ' + item.path)
                stream.seek(offset)
                data = stream.read(disk_length)
                if len(data) != disk_length:
                    raise ValueError('Recurso RPA truncado: ' + item.path)
                parts.append(prefix + data)
        return b''.join(parts)

    def materialize(self, resource, workspace=None):
        item = self.resources[resource] if isinstance(resource, str) else resource
        if item.origin == 'loose':
            return Path(item.container)
        root = Path(workspace or self.workspace or '')
        if not workspace and self.workspace is None:
            raise ValueError('La extracción necesita una carpeta privada de trabajo')
        data = self.read(item)
        path = root / hashlib.sha256(data).hexdigest() / Path(item.path).name
        if not path.is_file() or path.read_bytes() != data:
            atomic_bytes(path, data)
        return path

    def scripts(self, suffixes=None):
        suffixes = set(suffixes or SCRIPT_SUFFIXES)
        for name, resource in sorted(self.resources.items()):
            suffix = Path(name).suffix.casefold()
            if suffix not in suffixes or Path(name).name.startswith('zzz_linguanova'):
                continue
            if suffix in ('.rpyc', '.rpymc') and name[:-1] in self.resources and Path(name[:-1]).suffix in suffixes:
                continue
            yield resource


def walk_values(value, limit=1000000):
    """Walk already decoded RPYC data with cycle/node limits; no eval/properties."""
    pending = [value]
    seen = set()
    count = 0
    while pending:
        current = pending.pop()
        count += 1
        if count > limit:
            raise ValueError('AST demasiado grande para el inventario de recursos')
        if isinstance(current, str):
            yield current
            continue
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, dict):
            pending.extend(current.values())
        elif isinstance(current, (list, tuple, set)):
            pending.extend(current)
        elif hasattr(current, '__dict__'):
            pending.extend(vars(current).values())


def compiled_nodes(catalog, resource):
    from src.core.rpyc_reader import read_rpyc_file
    with tempfile.TemporaryDirectory(prefix='linguanova-rpyc-read-') as temp:
        path = Path(temp) / ('source' + Path(resource.path).suffix.lower())
        path.write_bytes(catalog.read(resource, max_bytes=128 * 1024 * 1024))
        return read_rpyc_file(path)
