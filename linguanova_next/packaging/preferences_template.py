import json


def render_preferences(languages,styles):
    prefix=styles.get('prefix','pref')
    if not prefix.replace('_','').isalnum():
        raise ValueError('Unsafe style prefix')
    lines=['# LinguaNova Next: native Preferences slot only.','init offset = 900','',
           'screen linguanova_preferences_languages():','    vbox:',f'        style_prefix "{prefix}"',
           '        label _ln_next_language_caption()',
           '        textbutton _ln_next_original_caption() action Function(_ln_next_choose_language, None) selected (_preferences.language is None)']
    for code,item in sorted(languages.items()):
        if not code.isidentifier():
            raise ValueError('Invalid RenPy language id')
        label=json.dumps(item['name'],ensure_ascii=False)
        profile=json.dumps(item.get('profile_id',''))
        locale=json.dumps(item.get('locale',''))
        lines.append(f'        textbutton {label} action Function(_ln_next_choose_language, "{code}", {profile}, {locale}) selected (_preferences.language == "{code}")')
    return '\n'.join(lines)+'\n'
