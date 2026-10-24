import hashlib
import io
from pathlib import Path
from ..adapters.resource_catalog import ResourceCatalog, FONT_SUFFIXES


def inventory_fonts(game, catalog=None, workspace=None):
    from fontTools.ttLib import TTFont, TTCollection
    catalog = catalog or ResourceCatalog(game, workspace)
    result = []
    for resource in catalog.resources.values():
        if Path(resource.path).suffix.lower() not in FONT_SUFFIXES:
            continue
        try:
            data = catalog.read(resource)
            if Path(resource.path).suffix.lower() == '.ttc':
                font = TTFont(io.BytesIO(data), fontNumber=0)
            else:
                font = TTFont(io.BytesIO(data))
            with font:
                names = font['name']
                local = str(catalog.materialize(resource, workspace)) if resource.origin == 'loose' or workspace or catalog.workspace else ''
                result.append({'path': resource.path, 'local_path': local, 'sha256': hashlib.sha256(data).hexdigest(),
                    'family': names.getDebugName(1) or Path(resource.path).stem, 'variant': names.getDebugName(2) or '',
                    'glyphs': len(font.getBestCmap() or {}), 'license_notice': names.getDebugName(13) or '',
                    'origin': resource.origin, 'identification': 'font metadata; image typeface identity not proven'})
        except Exception as exc:
            result.append({'path': resource.path, 'status': 'unreadable', 'cause': type(exc).__name__})
    return result
