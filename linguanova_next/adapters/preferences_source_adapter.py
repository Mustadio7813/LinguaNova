from pathlib import Path
import re
from ..util import load_json, file_hash, safe_join


def inspect_preferences(game,recipe):
    if not recipe or recipe.get('schema_version')!=1:
        return {'compatible':False,'reason':'No inspected game-specific recipe supplied'}
    if recipe.get('strategy')!='existing_use_slot':
        return {'compatible':False,'reason':'Recipe strategy not implemented; requires a new reviewed integration'}
    path=safe_join(game,recipe['source_path'])
    if not path.is_file() or file_hash(path)!=recipe['source_sha256']:
        return {'compatible':False,'reason':'Recipe source fingerprint differs from the inspected version'}
    text=path.read_text(encoding='utf-8-sig')
    screen=recipe['screen']
    m=re.search(r'^screen\s+'+re.escape(screen)+r'\s*\([^\n]*\)\s*:\s*\n(?P<body>(?:(?:[ \t]+[^\n]*|\s*)\n)*)',text,re.M)
    if not m or not re.search(r'^\s+use\s+linguanova_preferences_languages\b',m['body'],re.M):
        return {'compatible':False,'reason':'Native Preferences extension slot absent; no shortcut is generated'}
    return {'compatible':True,'recipe_id':recipe['game_id'],'screen':screen,'source_hash':recipe['source_sha256'],
            'styles':recipe.get('styles',{}),'visual_review':recipe.get('visual_review','not_executed'),
            'persistence_review':recipe.get('persistence_review','not_executed'),
            'startup_language_override':bool(re.search(r'\bconfig\.language\s*=\s*[^N\s]',text))}
