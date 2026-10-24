"""Atomic per-project dictionary, integrity checks and immutable job snapshots."""
from dataclasses import asdict
import os
from pathlib import Path
from ..adapters.extraction_adapter import game_directory
from ..core.job_lock import JobLock
from ..util import atomic_json, digest, load_json
from .analysis import ANALYZER_VERSION, analyze, check_cancelled, inventory_manifest


def project_identity(game):
    canonical = str(Path(game).resolve())
    if os.name == 'nt':
        canonical = os.path.normcase(canonical)
    return digest(canonical), canonical


def read_verified(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Falta un archivo requerido del Diccionario: ' + str(path))
    envelope = load_json(path)
    if not isinstance(envelope, dict) or digest(envelope.get('payload')) != envelope.get('sha256'):
        raise ValueError('Integridad del Diccionario incorrecta: ' + str(path))
    return envelope['payload']


def write_verified(path, payload):
    atomic_json(path, {'sha256': digest(payload), 'payload': payload})


class DictionaryService:
    def __init__(self, data, diagnostics):
        self.root = Path(data) / 'dictionaries'
        self.diagnostics = diagnostics

    def prepare(self, project, destination, mode='native', cancelled=None, progress=None):
        game = game_directory(project)
        project_id, canonical = project_identity(game)
        target = asdict(destination)
        target_key = digest(target)
        folder = self.root / project_id
        progress = progress or (lambda text: None)
        try:
            with JobLock(game):
                sources = inventory_manifest(game, cancelled)
                source_key = digest([ANALYZER_VERSION, mode, sources])
                cached_path = folder / (mode + '.json')
                previous = read_verified(cached_path) if cached_path.exists() else None
                reused = bool(previous and previous['source_key'] == source_key)
                if reused:
                    analysis = previous['analysis']
                    progress('Diccionario: reutilizando el análisis del mismo juego para ' + destination.locale)
                else:
                    analysis = analyze(game, mode, cancelled, progress)
                    check_cancelled(cancelled)
                    if inventory_manifest(game, cancelled) != sources:
                        raise ValueError('El juego cambió durante el análisis del Diccionario; vuelve a prepararlo')
                    write_verified(cached_path, {'source_key': source_key, 'sources': sources,
                        'analysis': analysis, 'project_id': project_id, 'canonical_game': canonical})
                decisions_path = folder / 'targets' / (target_key + '.json')
                decisions = read_verified(decisions_path) if decisions_path.exists() else {'target': target, 'entries': {}}
                if decisions['target'] != target:
                    raise ValueError('Las decisiones del Diccionario pertenecen a otro idioma/perfil')
                current = {e['id']: e for e in analysis['entities']}
                choices = {k: v for k, v in decisions['entries'].items() if k in current and v.get('source_key')==source_key}
                for key, decision in choices.items():
                    self._validate_choice(current[key], decision)
                snapshot = {'schema_version': 1, 'analyzer_version': ANALYZER_VERSION, 'project_id': project_id,
                    'canonical_game': canonical, 'source_key': source_key, 'target_key': target_key, 'target': target,
                    'analysis': analysis, 'choices': choices}
                previous_sources = previous['sources'] if previous else {}
                changed = sum(previous_sources.get(k) != v for k, v in sources.items())
                removed = len(set(previous_sources) - set(sources))
                return {'snapshot': snapshot, 'reused': reused, 'files': len(sources),
                        'changed_files': 0 if reused else changed, 'removed_files': removed,
                        'stale_choices': len(decisions['entries']) - len(choices)}
        except Exception as exc:
            from ..core.work_queue import CancelledJob
            if isinstance(exc, CancelledJob):
                raise
            self.diagnostics.record('Diccionario · preparación', exc, project=game)
            raise

    @staticmethod
    def _validate_choice(entity, decision):
        if decision.get('source') != entity['source'] or decision.get('decision') not in ('translate', 'preserve'):
            raise ValueError('Decisión del Diccionario incompatible con su término')
        if not decision.get('text', '').strip() or not decision.get('reason', '').strip():
            raise ValueError('Indica texto y motivo para la decisión del Diccionario')
        if decision['decision'] == 'preserve' and decision['text'] != entity['source']:
            raise ValueError('Conservar debe mantener exactamente el texto original')

    def save_choice(self, prepared, entity_id, decision, text, reason):
        snapshot = prepared['snapshot']
        game = Path(snapshot['canonical_game'])
        with JobLock(game):
            if digest([ANALYZER_VERSION, snapshot['analysis']['mode'], inventory_manifest(game)]) != snapshot['source_key']:
                raise ValueError('El juego cambió; prepara el Diccionario antes de editarlo')
            entity = next((e for e in snapshot['analysis']['entities'] if e['id'] == entity_id), None)
            if entity is None:
                raise ValueError('El término no pertenece al Diccionario del proyecto visible')
            choice = {'source': entity['source'], 'decision': decision, 'text': text, 'reason': reason.strip(),
                      'source_key': snapshot['source_key']}
            self._validate_choice(entity, choice)
            path = self.root / snapshot['project_id'] / 'targets' / (snapshot['target_key'] + '.json')
            stored = read_verified(path) if path.exists() else {'target': snapshot['target'], 'entries': {}}
            if stored['target'] != snapshot['target']:
                raise ValueError('El destino del Diccionario cambió')
            stored['entries'][entity_id] = choice
            write_verified(path, stored)
        return choice

    @staticmethod
    def glossary(snapshot):
        # Automatic character detection is scoped to declarations, never a global word replacement.
        return {choice['source']: choice['text'] for key, choice in snapshot['choices'].items()
                if next(e for e in snapshot['analysis']['entities'] if e['id'] == key)['kind'] == 'term'}

    @staticmethod
    def view(prepared):
        snapshot = prepared['snapshot']
        rows = [dict(e, choice=snapshot['choices'].get(e['id'])) for e in snapshot['analysis']['entities']]
        return {k: v for k, v in prepared.items() if k != 'snapshot'} | {
            'project': snapshot['canonical_game'], 'project_id': snapshot['project_id'],
            'target': snapshot['target'], 'source_key': snapshot['source_key'], 'entries': rows,
            'diagnostics': snapshot['analysis']['diagnostics'], 'coverage': snapshot['analysis']['coverage'],
            'inventory_count': len(snapshot['analysis']['inventory'])}
