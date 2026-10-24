from pathlib import Path
from ..util import atomic_bytes
from ..adapters.preferences_source_adapter import inspect_preferences
from ..adapters.language_menu_adapter import installed_languages, protect_resources
from ..core.native_ui_audit import audit_native_source
from ..core.native_ui_policy import require_preferences_only
from .preferences_template import render_preferences
from .persistence_template import render_persistence

LABELS={'spanish':'Español (variante heredada)','french':'Français','russian':'Русский','english':'English','portuguese':'Português'}


def build_native_ui(game, staging_game, destinations, recipe):
    inspection=inspect_preferences(game,recipe)
    if not inspection.get('compatible'):
        return {'preferences_only':False,'reason':inspection['reason'],'forbidden':[],
                'persistence_implemented':False,'visual_review':'not_executed','persistence_review':'not_executed'}
    languages={code:{'name':LABELS.get(code,code),'profile_id':'','locale':''} for code in installed_languages(game)}
    for dest in destinations:
        languages[dest['renpy_id']]={'name':dest['name'],'profile_id':dest.get('profile_id',''),'locale':dest['locale']}
    source=render_preferences(languages,inspection.get('styles',{}))+render_persistence()
    audit=audit_native_source(source,inspection)
    require_preferences_only(audit)
    target=Path(staging_game)/'zzz_linguanova_preferences_languages.rpy'
    atomic_bytes(target,source.encode('utf-8'))
    protect_resources(staging_game)
    return audit|{'languages':languages,'path':target.name,'recipe_id':recipe['game_id']}
