from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from ..adapters.resource_catalog import ResourceCatalog
from ..util import digest
from .image_formats import IMAGE_SUFFIXES, decode
from .image_references import references


@dataclass(frozen=True)
class ImageResource:
    resource_id: str
    path: str
    image_hash: str
    format: str
    width: int
    height: int
    transparency: bool
    frames: int
    state: str
    group: str
    status: str
    reason: str = ''
    origin: str = 'loose'
    container: str = ''
    references: tuple = ()


def inventory(game, catalog=None, scope='all', diagnostics=None, input_path=None):
    if scope not in ('all', 'rpa', 'rpy', 'rpyc'):
        raise ValueError('Origen de imágenes desconocido: ' + scope)
    catalog = catalog or ResourceCatalog(game)
    refs, issues = references(catalog, scope, input_path)
    if diagnostics is not None:
        diagnostics.extend(catalog.diagnostics + issues)
    result = []
    for path, item in sorted(catalog.resources.items()):
        if Path(path).suffix.casefold() not in IMAGE_SUFFIXES:
            continue
        if input_path and input_path.lower().endswith('.rpa'):
            if path not in catalog.archive_members.get(input_path,set()) and path not in refs:continue
        elif input_path and path not in refs:continue
        packed=any(path in members for members in catalog.archive_members.values())
        if scope == 'rpa' and not packed and path not in refs:
            continue
        if scope in ('rpy', 'rpyc') and path not in refs:
            continue
        match = re.search(r'(?:^|[_\-.])(idle|normal|hover|selected|disabled)(?:[_\-.]|$)', Path(path).name, re.I)
        state = match.group(1).lower() if match else 'unclassified'
        group = re.sub(r'(?i)(idle|normal|hover|selected|disabled)', '{state}', path)
        sha = ''
        try:
            data = catalog.read(item)
            sha = hashlib.sha256(data).hexdigest()
            decoded = decode(data, Path(path).suffix)
            first = decoded.frames[0]
            result.append(ImageResource(digest(path), path, sha, decoded.format, first.width, first.height,
                any(frame.getchannel('A').getextrema()[0] < 255 for frame in decoded.frames), len(decoded.frames),
                state, group, 'inventoried', origin=item.origin, container=item.container,
                references=tuple(refs.get(path, []))))
        except Exception as exc:
            from ..core.work_queue import CancelledJob
            if isinstance(exc, CancelledJob):raise
            result.append(ImageResource(digest(path), path, sha, '', 0, 0, False, 0, state, group,
                'unsupported_format', str(exc)[:350], item.origin, item.container, tuple(refs.get(path, []))))
    return result
