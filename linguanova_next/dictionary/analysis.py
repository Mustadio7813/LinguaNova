"""Conservative dictionary analysis. No provider calls and no source writes."""
from collections import Counter
from pathlib import Path
import re
from ..adapters.extraction_adapter import ExtractionAdapter, source_files
from ..contracts.entry import Occurrence
from ..core.work_queue import CancelledJob
from ..util import digest, file_hash, jsonable

ANALYZER_VERSION = 'project-dictionary-2-resources'


def check_cancelled(cancelled):
    if cancelled is not None and cancelled.is_set():
        raise CancelledJob('Preparación del Diccionario cancelada')


def inventory_manifest(game, cancelled=None):
    result = {}
    for path in source_files(game):
        check_cancelled(cancelled)
        if path.name.startswith('zzz_linguanova') or 'linguanova_next_packages' in path.relative_to(game).parts:
            continue
        result[path.relative_to(game).as_posix()] = file_hash(path)
    return result


def analyze(game, mode, cancelled=None, progress=None):
    from src.core.parser import _CHARACTER_NAME_ARG_RE, _PLAIN_NAME_RE
    progress = progress or (lambda text: None)
    declarations = {}
    for path in source_files(game):
        check_cancelled(cancelled)
        if path.suffix.lower() not in ('.rpy', '.rpym') or path.name.startswith('zzz_linguanova'):
            continue
        # A decoding error blocks preparation with its path; it is not an empty dictionary.
        try:
            content = path.read_text(encoding='utf-8-sig')
        except UnicodeError as exc:
            raise ValueError(f'No se puede leer el guion UTF-8: {path}') from exc
        for match in _CHARACTER_NAME_ARG_RE.finditer(content):
            name = match['name'].strip()
            if _PLAIN_NAME_RE.fullmatch(name) and not any(c in name for c in '[]{}%\\'):
                declarations.setdefault(name, []).append({'path': path.relative_to(game).as_posix(),
                    'line': content.count('\n', 0, match.start()) + 1})
    progress('Diccionario: inventariando los textos y sus contextos antes de traducir')
    entries, diagnostics = ExtractionAdapter().extract(game, mode)
    check_cancelled(cancelled)
    # Compiled/archive contexts are accepted as evidence only when the parser retained a declaration.
    for entry in entries:
        for match in _CHARACTER_NAME_ARG_RE.finditer(entry.context):
            name = match['name'].strip()
            if name == entry.original and _PLAIN_NAME_RE.fullmatch(name):
                evidence = {'path': entry.path, 'line': entry.line}
                if evidence not in declarations.setdefault(name, []):
                    declarations[name].append(evidence)
    entities = []
    for name, evidence in sorted(declarations.items()):
        scoped = [e.occurrence_id for e in entries if e.original == name and
                  any(m['name'] == name for m in _CHARACTER_NAME_ARG_RE.finditer(e.context))]
        entities.append({'id': digest(['character', name]), 'source': name, 'kind': 'character',
                         'evidence': evidence, 'occurrence_ids': scoped,
                         'policy': 'preserve_declaration_only', 'confidence': 'declaration'})
    counts = Counter(e.original for e in entries if e.publishable and e.kind in ('ui', 'screen_translatable'))
    for text, count in sorted(counts.items()):
        if count >= 2 and len(text) <= 100 and text not in declarations:
            entities.append({'id': digest(['term', text]), 'source': text, 'kind': 'term',
                             'count': count, 'policy': 'review_before_enforcing',
                             'evidence': [{'path': e.path, 'line': e.line} for e in entries if e.original == text][:12],
                             'occurrence_ids': [], 'confidence': 'repeated_ui_text'})
    # Assets and opaque source formats remain visible as coverage limitations.
    opaque = sorted(p.relative_to(game).as_posix() for p in source_files(game)
                    if p.suffix.lower() in ('.rpa', '.rpyc', '.rpymc'))
    if opaque:
        diagnostics.append({'status': 'source_coverage_requires_review', 'paths': opaque,
                            'reason': 'Compiled/archive contents depend on supported parser formats; virtual image inventory is reported separately'})
    return {'inventory': jsonable(entries), 'entities': entities, 'diagnostics': diagnostics,
            'coverage': 'supported_scripts_only', 'mode': mode}
