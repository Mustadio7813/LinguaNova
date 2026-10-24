"""Creator-side safe copy rehearsal; recipient needs only their game."""
from pathlib import Path
import shutil
import zipfile
import json
from ..util import safe_join, file_hash, atomic_bytes, atomic_json
from .share_package_validator import validate_archive
from .rar_archive import open_player_archive

INSTRUCTIONS="""PAQUETE EXPERIMENTAL: instalación y ejecución en un juego real NO VERIFICADAS.
Compatible únicamente con la versión/huella indicada en manifest.json.

DESTINO: carpeta raíz del juego, donde se encuentra su ejecutable habitual.
1. Cierra el juego completamente.
2. Descomprime este archivo ZIP o RAR en una carpeta temporal.
3. Copia la carpeta game/ de este paquete a la RAÍZ del juego y combina las carpetas.
   NO la pegues dentro de game/: produciría game/game/ y no funcionaría.
4. Abre el ejecutable habitual del juego. Si la receta de Preferencias fue comprobada,
   los idiomas aparecen allí. No se añaden teclas de cambio de idioma.
El jugador no necesita Python externo, LinguaNova ni modelos de IA.

ANTES DE ACTUALIZAR: conserva una copia privada de los archivos del paquete anterior.
La copia manual no ejecuta verificaciones, no hace respaldos y no detecta modificaciones.
No sobrescribas archivos ajenos o modificados: solicita un paquete compatible al creador.
No copies archivos de persistent ni partidas; no están incluidos en este paquete.

RETIRADA: elimina únicamente las rutas game/ enumeradas en manifest.json, después de
comprobar que siguen siendo los archivos de este paquete. Los .rpyc creados por RenPy
con el mismo nombre que los auxiliares .rpy propios también deben retirarse para que
no se cargue código antiguo. No borres traducciones ajenas, fuentes ajenas ni datos del
jugador. Si un archivo fue modificado o compartido con otro paquete, revisa su propiedad.
Selecciona Original antes de retirar la traducción activa cuando sea posible.

Las imágenes exportadas ya están compuestas y conservan sus rutas completas.
Instalar recursos nuevos puede requerir reiniciar. El cambio entre idiomas instalados
usa Preferencias. La calidad lingüística y la integración técnica se revisan por separado.
"""


def install_copy(zip_path,game_root,backup_root,previous_manifest=None):
    verdict=validate_archive(zip_path)
    if not verdict['valid']:raise ValueError(verdict['errors'])
    root=Path(game_root).resolve();backup=Path(backup_root).resolve()
    if root==backup or backup.is_relative_to(root):raise ValueError('Backup must be outside the destination game')
    with open_player_archive(zip_path) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        previous={x['path']:x for x in (previous_manifest or {}).get('files',[])}
        plans=[]
        for f in manifest['files']:
            path=safe_join(root,f['path'])
            if path.exists() and file_hash(path)!=f['sha256']:
                prior=previous.get(f['path'])
                if not prior or file_hash(path)!=prior['sha256']:
                    raise ValueError('Refusing to overwrite foreign/modified file: '+f['path'])
            plans.append((f,path))
        touched=[]
        try:
            for f,path in plans:
                existed=path.exists()
                if existed:
                    saved=safe_join(backup,f['path']);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved)
                atomic_bytes(path,archive.read(f['path']));touched.append((f,path,existed))
        except Exception:
            for f,path,existed in reversed(touched):
                if existed:shutil.copy2(safe_join(backup,f['path']),path)
                else:path.unlink(missing_ok=True)
            raise
        atomic_json(backup/'installation.json',manifest)
        return manifest


def remove_owned(game_root,manifest):
    removed=[];blocked=[]
    ordered=sorted(manifest['files'],key=lambda f:'linguanova_next_packages/' in f['path'])
    for f in ordered:
        path=safe_join(game_root,f['path'])
        if not path.exists():continue
        if file_hash(path)!=f['sha256']:
            blocked.append(f['path']);continue
        path.unlink();removed.append(f['path'])
        # Compiled siblings are intentionally not guessed/deleted here. A creator
        # records their hashes after an engine run for safe automated removal.
    return {'removed':removed,'modified_or_foreign':blocked,'compiled_siblings':'remove only after recording ownership hashes'}
