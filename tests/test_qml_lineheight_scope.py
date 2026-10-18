# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression guard for QML Text.lineHeight placement."""

from pathlib import Path


def test_wrapped_settings_descriptions_keep_lineheight_inside_label():
    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")

    keys = (
        "activate_language_desc",
        "multi_endpoint_desc",
        "parallel_batch_desc",
        "rpyc_reader_desc",
        "stateful_lexer_desc",
    )

    for key in keys:
        pos = qml.index(key)
        # These descriptions are intentionally one-line Label declarations.
        line_start = qml.rfind("\n", 0, pos) + 1
        line_end = qml.find("\n", pos)
        line = qml[line_start:line_end]
        assert "Label {" in line
        assert "lineHeight: 1.15" in line
        assert line.rstrip().endswith("}")

    # No standalone lineHeight must appear immediately after an inline Label.
    lines = qml.splitlines()
    for i, line in enumerate(lines[:-1]):
        if "Label {" in line and line.rstrip().endswith("}"):
            assert lines[i + 1].strip() != "lineHeight: 1.15"
