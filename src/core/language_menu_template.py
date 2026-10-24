# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova modification: persistent multilingual picker, 2026-10-20.
"""Render the shared in-game picker without importing Qt or any engine client."""

import json
from pathlib import Path
from typing import Dict, List


LANGUAGE_NAMES = {
    "english": "English", "en": "English",
    "spanish": "Español", "es": "Español",
    "french": "Français", "fr": "Français",
    "portuguese": "Português", "pt": "Português",
    "russian": "Русский", "ru": "Русский",
}

RESOURCE_FOLDERS = frozenset({
    "linguanova_fonts", "linguanova_font", "linguanova_mod_fonts",
})
RESOURCE_FILTER_FILE = "zzz_linguanova_ocultar_fuentes.rpy"


def installed_language_folders(game_dir: str) -> List[str]:
    """Actual script-bearing language folders, excluding diagnostic/font folders."""
    root = Path(game_dir) / "tl"
    if not root.is_dir():
        return []
    return sorted(
        path.name for path in root.iterdir()
        if path.is_dir() and path.name.isidentifier() and path.name.casefold() != "none"
        and path.name.casefold() not in RESOURCE_FOLDERS
        and any(item.suffix.lower() in (".rpy", ".rpyc") for item in path.rglob("*"))
    )


def render_resource_filter() -> str:
    """Exclude resource identifiers from menus without touching font loading."""
    template = r'''# SPDX-License-Identifier: GPL-3.0-or-later
# Generated and installed automatically by LinguaNova.
# Font files, paths and translate-python font blocks remain available.

init -999 python:
    # Older Font Injector versions put assets inside tl/linguanova_fonts.
    # Ren'Py also discovers languages from resource paths. Hide ONLY our own
    # resource folders, including from the game's original automatic selector.
    # Keep every font path/file intact; the Russian font continues to work.
    _lntl_resource_folders = set(__LNTL_RESOURCES__)
    if not getattr(renpy.known_languages, '_lntl_resource_filter', False):
        _lntl_original_known_languages = renpy.known_languages

        def _lntl_known_languages():
            return set(code for code in _lntl_original_known_languages()
                       if code and code.lower() not in _lntl_resource_folders)

        _lntl_known_languages._lntl_resource_filter = True
        renpy.known_languages = _lntl_known_languages
'''
    return template.replace("__LNTL_RESOURCES__", json.dumps(sorted(RESOURCE_FOLDERS)))


def install_resource_filter(game_dir: str) -> Path:
    """Publish the protection independently of optional menu integration.

    The translator, font utility and MOD install this themselves. Existing font
    assets and their references are never renamed, moved, hidden or deleted.
    """
    from src.utils.encoding import save_text_safely

    path = Path(game_dir) / RESOURCE_FILTER_FILE
    content = render_resource_filter()
    try:
        previous = path.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, UnicodeDecodeError):
        previous = None
    if previous != content:
        if not save_text_safely(path, content, encoding="utf-8-sig", newline="\n"):
            raise OSError("Could not save the language selector resource filter: " + str(path))
        if path.read_text(encoding="utf-8-sig") != content:
            raise OSError("Language selector resource filter verification failed: " + str(path))
        Path(str(path) + "c").unlink(missing_ok=True)
    return path


def render_language_picker(labels: Dict[str, str], *, show_button: bool = True) -> str:
    """One chooser for every loaded language; Shift+L also works during dialogue.

    Language() is Ren'Py's native action. It handles persistence, rebuilding the
    current translated interaction and restoring the original with Language(None).
    The original game screens and its language defaults are never forced here.
    """
    template = r'''init 950 python:
    _lntl_labels = __LNTL_LABELS__
    _lntl_names = __LNTL_NAMES__
    _lntl_show_button = __LNTL_BUTTON__

    def _lntl_languages():
        try:
            known = list(renpy.known_languages())
        except Exception:
            known = list(_lntl_labels)
        rows = []
        seen = set()
        for code in known:
            if not code or code == "None" or code.lower() in _lntl_resource_folders:
                continue
            if code in seen:
                continue
            seen.add(code)
            name = _lntl_labels.get(code) or _lntl_names.get(code.lower())
            rows.append((code, name or code.replace('_', ' ').title()))
        return sorted(rows, key=lambda row: (row[1].lower(), row[0]))

    def _lntl_mod_present():
        try:
            return renpy.has_screen('lnmod_language_panel')
        except Exception:
            return False

    _lntl_button_in_menus = hasattr(config, 'always_shown_screens')

    def _lntl_button_visible():
        if not _lntl_show_button or _lntl_mod_present():
            return False
        if getattr(persistent, '_lntl_hide_button', False):
            return False
        if not _lntl_button_in_menus:
            return True
        names = globals()
        return bool(names.get('main_menu', False) or names.get('_menu', False))

    # Always-shown screens keep the hotkey active in gameplay and in menus.
    # Older Ren'Py builds use the normal gameplay overlay instead.
    if _lntl_button_in_menus:
        if 'lntl_language_button' not in config.always_shown_screens:
            config.always_shown_screens.append('lntl_language_button')
    elif 'lntl_language_button' not in config.overlay_screens:
        config.overlay_screens.append('lntl_language_button')

screen lntl_language_preferences():
    vbox:
        style_prefix "radio"
        label _("Language")
        textbutton _("Original") action Language(None)
        for _lntl_code, _lntl_label in _lntl_languages():
            textbutton _lntl_label action Language(_lntl_code)

screen lntl_language_button():
    zorder 189
    if not _lntl_mod_present():
        key "shift_K_l" action ToggleScreen("lntl_language_panel")
    if _lntl_button_visible() and not renpy.get_screen("lntl_language_panel"):
        textbutton "Idioma / Language":
            xalign 1.0
            yalign 1.0
            xoffset -12
            yoffset -12
            background Solid("#12161fcc")
            hover_background Solid("#2b3648ee")
            padding (14, 8, 14, 8)
            text_size max(14, int(config.screen_height * 0.022))
            text_color "#e6eaf2"
            action Show("lntl_language_panel")

screen lntl_language_panel():
    modal True
    zorder 191
    key "game_menu" action Hide("lntl_language_panel")
    key "shift_K_l" action Hide("lntl_language_panel")
    add Solid("#000000a0")
    frame:
        xalign 0.5
        yalign 0.5
        xsize min(config.screen_width - 32, max(320, int(config.screen_width * 0.42)))
        background Solid("#12161ff2")
        padding (int(config.screen_height * 0.03), int(config.screen_height * 0.025))
        vbox:
            spacing max(8, int(config.screen_height * 0.012))
            text "Idioma / Language" size max(18, int(config.screen_height * 0.036)) color "#e6eaf2"
            text "Shift+L" size max(12, int(config.screen_height * 0.02)) color "#9aa3b7"
            viewport:
                ysize int(config.screen_height * 0.52)
                mousewheel True
                draggable True
                scrollbars "vertical"
                vbox:
                    spacing max(6, int(config.screen_height * 0.01))
                    textbutton "Original":
                        action Language(None)
                        selected (_preferences.language is None)
                        text_size max(14, int(config.screen_height * 0.026))
                        text_color "#e6eaf2"
                        text_selected_color "#4c8dff"
                        text_hover_color "#ffffff"
                    for _lntl_code, _lntl_label in _lntl_languages():
                        textbutton _lntl_label:
                            action Language(_lntl_code)
                            selected (_preferences.language == _lntl_code)
                            text_size max(14, int(config.screen_height * 0.026))
                            text_color "#e6eaf2"
                            text_selected_color "#4c8dff"
                            text_hover_color "#ffffff"
            textbutton "Cerrar / Close":
                action Hide("lntl_language_panel")
                text_size max(12, int(config.screen_height * 0.02))
                text_color "#9aa3b7"
                text_hover_color "#ffffff"
'''
    return render_resource_filter() + "\n" + (
        template.replace("__LNTL_LABELS__", json.dumps(labels, ensure_ascii=False, sort_keys=True))
        .replace("__LNTL_NAMES__", json.dumps(LANGUAGE_NAMES, ensure_ascii=False, sort_keys=True))
        .replace("__LNTL_BUTTON__", str(bool(show_button)))
    )
