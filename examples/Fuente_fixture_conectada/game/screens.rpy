# Controlled fixture. Deliberate public extension slot, not a real game's UI.
screen linguanova_preferences_languages():
    null height 0

screen main_menu():
    tag menu
    add Solid("#101820")
    frame:
        background Solid("#17252c")
        xalign 0.08
        yalign 0.5
        padding (28, 22)
        vbox:
            spacing 14
            text "LINGUANOVA FIXTURE" color "#b8f36b"
            textbutton _("Start") action Start()
            textbutton _("Preferences") action ShowMenu("preferences")
            textbutton _("Quit") action Quit(confirm=False)

screen preferences():
    tag menu
    add Solid("#101820")
    frame:
        background Solid("#17252c")
        xalign 0.08
        yalign 0.5
        padding (28, 22)
        vbox:
            spacing 10
            text _("Preferences") color "#b8f36b"
            use linguanova_preferences_languages
            textbutton _("Return") action Return()
