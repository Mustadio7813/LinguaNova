# -*- coding: utf-8 -*-
from pathlib import Path

from src.ui_mod.parser import ModInterfaceParser
from src.ui_mod.protect import is_junk, preserve_edge_whitespace, protect_mod_text, restore_mod_text, validate_mod_translation
from src.ui_mod.ui_mod_hook_template import render_ui_mod_hook


def test_mod_parser_collects_screen_ui_menu_and_story_dialogue():
    script = r'''
default phone_items = ["Inventory", "Settings", "icons/phone.png"]

screen phone():
    text "Messages"
    textbutton _("Contacts") action NullAction()
    textbutton "Open Map" action NullAction()
    for item in phone_items:
        text item

label start:
    e "This is story dialogue and must enter the game MOD."
    $ dynamic_line = "This is dynamic Python dialogue."
    e dynamic_line
    $ renpy.say(None, "This is a Python say call.")
    $ renpy.notify("Quest updated")
    menu:
        "Open the map":
            pass
'''
    entries = ModInterfaceParser().parse_text(script, "screens.rpy")
    texts = {e.text for e in entries}
    assert "Messages" in texts
    assert "Contacts" in texts
    assert "Open Map" in texts
    assert "Open the map" in texts
    assert "Inventory" in texts
    assert "Settings" in texts
    assert "icons/phone.png" not in texts
    assert "This is story dialogue and must enter the game MOD." in texts
    assert "This is dynamic Python dialogue." in texts
    assert "This is a Python say call." in texts
    assert "Quest updated" in texts


def test_mod_token_guard_is_fail_closed():
    source = "Money: [money] {b}available{/b}"
    protected, mapping = protect_mod_text(source)
    assert "[money]" not in protected
    restored = restore_mod_text(protected.replace("Money", "Dinero"), mapping)
    assert validate_mod_translation(source, restored)
    assert not validate_mod_translation(source, "Dinero disponible")


def test_mod_junk_and_edge_whitespace_guards():
    assert is_junk("A")
    assert is_junk("#FFF")
    assert not is_junk("Inventory")
    assert preserve_edge_whitespace(" \tInventory  \n", "  Inventario \t") == " \tInventario  \n"


def test_mod_hook_is_exclusive_and_chains_previous_replace_text():
    hook = render_ui_mod_hook(
        {"Inventory": "Inventario", "Money: [money]": "Dinero: [money]"},
        {"Inventory": ["inventory"], "Money: [money]": ["hud"]},
        "es",
    )
    assert "src.core.runtime_hook_template" not in hook
    assert "_lnmod_previous_replace_text" in hook
    assert "config.replace_text = _lnmod_replace_text" in hook
    assert "b85decode" not in hook  # readable format since 2026-10-17
    assert '"Inventory": "Inventario",' in hook
    assert "linguanova_mod_hook_data.json" in hook
    assert "_lnmod_compile_template" in hook


def test_rendered_mod_hook_runtime_smoke():
    """Format 4: whole strings go to Ren'Py's native table; replace_text only fills
    printf/{0} templates and otherwise chains the game's previous callback."""
    from src.ui_mod.hook_check import displayed, make_env, python_body
    hook = render_ui_mod_hook(
        {"Inventory": "Inventario", "Money: [money]": "Dinero: [money]", "Coins: %d": "Monedas: %d"},
        {"Inventory": ["inventory"], "Money: [money]": ["hud"], "Coins: %d": ["hud"]},
        "es",
    )
    ns, config, translator, prefs = make_env("es")
    config.replace_text = lambda text: "PREV:" + text
    exec(python_body(hook), ns, ns)
    for callback in config.start_callbacks:
        callback()
    assert displayed(translator, prefs, "Inventory") == "Inventario"
    assert displayed(translator, prefs, "Money: [money]") == "Dinero: [money]"   # before substitution
    assert config.replace_text("Coins: 7") == "PREV:Monedas: 7"     # MOD first, then the game's callback
    assert config.replace_text("Unrelated") == "PREV:Unrelated"
    prefs.language = None                          # original language: game callback only
    assert config.replace_text("Coins: 7") == "PREV:Coins: 7"

def test_mod_parser_collects_global_marked_story_text():
    script = r'''
define ui_labels = [_('Inventory'), _('Settings')]

screen inventory():
    for item in ui_labels:
        text item

label start:
    $ story_line = _("This marked story line must enter MOD.")
    e "[story_line]"
    $ renpy.notify(_("Saved"))
'''
    entries = ModInterfaceParser().parse_text(script, "script.rpy")
    texts = {e.text for e in entries}
    assert "Inventory" in texts
    assert "Settings" in texts
    assert "Saved" in texts
    assert "This marked story line must enter MOD." in texts
    data_entries = [e for e in entries if e.text == "Inventory"]
    assert data_entries and any(e.screen == "inventory" for e in data_entries)


def test_mod_parser_preserves_multiline_text_and_long_multiline_data():
    help_items = [f"Complete help entry {index:03}" for index in range(90)]
    script = (
        'screen help_menu():\n'
        '    text """This complete interface message\n'
        'continues on another source line without being truncated."""\n'
        '    for item in help_items:\n'
        '        text item\n'
        'default help_items = [\n'
        + "".join(f'    {item!r},\n' for item in help_items)
        + ']\n'
    )

    entries = ModInterfaceParser().parse_text(script, "screens.rpy")
    texts = {entry.text for entry in entries}

    assert "This complete interface message\ncontinues on another source line without being truncated." in texts
    assert set(help_items) <= texts



def test_rendered_hook_reloads_external_json_when_active_language_changes():
    """The editable JSON in tl/<lang>/ wins over the embedded copy; languages the
    MOD does not cover are left alone."""
    from src.ui_mod.hook_check import displayed, run_hook
    hook = render_ui_mod_hook(
        {"Inventory": "Fallback inventory"},
        {"Inventory": ["__global_ui__"], "Settings": ["__global_ui__"]},
        "spanish",
    )
    files = {"tl/spanish/linguanova_mod_hook_data.json":
             {"mapping": {"Inventory": "Inventario"}, "contexts": {"Inventory": ["__global_ui__"]}}}
    _ns, _config, translator, prefs = run_hook(hook, "spanish", files)
    assert displayed(translator, prefs, "Inventory") == "Inventario"
    prefs.language = "french"
    assert displayed(translator, prefs, "Inventory") == "Inventory"
    _ns, _config, translator, prefs = run_hook(hook, "spanish", {})
    assert displayed(translator, prefs, "Inventory") == "Fallback inventory"
