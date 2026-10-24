from pathlib import Path
import re
import shutil
from ..util import atomic_bytes, file_hash, safe_join
from ..image.font_resolver import resolve_font


def runtime_font_export(game,stage,job,texts,options,diagnostics=None):
    """Explicit licensed fallback, no automatic font replacement or downloads."""
    from fontTools.ttLib import TTFont
    references=[];warnings=[]
    for script in Path(game).rglob('*.rpy'):
        if 'tl' in script.relative_to(game).parts:
            continue
        content=script.read_text(encoding='utf-8-sig',errors='replace')
        references+=re.findall(r'(?:gui\.(?:text_font|interface_text_font)|style\.default\.font)\s*=\s*["\']([^"\']+)["\']',content)
    needed=set(c for t in texts for c in t if c.isalpha())
    for ref in references:
        p=safe_join(game,ref)
        try:
            with TTFont(p) as font:
                if all(ord(c) in (font.getBestCmap() or {}) for c in needed):
                    return {'status':'original_font_coverage_verified','font':ref,'sha256':file_hash(p),'visual_review':'pending','warnings':warnings}
        except (OSError,ValueError) as exc:
            message='No se pudo comprobar la fuente '+ref+': '+type(exc).__name__+' · '+str(exc)
            if diagnostics:message=diagnostics.record('Fuente · cobertura',exc,project=game,resource=ref,severity='warning')
            warnings.append(message)
    selected=options.get('runtime_font')
    if not needed:
        return {'status':'no_characters_required','warnings':warnings}
    if not selected:
        return {'status':'font_coverage_unverified','reason':'No proved original font or approved runtime fallback','warnings':warnings}
    path=Path(selected)
    license_path=Path(options.get('runtime_font_license',''))
    if not path.is_file() or not license_path.is_file() or not options.get('runtime_font_approved'):
        raise ValueError('Runtime font requires explicit approval and a supplied license notice')
    with TTFont(path) as font:
        missing=needed-set(chr(c) for c in (font.getBestCmap() or {}))
    if missing:
        raise ValueError('Runtime fallback lacks required glyphs')
    relative='linguanova_fonts/next_'+file_hash(path)[:16]+path.suffix.lower()
    output=Path(stage)/'game'/relative;output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,output)
    shutil.copy2(license_path,output.with_suffix('.LICENSE.txt'))
    code=f'translate {job.renpy_id} style default:\n    font "{relative}"\n'
    atomic_bytes(Path(stage)/f'game/tl/{job.renpy_id}/linguanova_next_font.rpy',code.encode())
    return {'status':'approved_fallback','font':relative,'sha256':file_hash(path),'visual_review':'pending','warnings':warnings}
