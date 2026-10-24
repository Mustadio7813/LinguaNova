from ..packaging.native_export import native_export
from ..packaging.mod_profile_export import export_mod


def export_runtime(game,stage,job,entries,results):
    results,written,warnings=native_export(game,stage,job,entries,results)
    if job.output_mode=='mod':
        # Same dictionary owner, no second old/new definitions; raw UI labels
        # additionally use this exact profile-aware mapping through replace_text.
        export_mod(stage,job,written)
    return results,written,warnings
