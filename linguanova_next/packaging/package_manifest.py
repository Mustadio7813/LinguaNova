from pathlib import Path
from ..util import file_hash, safe_relative
from ..version import VERSION


def output_manifest(stage,job,destination,limitations,ui,fonts,resources):
    files=[]
    for path in sorted(Path(stage).rglob('*')):
        if path.is_file():
            rel=path.relative_to(stage).as_posix();safe_relative(rel)
            files.append({'path':rel,'size':path.stat().st_size,'sha256':file_hash(path),'owner':'linguanova_next'})
    return {'schema_version':1,'generator_version':VERSION,'project_id':job.project_id,'sources_hash':job.sources_hash,
            'job_id':job.job_id,'job_identity':job.identity,'destination':destination,'files':files,
            'limitations':limitations,'native_ui':ui,'runtime_fonts':fonts,'visual_results':resources,
            'validation_level':'experimental_unverified','requires_creator_runtime':False,
            'renpy_compatibility':'Verify with the exact target game/engine before distribution'}
