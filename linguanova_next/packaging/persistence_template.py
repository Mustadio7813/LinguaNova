"""Generated player code uses only Ren'Py APIs and native persistent types."""


def render_persistence():
    return r"""
init 950 python:
    def _ln_next_language_caption():
        return {"spanish_latam": u"Idioma", "spanish_spain": u"Idioma", "spanish": u"Idioma",
                "french": u"Langue", "portuguese": u"Idioma", "russian": u"Язык",
                "english": u"Language"}.get(_preferences.language, _("Language"))

    def _ln_next_original_caption():
        return u"Оригинал" if _preferences.language == "russian" else _("Original")

    def _ln_next_choose_language(code, profile_id="", locale=""):
        # Apply first. A failing language switch must not save a false choice.
        renpy.change_language(code)
        persistent.linguanova_language_choice = {
            "schema_version": 1, "selected": True, "renpy_id": code,
            "profile_id": profile_id, "locale": locale,
        }
        renpy.save_persistent()
        renpy.restart_interaction()

    def _ln_next_restore_language():
        choice = getattr(persistent, "linguanova_language_choice", None)
        if not isinstance(choice, dict) or not choice.get("selected", False):
            return
        code = choice.get("renpy_id")
        if code is None or code in renpy.known_languages():
            # Explicit Original (None) differs from an absent choice.
            config.language = None
            renpy.change_language(code)

    if _ln_next_restore_language not in config.start_callbacks:
        config.start_callbacks.append(_ln_next_restore_language)
"""
