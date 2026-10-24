"""Read-only native extraction, retaining occurrences and source fingerprints."""
from pathlib import Path
import tempfile
from ..contracts.entry import Occurrence
from ..util import file_hash, digest
from ..core.text_classification import classify
from ..core.supplemental_extraction import omitted_occurrences

EXCLUDED = {'tl','saves','cache','.git','linguanova_mod_data','linguanova_next_data'}


def game_directory(path):
    path=Path(path).expanduser().resolve()
    if path.is_file() and path.suffix.lower() in ('.rpa','.rpy','.rpyc','.rpym','.rpymc'):
        for parent in path.parents:
            if parent.name.casefold()=='game':
                return parent
        raise ValueError('El archivo debe pertenecer a la carpeta game/ del proyecto')
    if (path/'game').is_dir():
        return path/'game'
    if path.name=='game' and path.is_dir():
        return path
    raise ValueError('Select the game root containing game/, or game/ itself')


def source_files(game):
    for p in sorted(Path(game).rglob('*')):
        rel=p.relative_to(game)
        if any(part in EXCLUDED or part.startswith('.') for part in rel.parts):
            continue
        if p.is_symlink():
            raise ValueError('Symbolic resources require an explicit copied project')
        if p.is_file():
            yield p


def source_manifest(game):
    # Includes source/assets and installed translations, excludes player data.
    result={}
    for p in sorted(Path(game).rglob('*')):
        rel=p.relative_to(game)
        if any(part in {'saves','cache','.git'} or part.startswith('.') for part in rel.parts):
            continue
        if p.is_symlink():
            raise ValueError('Symlinks are not part of an immutable source snapshot')
        if p.is_file():
            result[rel.as_posix()]=file_hash(p)
    return result


class ExtractionAdapter:
    def extract(self, game, mode='native'):
        if mode=='mod':
            from .mod_adapter import ModAdapter
            return ModAdapter().extract(game)
        from src.core.parser import RenPyParser
        parser=RenPyParser()
        entries,diagnostics,seen=[],[],set()
        def collect(path, values, source_hash, content=''):
            known=set()
            for v in values:
                text=v.get('text') or v.get('original_text') or ''
                if not text:
                    continue
                line=v.get('line_number',v.get('line',0)) or 0
                context=v.get('context_line','') or ' / '.join(v.get('context_path',[]))
                occurrence=Occurrence.create(path,line,text,context,classify(text,context,v.get('text_type','')),source_hash,
                                              character=v.get('character','') or '',publishable=classify(text,context,v.get('text_type',''))!='technical_uncertain')
                known.add((int(line),text))
                if occurrence.occurrence_id not in seen:
                    entries.append(occurrence)
                    seen.add(occurrence.occurrence_id)
            if content:
                for o in omitted_occurrences(path,content,source_hash,known):
                    if o.occurrence_id not in seen:
                        entries.append(o);seen.add(o.occurrence_id)
        from .resource_catalog import ResourceCatalog
        catalog=ResourceCatalog(game)
        diagnostics.extend(catalog.diagnostics)
        with tempfile.TemporaryDirectory(prefix='linguanova-source-') as td:
            for resource in catalog.scripts():
                rel=resource.path
                suffix=Path(rel).suffix.lower()
                try:
                    data=catalog.read(resource)
                    path=Path(td)/('source'+suffix)
                    path.write_bytes(data)
                    values=parser.extract_text_entries(path) if suffix in ('.rpy','.rpym') else parser.extract_from_rpyc(path)
                    content=data.decode('utf-8-sig') if suffix in ('.rpy','.rpym') else ''
                    collect(rel,values,file_hash(path),content)
                    if suffix in ('.rpyc','.rpymc') and not values:
                        diagnostics.append({'path':rel,'status':'compiled_unverified'})
                except Exception as exc:
                    diagnostics.append({'path':rel,'status':'script_unverified','cause':type(exc).__name__,'reason':str(exc)[:400]})
        return entries,diagnostics
