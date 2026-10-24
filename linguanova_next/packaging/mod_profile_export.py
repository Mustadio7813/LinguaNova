from pathlib import Path
from ..util import atomic_json, atomic_bytes

HOOK=r"""# LinguaNova Next isolated MOD mapping; no selector, overlay or language key.
init 920 python:
    import json as _ln_mod_json
    _ln_mod_previous_filter = config.replace_text
    _ln_mod_catalogs = {}
    _ln_mod_active = object()
    def _ln_mod_replace_text(text):
        global _ln_mod_active, _ln_mod_catalogs
        code = _preferences.language
        if code != _ln_mod_active:
            _ln_mod_catalogs = {}
            _ln_mod_active = code
            if code:
                path = "linguanova_next_mod/" + code + ".json"
                if renpy.loadable(path):
                    with renpy.file(path) as source:
                        data = _ln_mod_json.loads(source.read().decode("utf-8"))
                    if data.get("schema_version") == 1 and data.get("renpy_id") == code:
                        _ln_mod_catalogs = data.get("strings", {})
        value = _ln_mod_previous_filter(text) if _ln_mod_previous_filter else text
        return _ln_mod_catalogs.get(value, value) if code else value
    config.replace_text = _ln_mod_replace_text
"""


def export_mod(stage,job,mapping):
    data={'schema_version':1,'renpy_id':job.renpy_id,'locale':job.target_locale,'profile_id':job.profile_id,'strings':mapping}
    path=Path(stage)/'game/linguanova_next_mod'/(job.renpy_id+'.json')
    atomic_json(path,data)
    atomic_bytes(Path(stage)/'game/zzz_linguanova_next_mod.rpy',HOOK.encode())
    return ['game/linguanova_next_mod/'+path.name,'game/zzz_linguanova_next_mod.rpy']
