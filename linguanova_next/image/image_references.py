"""Inspect script image references as data, including expressions in RPYC AST."""
import ast
import fnmatch
from pathlib import PurePosixPath
import re
from ..adapters.resource_catalog import compiled_nodes, walk_values
from .image_formats import IMAGE_SUFFIXES

LITERALS = re.compile(r'#([^\n]*)|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)


def _literal_values(text):
    for match in LITERALS.finditer(text):
        value = match.group(0)
        if value.startswith('#'):
            continue
        try:
            yield ast.literal_eval(value)
        except (SyntaxError, ValueError):
            yield value[1:-1]


def references(catalog, scope='all', input_path=None):
    found, diagnostics = {}, []
    suffixes = {'.rpy', '.rpym'} if scope == 'rpy' else {'.rpyc', '.rpymc'} if scope == 'rpyc' else None
    for resource in catalog.scripts(suffixes):
        if scope=='rpa' and not any(resource.path in members for members in catalog.archive_members.values()):continue
        if input_path:
            if input_path.lower().endswith('.rpa'):
                if resource.path not in catalog.archive_members.get(input_path,set()):continue
            elif resource.path!=input_path:continue
        try:
            if resource.path.lower().endswith(('.rpy', '.rpym')):
                values = list(_literal_values(catalog.read(resource).decode('utf-8-sig')))
                text=catalog.read(resource).decode('utf-8-sig')
                for match in re.finditer(r'(?m)^\s*(?:show|scene)\s+([\w]+(?:[ \t]+[\w]+)*)',text):
                    words=match[1].split()
                    for stop in ('at','with','as','behind','onlayer','zorder'):
                        if stop in words:words=words[:words.index(stop)]
                    image_name=' '.join(words).casefold()
                    for name in catalog.resources:
                        if PurePosixPath(name).stem.casefold()==image_name and PurePosixPath(name).suffix.casefold() in IMAGE_SUFFIXES:
                            found.setdefault(name,set()).add(resource.path)
            else:
                values = list(walk_values(compiled_nodes(catalog, resource)))
                values += [item for value in values for item in _literal_values(value)]
            for value in values:
                if not isinstance(value, str) or PurePosixPath(value).suffix.casefold() not in IMAGE_SUFFIXES:
                    continue
                value = value.replace('\\', '/')
                if value.startswith('/') or '..' in PurePosixPath(value).parts:
                    continue
                pattern = re.sub(r'\[[^\]]+\]|%\([^)]+\)[a-z]|%[0-9]*[sd]|\{[^}]*\}', '*', value)
                candidates = [pattern] if pattern.startswith('images/') else [pattern, 'images/' + pattern]
                matches = [name for name in catalog.resources if any(fnmatch.fnmatchcase(name, p) for p in candidates)]
                for name in matches:
                    found.setdefault(name, set()).add(resource.path)
                if not matches:
                    diagnostics.append({'path': resource.path, 'reference': value, 'status': 'unresolved_image_reference'})
        except Exception as exc:
            from ..core.work_queue import CancelledJob
            if isinstance(exc, CancelledJob):raise
            diagnostics.append({'path': resource.path, 'status': 'image_references_unverified', 'reason': str(exc)[:350]})
    return {name: sorted(paths) for name, paths in found.items()}, diagnostics
