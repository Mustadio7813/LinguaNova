from src.core.language_menu_template import installed_language_folders, install_resource_filter, RESOURCE_FOLDERS


def installed_languages(game):
    return installed_language_folders(str(game))


def protect_resources(staging_game):
    # Only the compatible resource filter is used. Neither legacy picker nor
    # create_language_menu_integration is called or post-processed.
    return install_resource_filter(str(staging_game))
