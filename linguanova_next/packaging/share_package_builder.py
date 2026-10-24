from pathlib import Path
import tempfile
import shutil
import zipfile
from ..util import load_json, atomic_bytes, atomic_json, file_hash, safe_join
from ..contracts.job import TranslationJob
from ..core.language_registry import LanguageRegistry
from ..adapters.extraction_adapter import game_directory, source_manifest
from ..util import digest
from .native_ui_export import build_native_ui
from .share_package_manifest import share_manifest
from .share_package_validator import validate_zip
from .share_package_installation import INSTRUCTIONS
from .package_validator import validate_output


class SharePackageBuilder:
    def inspect(self,job_directories):
        rows=[]
        for directory in job_directories:
            directory=Path(directory)
            manifest=load_json(directory/'published/output_manifest.json') or load_json(directory/'output_manifest.json')
            if not manifest:raise ValueError('Job has no generated output')
            verdict=validate_output(directory/'published',manifest)
            if not verdict['valid']:raise ValueError(verdict['errors'])
            rows.append((directory,manifest))
        if not rows:raise ValueError('Select at least one generated destination/profile')
        if len({(m['project_id'],m['sources_hash']) for _,m in rows})!=1:
            raise ValueError('Selected outputs belong to different source versions/projects')
        if len({m['destination']['renpy_id'] for _,m in rows})!=len(rows):
            raise ValueError('Select a single revision per destination/profile')
        return rows

    def preview(self,job_directories):
        rows=self.inspect(job_directories)
        from .rar_archive import rar_status
        return {'destinations':[m['destination'] for _,m in rows],
                'files':[f['path'] for _,m in rows for f in m['files']],
                'estimated_bytes':sum(f['size'] for _,m in rows for f in m['files']),
                'limitations':sorted(set(v for _,m in rows for v in m['limitations'])),
                'validation_level':'experimental_unverified',
                'archive_formats':{'zip':{'available':True},'rar':rar_status()}}

    def build(self,job_directories,destination):
        destination=Path(destination).resolve()
        if destination.suffix.lower()=='.rar':
            from .rar_archive import rar_status,zip_to_rar
            status=rar_status()
            if not status['available']:raise ValueError(status['reason'])
            destination.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='linguanova-rar-source-',dir=destination.parent) as temp:
                result=self.build(job_directories,Path(temp)/'validated_payload.zip')
                return result|zip_to_rar(Path(temp)/'validated_payload.zip',destination)
        rows=self.inspect(job_directories)
        jobs=[]
        for d,_ in rows:
            data=load_json(d/'job.json')
            for legacy in ('image_enabled','ocr_source','image_method'):
                data.pop(legacy,None)
            jobs.append(TranslationJob(**data))
        from ..bootstrap import rules_hash
        from .frozen_resources import resource_root
        if any(j.rules_hash!=rules_hash(resource_root()) for j in jobs):
            raise ValueError('Generation rules changed; regenerate reviewed outputs before sharing')
        game=game_directory(jobs[0].project_path)
        if digest(source_manifest(game))!=jobs[0].sources_hash:
            raise ValueError('Source game changed since generation; create a new reviewed job')
        destination=Path(destination).resolve()
        if destination.suffix.lower()!='.zip':raise ValueError('Choose a .zip or .rar output path')
        destination.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='linguanova-share-',dir=destination.parent) as temp:
            stage=Path(temp)
            seen={}
            common={'game/zzz_linguanova_preferences_languages.rpy','game/zzz_linguanova_ocultar_fuentes.rpy',
                    'game/zzz_linguanova_image_codecs.rpy'}
            for directory,manifest in rows:
                for f in manifest['files']:
                    rel=f['path']
                    if rel in common:continue
                    if rel.casefold() in seen and seen[rel.casefold()]!=f['sha256']:
                        raise ValueError('Output resource collision: '+rel)
                    seen[rel.casefold()]=f['sha256']
                    target=safe_join(stage,rel);target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(safe_join(directory/'published',rel),target)
            options=__import__('json').loads(jobs[0].options_json)
            ui=build_native_ui(game,stage/'game',[m['destination'] for _,m in rows],options.get('ui_recipe'))
            from ..adapters.language_menu_adapter import protect_resources
            protect_resources(stage/'game')
            from .image_codecs_template import write_image_codecs
            write_image_codecs(stage/'game')
            limitations=[v for _,m in rows for v in m['limitations']]
            if not ui.get('preferences_only'):limitations.append('Preferences integration blocked: '+ui.get('reason','unknown recipe'))
            files=[{'path':p.relative_to(stage).as_posix(),'size':p.stat().st_size,'sha256':file_hash(p),'owner':'linguanova_next'}
                   for p in sorted(stage.rglob('*')) if p.is_file()]
            from .output_ownership import prove_target_collisions, write_ownership
            collisions=prove_target_collisions(game,files)
            if collisions:raise ValueError(collisions)
            files.append(write_ownership(stage,files,[m['destination'] for _,m in rows]))
            manifest=share_manifest([m for _,m in rows],files,ui,limitations)
            validation=validate_output(stage,manifest)
            if not validation['valid']:raise ValueError(validation['errors'])
            atomic_json(stage/'manifest.json',manifest)
            atomic_bytes(stage/'LEEME_INSTALACION.txt',INSTRUCTIONS.encode())
            output=stage/'package.zip'
            with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for rel in sorted([f['path'] for f in files]+['manifest.json','LEEME_INSTALACION.txt']):
                    info=zipfile.ZipInfo(rel,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    info.external_attr=0o100644<<16
                    z.writestr(info,safe_join(stage,rel).read_bytes())
            verdict=validate_zip(output)
            if not verdict['valid']:raise ValueError(verdict['errors'])
            atomic_bytes(destination,output.read_bytes())
            return verdict|{'path':str(destination),'bytes':destination.stat().st_size,'format':'zip','limitations':manifest['limitations']}
