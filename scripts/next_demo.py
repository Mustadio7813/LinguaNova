#!/usr/bin/env python3
"""Reproducible text-only demo using a controlled fixture provider."""
from pathlib import Path
import argparse, asyncio, shutil, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests/next'))
from support import FixtureProvider, TARGETS
from linguanova_next.bootstrap import Services
from linguanova_next.core.translation_job import TranslationJobRunner
from linguanova_next.util import load_json, atomic_json
from linguanova_next.packaging.share_package_builder import SharePackageBuilder


def build_demo(workspace, rar=False):
    workspace = Path(workspace).resolve(); workspace.mkdir(parents=True, exist_ok=True)
    project = workspace / 'Fuente de prueba á'
    if not project.exists():
        shutil.copytree(ROOT / 'next_fixtures/native_slot_game', project)
    services = Services(data=workspace / 'creator_data')
    recipe = load_json(ROOT / 'linguanova_next/data/game_ui_profiles/controlled_fixture.json')
    directories = []
    for target, profile in TARGETS:
        job = services.create_job(project, target, profile, options={'ui_recipe': recipe, 'attempts': 1})
        directory = services.data / 'jobs' / job.job_id
        asyncio.run(TranslationJobRunner(services, job, provider_factory=FixtureProvider).run())
        for entry in load_json(directory / 'inventory.json', []):
            if entry['original'] in ('Alex', 'LINGUANOVA FIXTURE', 'LinguaNova Controlled Fixture'):
                services.review_entry(job.job_id, entry['occurrence_id'], 'preserve', '', reason='Known name/title in the authored test fixture', reviewer='automated-fixture-test', editorial_approved=False)
        asyncio.run(TranslationJobRunner(services, job, provider_factory=FixtureProvider).run())
        if load_json(directory / 'state.json', {}).get('status') != 'completed_experimental':
            raise RuntimeError('Text fixture did not complete: ' + str(directory))
        directories.append(directory)
        print('Controlled fixture:', job.target_locale, 'job', job.job_id, flush=True)
    output = workspace / 'Paquete_fixture_multidioma_EXPERIMENTAL.zip'
    result = SharePackageBuilder().build(directories, output)
    summary = {'provider': 'controlled dictionary; not a real service', 'jobs': [str(d) for d in directories], 'source': str(project), 'package': result}
    if rar:
        rar_result = SharePackageBuilder().build(directories, workspace / 'Paquete_fixture_multidioma_EXPERIMENTAL.rar')
        summary['rar_package'] = rar_result
    atomic_json(workspace / 'demo_summary.json', summary)
    return workspace / 'demo_summary.json'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--rar', action='store_true', help='Also create genuine RAR with the locally installed RAR/WinRAR archiver')
    args = parser.parse_args()
    print(build_demo(args.workspace, rar=args.rar))
