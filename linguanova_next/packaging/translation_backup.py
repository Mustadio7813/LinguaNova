"""Independent backup of installed translations; never invokes a translator."""
from pathlib import Path
import tempfile
import zipfile
from ..adapters.extraction_adapter import game_directory
from ..dictionary.analysis import check_cancelled
from ..dictionary.service import project_identity
from ..util import atomic_bytes, canonical, digest, file_hash, safe_join, safe_relative
from .share_package_validator import validate_zip


class TranslationBackup:
    def inventory(self, project, cancelled=None):
        game = game_directory(project)
        tl = game / 'tl'
        if not tl.is_dir():
            raise ValueError('No existe game/tl en la carpeta seleccionada')
        files = []
        paths = sorted(tl.rglob('*'))
        # These helpers are dependencies of this app's installed language menu.
        paths += [game / name for name in ('zzz_linguanova_preferences_languages.rpy',
                    'zzz_linguanova_ocultar_fuentes.rpy','zzz_linguanova_image_codecs.rpy',
                    'zzz_linguanova_runtime.rpy','zzz_linguanova_init.rpy',
                    'zzz_linguanova_language_menu.rpy') if (game / name).exists()]
        paths += list(game.glob('linguanova_mod_*.rpy'))
        if (game / 'linguanova_fonts').is_dir():
            paths += sorted((game / 'linguanova_fonts').rglob('*'))
        if (game / 'linguanova_next_packages').is_dir():
            paths += sorted((game / 'linguanova_next_packages').rglob('*.json'))
        if tl.is_symlink() or any((game/name).is_symlink() for name in ('linguanova_fonts','linguanova_next_packages')):
            raise ValueError('Las carpetas del respaldo no pueden ser enlaces')
        for path in paths:
            check_cancelled(cancelled)
            relative = path.relative_to(game)
            if any(p.lower() in ('saves', 'cache', '__pycache__') or p.startswith('.') for p in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError('El respaldo requiere archivos copiados, sin enlaces: ' + str(path))
            if not path.is_file():
                continue
            name = 'game/' + relative.as_posix()
            safe_relative(name)
            files.append({'path': name, 'size': path.stat().st_size, 'sha256': file_hash(path), 'owner': 'translation_backup'})
        if not any(f['path'].startswith('game/tl/') for f in files):
            raise ValueError('game/tl no contiene traducciones para respaldar')
        if len({f['path'].casefold() for f in files}) != len(files):
            raise ValueError('Hay rutas de traducción incompatibles entre Windows y este sistema')
        return {'game': str(game), 'files': files,
                'languages': sorted({Path(f['path']).parts[2] for f in files if f['path'].startswith('game/tl/') and len(Path(f['path']).parts) > 3}),
                'estimated_bytes': sum(f['size'] for f in files)}

    def build(self, project, destination, cancelled=None):
        destination = Path(destination).expanduser().resolve()
        game = game_directory(project)
        if destination.is_relative_to(game):
            raise ValueError('Guarda el ZIP/RAR fuera de game/ para no incluirlo en el respaldo')
        if destination.suffix.lower() not in ('.zip', '.rar'):
            raise ValueError('Selecciona un destino .zip o .rar')
        before = self.inventory(game, cancelled)
        files = before['files']
        manifest = {'schema_version': 1, 'kind': 'installed_translation_backup',
                    'project_id': project_identity(game)[0], 'files': files,
                    'destinations': [{'renpy_id': name} for name in before['languages']],
                    'validation_level': 'backup_bytes_verified',
                    'limitations': ['Respaldo exacto de los archivos existentes; no certifica traducción, tipografía ni integración',
                                    'Las imágenes deben estar instaladas en game/tl/<idioma>/ conservando sus rutas relativas'],
                    'native_ui': {'preferences_only': False}}
        manifest['package_id'] = digest(manifest)
        instructions = ('RESPALDO DE TRADUCCIONES\n\nDescomprime y copia game/ sobre la misma versión del juego.\n'
                        'Conserva las subcarpetas de idioma. Haz una copia del juego antes de reemplazar archivos.\n'
                        'Incluye los archivos existentes de game/tl y las dependencias conocidas de LinguaNova.\n'
                        'No genera un selector para juegos desconocidos ni detecta imágenes reemplazadas fuera de game/tl.\n')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='linguanova-backup-', dir=destination.parent) as temporary:
            archive_path = Path(temporary) / 'backup.zip'
            with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                members = [(f['path'], None) for f in files] + [
                    ('manifest.json', (canonical(manifest) + '\n').encode()),
                    ('LEEME_INSTALACION.txt', instructions.encode())]
                for name, content in sorted(members):
                    check_cancelled(cancelled)
                    if content is None:
                        content = safe_join(game.parent, name).read_bytes()
                    item = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                    item.compress_type = zipfile.ZIP_DEFLATED
                    item.external_attr = 0o100644 << 16
                    archive.writestr(item, content)
            if self.inventory(game, cancelled) != before:
                raise ValueError('Las traducciones cambiaron durante el respaldo; se conserva el archivo anterior')
            verdict = validate_zip(archive_path)
            if not verdict['valid']:
                raise ValueError('El respaldo no superó la validación: ' + str(verdict['errors']))
            check_cancelled(cancelled)
            if destination.suffix.lower() == '.rar':
                from .rar_archive import zip_to_rar
                # Convert privately, then check cancellation before publication.
                private = Path(temporary) / 'backup.rar'
                verdict = zip_to_rar(archive_path, private)
                check_cancelled(cancelled)
                atomic_bytes(destination, private.read_bytes())
            else:
                atomic_bytes(destination, archive_path.read_bytes())
            return verdict | {'path': str(destination), 'bytes': destination.stat().st_size,
                              'format': destination.suffix[1:], 'languages': before['languages']}
