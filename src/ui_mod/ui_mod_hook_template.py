# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# MOD
# #MOD — runtime hook exclusively owned by the standalone MOD subsystem.
"""Render ``game/linguanova_mod_<game>_multilang.rpy`` (format v4).

How the generated file translates (verified against Ren'Py's own source,
``renpy/translation/__init__.py``, ``renpy/substitutions.py`` and
``renpy/character.py``):

* Every text Ren'Py displays — screen text, menu choices and dialogue that has no
  native ``translate`` block — goes through ``renpy.translation.translate_string``
  with the WHOLE string (text tags and ``[variables]`` included) before tags are
  split. The hook registers the MOD's translations in that native table at
  ``config.start_callbacks`` time, after every game ``translate ... strings``
  block has run, and skips strings the game already translates — so no duplicate
  ``old`` can ever raise Ren'Py's "A translation for ... already exists" error.
  Lines with ``{b}``/``{color}`` tags are translated whole, never in pieces.
* ``config.replace_text`` is only a fallback for printf/format templates built at
  runtime ("Dinero: %d" shown as "Dinero: 30"), always on the whole token.
* Fonts: ``translate <language> python`` blocks (run by Ren'Py on every language
  change) update ``config.font_replacement_map`` so only the game fonts that lack
  the language's characters are swapped; the rest keep the game's look.
* An in-game button + panel lists the languages and switches them live with
  Ren'Py's ``Language()`` action.

The data is readable (one ``"original": "translation",`` line per entry) and the
runtime code runs on Ren'Py 7 (Python 2.7) and Ren'Py 8 (Python 3).
"""
from __future__ import annotations

import json
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

MOD_HOOK_ID = "linguanova_interface_mod"
MOD_HOOK_STATUS = "functional_isolated"
MOD_HOOK_FORMAT = 4

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MOD_PANEL_LABELS = {
    "english": {
        "button": "Language",
        "title": "Choose language",
        "original": "Original",
        "show_button": "Show button in menus",
        "hide_button": "Hide button (Shift+L)",
        "close": "Close",
    },
    "spanish": {
        "button": "Idioma",
        "title": "Elegir idioma",
        "original": "Original",
        "show_button": "Mostrar botón en los menús",
        "hide_button": "Ocultar botón (Mayús+L)",
        "close": "Cerrar",
    },
    "french": {
        "button": "Langue",
        "title": "Choisir la langue",
        "original": "Original",
        "show_button": "Afficher le bouton dans les menus",
        "hide_button": "Masquer le bouton (Maj+L)",
        "close": "Fermer",
    },
    "portuguese": {
        "button": "Idioma",
        "title": "Escolher idioma",
        "original": "Original",
        "show_button": "Mostrar botão nos menus",
        "hide_button": "Ocultar botão (Shift+L)",
        "close": "Fechar",
    },
    "russian": {
        "button": "Язык",
        "title": "Выбрать язык",
        "original": "Оригинал",
        "show_button": "Показывать кнопку в меню",
        "hide_button": "Скрыть кнопку (Shift+L)",
        "close": "Закрыть",
    },
}


def mod_hook_is_isolated() -> bool:
    return True


def _literal(value) -> str:
    # JSON syntax is a valid Python 2/3 literal for str/int/list/dict; non-ASCII stays readable.
    return json.dumps(value, ensure_ascii=False)


def _render_language(lines: List[str], language: str, data: Mapping[str, Mapping]) -> None:
    mapping = data.get("mapping") or {}
    contexts = data.get("contexts") or {}
    lines.append(f"        {_literal(language)}: {{")
    lines.append('            "mapping": {')
    for source in sorted(mapping, key=lambda s: (s.casefold(), s)):
        lines.append(f"                {_literal(source)}: {_literal(mapping[source])},")
    lines.append("            },")
    lines.append('            "contexts": {')
    for source in sorted(contexts, key=lambda s: (s.casefold(), s)):
        screens = ", ".join(_literal(str(s)) for s in contexts[source])
        lines.append(f"                {_literal(source)}: [{screens}],")
    lines.append("            },")
    lines.append("        },")


def _dict_block(name: str, comment: str, value: Mapping) -> str:
    lines = [f"    # {comment}", f"    {name} = {{"]
    for key in sorted(value, key=lambda k: str(k)):
        lines.append(f"        {_literal(key)}: {_literal(value[key])},")
    lines.append("    }")
    return "\n".join(lines) + "\n"


def render_ui_mod_hook_multi(
    languages: Mapping[str, Mapping[str, Mapping]],
    default_language: Optional[str],
    aliases: Optional[Mapping[str, Iterable[str]]] = None,
    header_notes: Iterable[str] = (),
    *,
    labels: Optional[Mapping[str, str]] = None,
    stats: Optional[Mapping[str, Sequence[int]]] = None,
    fonts: Optional[Mapping[str, Mapping[str, str]]] = None,
    rtl_languages: Iterable[str] = (),
    other_languages: Iterable[str] = (),
    other_labels: Optional[Mapping[str, str]] = None,
) -> str:
    """Render the hook for every language in ``languages`` ({folder: {mapping, contexts}}).

    ``default_language`` is offered to NEW players (``config.default_language``) when
    the game sets none; the original language always stays untranslated.
    ``fonts`` = {folder: {game_font: mod_font}} for fonts lacking the language's glyphs.
    ``other_languages`` = the game's own tl/ languages (fonts are reset for them).
    """
    alias_map: Dict[str, List[str]] = {}
    for language in sorted(languages):
        names = [language] + [a for a in (aliases or {}).get(language, ()) if a != language]
        alias_map[language] = list(dict.fromkeys(names))
    data_lines: List[str] = []
    for language in sorted(languages):
        _render_language(data_lines, language, languages[language])
    notes = "".join(f"# {note}\n" for note in header_notes)
    counts = ", ".join(
        f"{lang}={len((languages[lang] or {}).get('mapping') or {})}" for lang in sorted(languages)
    ) or "ninguno"
    label_map = {lang: (labels or {}).get(lang, lang) for lang in sorted(languages)}
    # The game's own tl/ languages (and a tl/ folder made by the Translation
    # flow) are offered in the same panel, by their visible name.
    extra_label_map = {lang: (other_labels or {}).get(lang, lang)
                       for lang in sorted(set(other_languages) - set(languages)) if lang}
    stat_map = {lang: list((stats or {}).get(lang, [len((languages[lang] or {}).get("mapping") or {}), 0, 0]))
                for lang in sorted(languages)}
    font_map = {lang: dict((fonts or {}).get(lang, {})) for lang in sorted(languages)}
    rtl = sorted(set(rtl_languages) & set(languages))

    # translate <language> python blocks: every known language (incl. None) re-applies
    # its own font plan, so switching away from a MOD language restores the game fonts.
    font_switch_langs = sorted(
        {lang for lang in languages if _IDENTIFIER_RE.match(lang)}
        | {lang for lang in other_languages if _IDENTIFIER_RE.match(lang or "")}
    )
    callback_langs = sorted(
        {lang for lang in list(languages) + list(other_languages) if lang and not _IDENTIFIER_RE.match(lang)}
    )
    translate_blocks = "".join(
        f"translate {lang} python:\n    _lnmod_apply_fonts({_literal(lang)})\n\n" for lang in font_switch_langs
    ) + "translate None python:\n    _lnmod_apply_fonts(None)\n"

    return (
        "# LinguaNova MOD — traducción multilenguaje (formato legible v4)\n"
        "# Archivo generado por LinguaNova. No modifica los scripts del juego.\n"
        "# Registra las traducciones en la tabla NATIVA de Ren'Py al iniciar el juego:\n"
        "# cada frase se traduce completa (con {b}, {color} y [variables]), igual que\n"
        "# en un juego traducido oficialmente. Nunca duplica traducciones que el juego\n"
        "# ya tenga, así que no provoca el error \"A translation for ... already exists\".\n"
        "#\n"
        "# CÓMO CORREGIR UNA TRADUCCIÓN (recomendado):\n"
        "#   Edita game/tl/<idioma>/linguanova_mod_manual.json, sección \"mapping\":\n"
        "#       \"texto original\": \"tu traducción\",\n"
        "#   Se aplica al reiniciar el juego y LinguaNova la respeta al regenerar.\n"
        "#\n"
        "# Orden de prioridad al jugar: 1) linguanova_mod_manual.json\n"
        "#   2) linguanova_mod_hook_data.json  3) la copia escrita en este archivo.\n"
        "# Si editas las líneas de abajo, el cambio solo se ve cuando no existen los JSON\n"
        "# y se pierde al regenerar. Un error de sintaxis aquí (comilla o coma faltante)\n"
        "# impide que Ren'Py arranque; los JSON, en cambio, se ignoran si están dañados.\n"
        "#\n"
        "# EN EL JUEGO: botón \"Idioma\" abajo a la derecha en los menús (o Mayús+L en\n"
        "# cualquier momento) para cambiar de idioma al instante. El idioma original del\n"
        "# juego siempre queda sin traducir. El jugador no ve contadores ni porcentajes.\n"
        f"# Entradas por idioma: {counts}\n"
        f"{notes}"
        "\n"
        "init 990 python:\n"
        "    import json as _lnmod_json\n"
        "    import re as _lnmod_re\n"
        "\n"
        "    # Idioma que verá un jugador NUEVO la primera vez (None = idioma original).\n"
        "    # Solo se aplica si el juego no define config.default_language.\n"
        f"    _lnmod_default_language = {_literal(default_language) if default_language else 'None'}\n"
        "\n"
        + _dict_block("_lnmod_language_aliases", "Carpetas tl/ aceptadas para cada idioma.", alias_map)
        + "\n"
        + _dict_block("_lnmod_labels", "Nombre que muestra el panel de idiomas.", label_map)
        + "\n"
        + _dict_block("_lnmod_ui_labels", "Textos del selector traducidos por idioma.", _MOD_PANEL_LABELS)
        + "\n"
        + _dict_block("_lnmod_extra_labels", "Otros idiomas tl/ del juego (nombre visible).", extra_label_map)
        + "\n"
        + _dict_block("_lnmod_stats", "[traducidos, total, pendientes] según la última generación.", stat_map)
        + "\n"
        + _dict_block("_lnmod_fonts", "Fuente del juego sin los caracteres del idioma -> fuente que la sustituye.", font_map)
        + "\n"
        f"    _lnmod_rtl_languages = {_literal(rtl)}\n"
        "    # Idiomas cuyo nombre no sirve para 'translate X python' (p. ej. pt-br).\n"
        f"    _lnmod_callback_languages = {_literal(callback_langs)}\n"
        "\n"
        "    # Copia embebida: \"original\": \"traducción\" por línea.\n"
        "    _lnmod_embedded = {\n"
        + "\n".join(data_lines) + ("\n" if data_lines else "")
        + "    }\n"
        + _RUNTIME
        + _SCREENS
        + "\n"
        + translate_blocks
    )


def render_ui_mod_hook(mapping: Dict[str, str], contexts: Dict[str, List[str]], target_code: str) -> str:
    """Single-language compatibility wrapper (kept for existing callers/tests)."""
    return render_ui_mod_hook_multi(
        {target_code: {"mapping": dict(mapping), "contexts": dict(contexts)}}, target_code
    )


def python_body(rpy_text: str) -> str:
    """The ``init 990 python`` block of a rendered hook as plain Python (for checks/tests)."""
    lines = rpy_text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("init ")) + 1
    body: List[str] = []
    for line in lines[start:]:
        if line and not line.startswith((" ", "\t", "#")):
            break  # first Ren'Py statement after the python block (screens, translate ...)
        body.append(line[4:] if line.startswith("    ") else line)
    return "\n".join(body)


_RUNTIME = r'''
    try:
        _lnmod_text_types = (str, unicode)
    except NameError:
        _lnmod_text_types = (str,)

    _lnmod_cache = {"language": None, "data": None, "templates": None}
    _lnmod_registered = {}
    _lnmod_previous_replace_text = getattr(config, "replace_text", None)

    def _lnmod_log(message):
        logger = getattr(renpy, "log", None)
        if callable(logger):
            logger("[LinguaNova MOD] " + str(message))

    def _lnmod_current_language():
        # Idioma elegido en el juego (Preferencias > Idioma); None = idioma original.
        try:
            language = renpy.game.preferences.language
        except Exception:
            language = None
        return language or None

    def _lnmod_resolve(language):
        # Traduce el nombre de idioma del juego a la clave usada en este archivo.
        if not language:
            return None
        if language in _lnmod_embedded:
            return language
        folded = str(language).strip().lower().replace("-", "_")
        for key, names in _lnmod_language_aliases.items():
            if folded == key.lower() or folded in names:
                return key
        return None

    def _lnmod_ui_text(key):
        # El selector se muestra en el idioma elegido, no en el idioma de la app.
        language = _lnmod_resolve(_lnmod_current_language())
        labels = _lnmod_ui_labels.get(language or "", _lnmod_ui_labels["english"])
        return labels.get(key, _lnmod_ui_labels["english"].get(key, key))

    def _lnmod_valid(data):
        return isinstance(data, dict) and isinstance(data.get("mapping"), dict) \
            and isinstance(data.get("contexts"), dict)

    def _lnmod_read_json(path):
        # Lee un JSON del juego; devuelve None si falta o está dañado (nunca detiene el juego).
        try:
            stream = renpy.loader.load(path)
            try:
                return _lnmod_json.loads(stream.read().decode("utf-8"))
            finally:
                stream.close()
        except Exception:
            return None

    def _lnmod_with_manual(data, folders):
        # Superpone las correcciones manuales (linguanova_mod_manual.json) sobre los datos.
        for folder in folders:
            manual = _lnmod_read_json("tl/" + folder + "/linguanova_mod_manual.json")
            if isinstance(manual, dict) and isinstance(manual.get("mapping"), dict) and manual["mapping"]:
                mapping = dict(data.get("mapping", {}))
                contexts = dict(data.get("contexts", {}))
                for source, target in manual["mapping"].items():
                    if isinstance(source, _lnmod_text_types) and isinstance(target, _lnmod_text_types) and target.strip():
                        mapping[source] = target
                        contexts.setdefault(source, ["__global_ui__"])
                return {"mapping": mapping, "contexts": contexts}
        return data

    def _lnmod_load_base(key, folders):
        # Datos activos: primero el JSON de tl/<idioma>/, si no, la copia embebida.
        for folder in folders:
            data = _lnmod_read_json("tl/" + folder + "/linguanova_mod_hook_data.json")
            if _lnmod_valid(data):
                return data
        if key and _lnmod_valid(_lnmod_embedded.get(key)):
            return _lnmod_embedded[key]
        return {"mapping": {}, "contexts": {}}

    def _lnmod_load(language):
        key = _lnmod_resolve(language)
        if key is None:
            return {"mapping": {}, "contexts": {}}
        folders = list(_lnmod_language_aliases.get(key, [key]))
        return _lnmod_with_manual(_lnmod_load_base(key, folders), folders)

    def _lnmod_register_strings():
        # Registra cada traducción en la tabla nativa de Ren'Py (frase completa).
        # Se ejecuta al iniciar el juego, después de todos los bloques
        # "translate ... strings" del juego, y salta los textos que el juego ya
        # traduce: nunca hay dos traducciones del mismo texto.
        try:
            translator = renpy.game.script.translator
        except Exception as error:
            _lnmod_log("Native string table unavailable: " + str(error))
            return
        for key in _lnmod_embedded:
            added = 0
            kept = 0
            try:
                table = translator.strings[key]
                translator.languages.add(key)
            except Exception as error:
                _lnmod_log("Cannot open string table for " + key + ": " + str(error))
                continue
            existing = getattr(table, "translations", {})
            for source, target in _lnmod_load(key).get("mapping", {}).items():
                if not isinstance(source, _lnmod_text_types) or not isinstance(target, _lnmod_text_types):
                    continue
                if source in existing:
                    current = existing.get(source)
                    # A native entry that only repeats the original (or is
                    # empty) is not a translation: Ren'Py would show "Skip"
                    # while the MOD has "Saltar". Replace just those.
                    if isinstance(existing, dict) and (not current or current == source):
                        existing[source] = target
                        added += 1
                    else:
                        kept += 1
                    continue
                try:
                    try:
                        table.add(source, target, None)
                    except TypeError:
                        table.add(source, target)
                    added += 1
                except Exception as error:
                    kept += 1
                    _lnmod_log("Skipped one string for " + key + ": " + str(error))
            _lnmod_registered[key] = (added, kept)
        _lnmod_cache["language"] = None

    _lnmod_field = _lnmod_re.compile(
        r"%\([A-Za-z_]\w*\)[#0\- +]?\d*(?:\.\d+)?[diouxXeEfFgGcrs]"
        r"|%[#0\- +]?\d*(?:\.\d+)?[diouxXeEfFgGcrs]|\{\d*\}"
    )

    def _lnmod_compile_templates(data):
        # Textos armados en tiempo de ejecución ("Dinero: %d" -> "Dinero: 30",
        # "{0} monedas" -> "30 monedas"): se reconocen con cualquier valor,
        # siempre sobre la frase completa, nunca sobre un trozo.
        templates = []
        for source, destination in data.get("mapping", {}).items():
            if "%" not in source and "{" not in source:
                continue
            parts = []
            tokens = []
            position = 0
            for match in _lnmod_field.finditer(source):
                parts.append(_lnmod_re.escape(source[position:match.start()]))
                parts.append("(.+?)")
                tokens.append(match.group(0))
                position = match.end()
            if not tokens:
                continue
            parts.append(_lnmod_re.escape(source[position:]))
            try:
                pattern = _lnmod_re.compile("^" + "".join(parts) + "$", _lnmod_re.DOTALL)
            except Exception:
                continue
            templates.append((pattern, tokens, destination))
        return templates

    def _lnmod_data():
        language = _lnmod_resolve(_lnmod_current_language())
        if _lnmod_cache["language"] != language or _lnmod_cache["data"] is None:
            data = _lnmod_load(language) if language else {"mapping": {}, "contexts": {}}
            _lnmod_cache["language"] = language
            _lnmod_cache["data"] = data
            _lnmod_cache["templates"] = _lnmod_compile_templates(data)
        return _lnmod_cache["data"], _lnmod_cache["templates"]

    def _lnmod_apply(text):
        # Solo plantillas completas: los textos fijos ya los traduce la tabla nativa.
        data, templates = _lnmod_data()
        for pattern, tokens, destination in templates:
            match = pattern.match(text)
            if match is None:
                continue
            output = destination
            for index, token in enumerate(tokens, 1):
                output = output.replace(token, match.group(index), 1)
            return output
        return None

    def _lnmod_replace_text(text):
        # Punto de entrada de Ren'Py. Cualquier error se registra en log.txt y se
        # muestra el texto original: el juego nunca se cierra por culpa del MOD.
        try:
            if isinstance(text, _lnmod_text_types) and text and _lnmod_resolve(_lnmod_current_language()):
                translated = _lnmod_apply(text)
                if translated is not None:
                    text = translated
        except Exception as error:
            _lnmod_log("Text replacement failed: " + str(error))
        if _lnmod_previous_replace_text is not None:
            return _lnmod_previous_replace_text(text)
        return text

    # ── Fuentes por idioma ────────────────────────────────────────────────
    _lnmod_font_keys = []

    def _lnmod_apply_fonts(language):
        # Quita las sustituciones del idioma anterior y aplica las del nuevo.
        try:
            table = config.font_replacement_map
            for old_key in _lnmod_font_keys:
                table.pop(old_key, None)
            del _lnmod_font_keys[:]
            plan = _lnmod_fonts.get(_lnmod_resolve(language) or "", {})
            for game_font, mod_font in plan.items():
                for bold in (False, True):
                    for italics in (False, True):
                        key = (game_font, bold, italics)
                        if key not in table:
                            table[key] = (mod_font, bold, italics)
                            _lnmod_font_keys.append(key)
        except Exception as error:
            _lnmod_log("Font switch failed: " + str(error))

    # ── Panel de idiomas ───────────────────────────────────────────────────
    def _lnmod_menu_languages():
        # [(idioma, nombre visible)] para el panel. Las cifras de cobertura
        # quedan en linguanova_mod_report.json: el jugador no ve contadores.
        rows = [(key, _lnmod_labels.get(key, key))
                for key in sorted(_lnmod_embedded, key=lambda k: _lnmod_labels.get(k, k))]
        try:
            known = set(renpy.known_languages())
        except Exception:
            known = set(_lnmod_extra_labels)
        extra = [(key, label) for key, label in _lnmod_extra_labels.items()
                 if key in known and key not in _lnmod_embedded]
        return rows + sorted(extra, key=lambda row: row[1].lower())

    # Ren'Py oculta las "overlay screens" dentro de los menús (suppress_overlay).
    # Con config.always_shown_screens (Ren'Py 8) el botón vive en los menús
    # (principal / juego), como una opción más, y durante la partida basta con
    # Mayús+L. En versiones sin esa opción se mantiene el botón en la partida.
    _lnmod_button_in_menus = hasattr(config, "always_shown_screens")

    def _lnmod_show_button():
        if getattr(persistent, "_lnmod_hide_button", False):
            return False
        if not _lnmod_button_in_menus:
            return True
        try:
            names = globals()
            return bool(names.get("main_menu", False) or names.get("_menu", False))
        except Exception:
            return False

    # ── Activación ──────────────────────────────────────────────────────────
    if _lnmod_rtl_languages and hasattr(config, "rtl"):
        config.rtl = True
    if _lnmod_default_language and hasattr(config, "default_language") \
            and config.default_language is None:
        config.default_language = _lnmod_default_language
    if hasattr(config, "language_callbacks"):
        for _lnmod_lang in _lnmod_callback_languages:
            config.language_callbacks[_lnmod_lang].append(
                (lambda _l=_lnmod_lang: _lnmod_apply_fonts(_l)))
    if _lnmod_register_strings not in config.start_callbacks:
        config.start_callbacks.append(_lnmod_register_strings)
    config.replace_text = _lnmod_replace_text
    if _lnmod_button_in_menus:
        if "lnmod_language_button" not in config.always_shown_screens:
            config.always_shown_screens.append("lnmod_language_button")
    elif "lnmod_language_button" not in config.overlay_screens:
        config.overlay_screens.append("lnmod_language_button")
'''


_SCREENS = r'''

# ---------------------------------------------------------------------------
# Panel de idiomas (botón abajo a la derecha o Mayús+L). Cambia el idioma al
# instante con la acción nativa Language(); no modifica las pantallas del juego.
# ---------------------------------------------------------------------------

screen lnmod_language_button():
    zorder 190
    key "shift_K_l" action ToggleScreen("lnmod_language_panel")
    if _lnmod_show_button() and not renpy.get_screen("lnmod_language_panel"):
        textbutton _lnmod_ui_text("button"):
            xalign 1.0
            yalign 1.0
            xoffset -12
            yoffset -12
            background Solid("#12161fcc")
            hover_background Solid("#2b3648ee")
            padding (14, 8, 14, 8)
            text_size max(14, int(config.screen_height * 0.022))
            text_color "#e6eaf2"
            action Show("lnmod_language_panel")

screen lnmod_language_panel():
    modal True
    zorder 191
    key "game_menu" action Hide("lnmod_language_panel")
    key "shift_K_l" action Hide("lnmod_language_panel")
    add Solid("#000000a0")
    frame:
        xalign 0.5
        yalign 0.5
        xminimum int(config.screen_width * 0.36)
        background Solid("#12161ff2")
        padding (int(config.screen_height * 0.03), int(config.screen_height * 0.025))
        vbox:
            spacing int(config.screen_height * 0.012)
            text _lnmod_ui_text("title") size max(18, int(config.screen_height * 0.036)) color "#e6eaf2"
            null height int(config.screen_height * 0.01)
            textbutton _lnmod_ui_text("original"):
                action Language(None)
                selected (_preferences.language is None)
                text_size max(14, int(config.screen_height * 0.026))
                text_color "#e6eaf2"
                text_selected_color "#4c8dff"
                text_hover_color "#ffffff"
            viewport:
                ymaximum int(config.screen_height * 0.55)
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing int(config.screen_height * 0.008)
                    for _lnmod_lang, _lnmod_label in _lnmod_menu_languages():
                        textbutton _lnmod_label:
                            action Language(_lnmod_lang)
                            selected (_preferences.language == _lnmod_lang)
                            text_size max(14, int(config.screen_height * 0.026))
                            text_color "#e6eaf2"
                            text_selected_color "#4c8dff"
                            text_hover_color "#ffffff"
            null height int(config.screen_height * 0.01)
            hbox:
                spacing int(config.screen_width * 0.02)
                textbutton (_lnmod_ui_text("show_button") if getattr(persistent, "_lnmod_hide_button", False)
                            else _lnmod_ui_text("hide_button")):
                    action ToggleField(persistent, "_lnmod_hide_button")
                    text_size max(12, int(config.screen_height * 0.02))
                    text_color "#9aa3b7"
                    text_hover_color "#ffffff"
                textbutton _lnmod_ui_text("close"):
                    action Hide("lnmod_language_panel")
                    text_size max(12, int(config.screen_height * 0.02))
                    text_color "#9aa3b7"
                    text_hover_color "#ffffff"
'''
