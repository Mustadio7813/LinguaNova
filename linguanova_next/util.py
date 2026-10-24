"""Deterministic identities, safe relative paths and atomic durable writes."""
import dataclasses
import hashlib
import json
import os
import tempfile
from pathlib import Path, PurePosixPath


def jsonable(value):
    if dataclasses.is_dataclass(value):
        return {f.name: jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return value


def canonical(value):
    return json.dumps(jsonable(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe_relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or any(ord(c)<32 for c in value):
        raise ValueError('Invalid relative path')
    path = PurePosixPath(value)
    reserved={'CON','PRN','AUX','NUL'} | {'COM'+str(i) for i in range(1,10)} | {'LPT'+str(i) for i in range(1,10)}
    if any(part.rstrip(' .')!=part or part.split('.')[0].upper() in reserved or any(c in part for c in '<>\"|?*') for part in path.parts):
        raise ValueError('Path cannot be copied safely on Windows: '+value)
    if path.is_absolute() or '..' in path.parts or str(path) != value or value.endswith('/'):
        raise ValueError('Non-canonical relative path: ' + value)
    return path


def safe_join(root, relative):
    rel = safe_relative(relative)
    root = Path(root).resolve()
    path = root.joinpath(*rel.parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path escapes destination')
    return path


def atomic_bytes(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(jsonable(value), ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode())


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        return default
