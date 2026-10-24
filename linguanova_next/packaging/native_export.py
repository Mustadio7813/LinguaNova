from pathlib import Path
import re
import json
from dataclasses import replace
from ..util import atomic_bytes, safe_join


def existing_strings(game,renpy_id):
    from ..adapters.resource_catalog import ResourceCatalog,compiled_nodes
    from src.core.tl_parser import TLParser
    from .output_ownership import known_owned_files
    import tempfile
    catalog=ResourceCatalog(game,include_translations=True)
    owned=known_owned_files(game)
    mapping={};warnings=[]
    # A failed archive can hide loaded translation owners. Never blindly add
    # new old/new entries when the effective game tree could not be checked.
    warnings.extend('Unverifiable archive: '+d['path'] for d in catalog.diagnostics if d['status']=='archive_unverified')
    with tempfile.TemporaryDirectory(prefix='linguanova-existing-tl-') as td:
        for resource in catalog.scripts():
            if 'game/'+resource.path in owned and resource.origin=='loose':continue
            try:
                if resource.path.lower().endswith(('.rpy','.rpym')):
                    content=catalog.read(resource).decode('utf-8-sig')
                    blocks=[]
                    pattern=r'(?m)^translate\s+(\w+)\s+strings\s*:[ \t]*(?:#[^\n]*)?\n((?:(?:[ \t]+[^\n]*|[ \t]*)\n)*)'
                    for match in re.finditer(pattern,content+'\n'):
                        if match[1]==renpy_id:blocks.append('translate '+renpy_id+' strings:\n'+match[2])
                    if not blocks:continue
                    path=Path(td)/'strings.rpy';path.write_text('\n'.join(blocks),encoding='utf-8')
                    parsed=TLParser().parse_file(str(path))
                    if not parsed:raise ValueError('No se pudieron comprobar las traducciones existentes')
                    for entry in parsed.entries:
                        if entry.entry_type=='string':mapping[entry.original_text]=entry.translated_text
                else:
                    pending=[compiled_nodes(catalog,resource)];seen=set()
                    while pending:
                        value=pending.pop()
                        if id(value) in seen:continue
                        seen.add(id(value))
                        if isinstance(value,dict):pending.extend(value.values())
                        elif isinstance(value,(list,tuple,set)):pending.extend(value)
                        elif hasattr(value,'__dict__'):
                            attrs=vars(value)
                            if attrs.get('language')==renpy_id and isinstance(attrs.get('old'),str) and isinstance(attrs.get('new'),str):
                                mapping[attrs['old']]=attrs['new']
                            pending.extend(attrs.values())
            except Exception as exc:
                # Unknown compiled scripts can contain TranslateString nodes.
                warnings.append('Unverifiable translation owner: '+resource.path+' · '+str(exc)[:200])
    return mapping,warnings


def native_export(game,stage,job,entries,results):
    existing,warnings=existing_strings(game,job.renpy_id)
    output={};owners={};updated=results.copy()
    scoped_ids={o.occurrence_id for o in entries if o.occurrence_id in results and
                results[o.occurrence_id].provenance in ('character_declaration_rule','target_dictionary_decision')}
    # Ren'Py old/new strings have a single owner per source string. Do not let
    # a contextual name decision rename a homonym elsewhere in the game.
    scoped_originals={o.original for o in entries if o.occurrence_id in scoped_ids}
    ambiguous={o.original for o in entries if o.original in scoped_originals and o.occurrence_id not in scoped_ids}
    for o in entries:
        r=results.get(o.occurrence_id)
        if not r or r.status not in ('accepted','preserved_approved'):
            continue
        if o.original in ambiguous:
            updated[o.occurrence_id]=replace(r,status='duplicate',written='',reasons=('context_collision_for_dictionary_name',))
            continue
        if warnings:
            updated[o.occurrence_id]=replace(r,status='uncertain',written='',reasons=('orphan_compiled_translations_cannot_be_checked_for_duplicates',))
            continue
        if o.original in existing:
            updated[o.occurrence_id]=replace(r,status='duplicate',written='',reasons=('existing_translation_owner',))
            continue
        if o.original in output and output[o.original]!=r.candidate:
            for oid in owners.get(o.original,[])+[o.occurrence_id]:
                updated[oid]=replace(updated[oid],status='duplicate',written='',reasons=('context_collision_for_native_string',))
            output.pop(o.original,None)
            owners[o.original]=owners.get(o.original,[])+[o.occurrence_id]
            continue
        if any(updated[oid].status=='duplicate' for oid in owners.get(o.original,[])):
            updated[o.occurrence_id]=replace(r,status='duplicate',written='',reasons=('context_collision_for_native_string',));continue
        output[o.original]=r.candidate;owners.setdefault(o.original,[]).append(o.occurrence_id)
    path=f'game/tl/{job.renpy_id}/linguanova_next_strings.rpy'
    lines=['# Generated by LinguaNova Next. Owned output; source game unchanged.']
    if output:
        lines.append(f'translate {job.renpy_id} strings:')
        for old,new in sorted(output.items()):
            lines.extend(['', '    old '+json.dumps(old,ensure_ascii=False),'    new '+json.dumps(new,ensure_ascii=False)])
    else:
        lines.extend([f'translate {job.renpy_id} python:', '    pass'])
    target=safe_join(stage,path)
    atomic_bytes(target,('\n'.join(lines)+'\n').encode())
    # Re-open actual bytes via the original parser, rather than assuming writes.
    from src.core.tl_parser import TLParser
    parsed=TLParser().parse_file(str(target))
    written={e.original_text:e.translated_text for e in parsed.entries if e.entry_type=='string'} if parsed else {}
    for old,ids in owners.items():
        for oid in ids:
            r=updated[oid]
            if r.status in ('accepted','preserved_approved'):
                updated[oid]=replace(r,written=written.get(old,''),output_path=path)
    return updated,written,warnings
