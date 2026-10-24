import re


def classify(text, context, kind=''):
    if re.search(r'\bconfig\.(?:save_directory|version|executable)\s*=',context):
        return 'technical_uncertain'
    if re.search(r'\.(?:png|webp|jpe?g|ogg|ttf|rpyc?)\b|https?://',text,re.I):
        return 'technical_uncertain'
    if re.fullmatch(r'[\W_]+',text):
        return 'vocalization_uncertain'
    if kind in ('ui','menu') or re.search(r'\b(?:screen|textbutton|tooltip)\b',context):
        return 'ui'
    if len(text.strip())<=3:
        return 'short_context_required'
    return kind or 'dialogue'
