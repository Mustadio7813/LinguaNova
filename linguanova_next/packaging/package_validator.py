from pathlib import Path
import json
import re
from ..util import safe_join, safe_relative, file_hash
from ..core.native_ui_audit import audit_native_source


def validate_output(stage,manifest):
    errors=[];seen=set();old_seen={}
    for f in manifest['files']:
        rel=f['path'];safe_relative(rel)
        key=rel.casefold()
        if key in seen: errors.append('Case-insensitive path collision: '+rel)
        seen.add(key)
        if not rel.startswith('game/') or rel.startswith('game/game/'):
            errors.append('Invalid player root: '+rel)
        if any(x in rel.lower() for x in ['persistent','settings_next','cache_next','jobs/','api_key','coverage_report']):
            errors.append('Creator/private file in player output: '+rel)
        path=safe_join(stage,rel)
        if not path.is_file() or file_hash(path)!=f['sha256']:
            errors.append('Output hash mismatch: '+rel);continue
        if path.suffix.lower() in ('.exe','.bat','.py','.pkl','.safetensors','.pt','.bin'):
            errors.append('Unexpected player dependency: '+rel)
        if path.suffix=='.rpy':
            content=path.read_text(encoding='utf-8-sig')
            if re.search(r'^\s*key\s|config\.(?:overlay_screens|keymap)|Shift\+L',content,re.M):
                errors.append('Generated language UI shortcut/overlay: '+rel)
            language=''
            for line in content.splitlines():
                match=re.match(r'\s*translate\s+(\w+)\s+strings:',line)
                if match:language=match[1]
                if line.strip().startswith('old '):
                    try: old=json.loads(line.strip()[4:])
                    except ValueError: errors.append('Invalid string literal: '+rel);continue
                    identity=(language,old)
                    if identity in old_seen:errors.append('Duplicate translation: '+language+' '+old[:40])
                    old_seen[identity]=rel
            for ref in re.findall(r'\bfont\s+"(linguanova_fonts/[^"\n]+)"',content):
                if not (Path(stage)/'game'/ref).is_file():errors.append('Missing font dependency: '+ref)
    return {'valid':not errors,'errors':errors,'files':len(manifest['files']),
            'integration_verified':manifest.get('native_ui',{}).get('visual_review')=='verified'}
