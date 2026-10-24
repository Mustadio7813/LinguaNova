from pathlib import Path
from ..util import file_hash, safe_join


def resolve_font(game, profile, text):
    from fontTools.ttLib import TTFont
    path=Path(profile.font_path)
    if not path.is_absolute():
        path=safe_join(game,profile.font_path)
    if not path.is_file() or file_hash(path)!=profile.font_hash:
        raise ValueError('Font identity/hash mismatch')
    with TTFont(path, **({'fontNumber':0} if path.suffix.lower()=='.ttc' else {})) as font:
        cmap=font.getBestCmap() or {}
        missing=sorted(set(c for c in text if not c.isspace() and ord(c) not in cmap))
    if missing:
        raise ValueError('Missing target glyphs: '+''.join(missing))
    return path
