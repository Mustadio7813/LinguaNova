# SPDX-License-Identifier: GPL-3.0-or-later
"""Static contract checks for the editable standalone source build."""
from pathlib import Path


def test_user_visible_source_words_do_not_use_backslash_apostrophe():
    roots = [
        Path("src/gui/qml/Main.qml"),
        Path("src/cli_main.py"),
    ]
    for path in roots:
        text = path.read_text(encoding="utf-8")
        assert "Ren\\'Py" not in text
        assert "game\\'s" not in text
