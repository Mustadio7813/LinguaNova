import re


def audit_native_source(content,inspection):
    forbidden=[]
    for pattern in [r'^\s*key\s',r'config\.overlay_screens',r'config\.keymap',r'ShowMenu\(',r'Show\(',r'Shift\+L',r'K_L',r'K_l']:
        if re.search(pattern,content,re.M):
            forbidden.append(pattern)
    return {'preferences_only':bool(inspection.get('compatible')),'forbidden':forbidden,
            'native_style_inherited':bool(inspection.get('compatible')),
            'persistence_implemented':'renpy.save_persistent()' in content,
            'visual_review':inspection.get('visual_review','not_executed'),
            'persistence_review':inspection.get('persistence_review','not_executed')}
