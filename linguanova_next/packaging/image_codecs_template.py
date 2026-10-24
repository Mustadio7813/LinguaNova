"""Explicit TGA type hint for the localized assets owned by this package.

Older pygame_sdl2 versions used by Ren'Py pass '.TGA' rather than 'TGA' to
SDL2_image. TGA has no detection signature. Preserve the genuine file format
and original path, and supply the supported hint instead of renaming files.
"""
import json
from pathlib import Path
from ..util import atomic_bytes

PLAYER_FILE='zzz_linguanova_image_codecs.rpy'


def write_image_codecs(staging_game, include_game=None):
    root=Path(staging_game)
    names=set()
    for tree in [root] + ([Path(include_game)] if include_game else []):
        for path in (tree/'tl').rglob('*'):
            if path.is_file() and path.suffix.lower()=='.tga':
                relative=path.relative_to(tree).as_posix()
                names.add(relative.casefold())
                names.add('/'.join(relative.split('/')[2:]).casefold())
    if not names:return None
    literals='['+','.join('u'+json.dumps(name) for name in sorted(names))+']'
    source='''# LinguaNova: native TGA decoding compatibility for packaged images only.
init -990 python:
    import renpy.display.pgrender as _ln_codec_renderer
    _ln_codec_names=set(__NAMES__)
    def _ln_codec_wrap(previous, paths):
        def load_image(stream, filename, size=None):
            name=filename.decode('utf-8') if isinstance(filename, bytes) else filename
            if name.lower() not in paths:
                return previous(stream, filename, size=size)
            with _ln_codec_renderer.image_load_lock:
                surface=_ln_codec_renderer.pygame.image.load(stream, b'TGA')
            return _ln_codec_renderer.copy_surface_unscaled(surface)
        load_image._ln_tga_compat=True
        load_image._ln_tga_files=paths
        return load_image
    for _ln_codec_attribute in ('load_image', 'load_image_unscaled'):
        _ln_codec_previous=getattr(_ln_codec_renderer, _ln_codec_attribute)
        if getattr(_ln_codec_previous, '_ln_tga_compat', False):
            _ln_codec_previous._ln_tga_files.update(_ln_codec_names)
        else:
            setattr(_ln_codec_renderer, _ln_codec_attribute, _ln_codec_wrap(_ln_codec_previous, _ln_codec_names))
'''.replace('__NAMES__',literals)
    path=root/PLAYER_FILE
    atomic_bytes(path,source.encode('utf-8'))
    return path
