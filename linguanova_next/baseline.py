"""Read-only checks against the frozen user-supplied base. No Qt/client imports."""
from pathlib import Path
from .util import atomic_json, file_hash, digest, load_json

EXPECTED_MANIFEST_HASH = '5de0222d532824549fd0db093d886b14bec7f45d735618d80889ff01ee7fb9df'
EXPECTED_ARCHIVE = 'd702b683002f7cebccb92fb582c4b7ac2021b2ab0100cac41106470aaa558747'

# User-authorized main-window integration: exact source bytes for this revision.
APPROVED_UI_PATCHES = {'LinguaNova.spec': {'size': 11768, 'sha256': '1e7a32961b73c19785762b58c683484df182ff1470523a12521dc1997cfbe9ba'}, 'README.es.md': {'size': 11568, 'sha256': '7170fcfcc80dfe115ae17e20f45a90f384e95cf32519e044e9b269d81afba3fb'}, 'README.md': {'size': 10668, 'sha256': '2fd69ee608f7a1027e8f2d6a3674a8ee713b6a109811263f4de6c62ea2e0e295'}, 'build_windows.bat': {'size': 630, 'sha256': 'd2945e811ea0320bb4ee78b9c0bd3f23b7effc3d3839fbdfff86fba80b4a5b41'}, 'locales/en.json': {'size': 109587, 'sha256': 'd3bec9b7f2c0d722fbdce4d6f4fc51dc1f800f80bdb34cef755a4fc9c2c0db80'}, 'locales/es.json': {'size': 119381, 'sha256': '728b3ff6f900812eff7b390179d9c0bfd3a56209a99141bda5302d388ae66cd0'}, 'locales/fr.json': {'size': 124316, 'sha256': '14acad40d9021a87e614bbcd2f19e0b984e5a1e87f4a08c51d5ad8052915a53d'}, 'locales/pt.json': {'size': 118574, 'sha256': 'dbd98bb680e209021655f5ee2c061813038fe12c2ab6bce1d1b142974b95ac41'}, 'locales/ru.json': {'size': 144768, 'sha256': 'f09990c25cc3396617d7cd80eef0add29fbbfc45c2db23321d50f991b2d83731'}, 'requirements.txt': {'size': 1142, 'sha256': '9766fc06861215f5e59a36e03877ce170e37691589d0012f7867694eabcb7648'}, 'run.bat': {'size': 760, 'sha256': 'a7c14e5046ee8bcdcb1d3b692be76fd33e69a85f1f00526d76209e9298a857e9'}, 'src/backend/app_backend.py': {'size': 124473, 'sha256': '2146183c46f71b7cf711459fb318b1f6f39a0db826f1271429c69649d6e0ce7d'}, 'src/core/pipeline/base.py': {'size': 2185, 'sha256': '04d02e7a0c07ed2be441f2ab464d003a0065727366529c16312350dc64954dc0'}, 'src/core/pipeline/orchestrator.py': {'size': 156885, 'sha256': '8d4a0db502c4f59fb73e26b1262a00dcd68c9dc0599038ed0d2a936591fb730b'}, 'src/gui/qml/Main.qml': {'size': 381569, 'sha256': '97cd6950bee1464d187dfa892dcce9615966a95077edffb066b201dc8a672347'}, 'src/utils/config.py': {'size': 48311, 'sha256': '124b26653401b6f12a0c5646b348e9143de2c031b74df540f7390be86534f37f'}, 'src/version.py': {'size': 409, 'sha256': '1ef8a4b6824b5d4ec94747530b913693d65d12b7a57ceb3f3af17f50e23df5e6'}}


def capture_baseline(root, paths):
    root = Path(root)
    return [{'path': str(p), 'size': (root/p).stat().st_size, 'sha256': file_hash(root/p)} for p in sorted(paths)]


def verify_baseline(root, manifest=None):
    root = Path(root)
    manifest = manifest or load_json(root/'next_evidence/baseline_manifest.json')
    if not manifest or digest(manifest)!=EXPECTED_MANIFEST_HASH or manifest['archive_sha256'] != EXPECTED_ARCHIVE or len(manifest['files']) != 283:
        raise ValueError('Unrecognized protected baseline')
    changed, missing, patched = [], [], []
    for f in manifest['files']:
        p = root/f['path']
        if not p.is_file():
            missing.append(f['path'])
        elif p.stat().st_size != f['size'] or file_hash(p) != f['sha256']:
            patch=APPROVED_UI_PATCHES.get(f['path'])
            if patch and p.stat().st_size==patch['size'] and file_hash(p)==patch['sha256']:
                patched.append(f['path'])
            else:
                changed.append(f['path'])
    return {'valid': not (changed or missing), 'protected_count': len(manifest['files']),
            'changed': changed, 'missing': missing, 'patched': patched,
            'manifest_hash': digest([digest(manifest),{p:file_hash(root/p) for p in patched}]) if patched else digest(manifest)}


def require_baseline(root):
    result = verify_baseline(root)
    if not result['valid']:
        raise ValueError('Protected base mismatch: ' + str(result))
    return result['manifest_hash']
