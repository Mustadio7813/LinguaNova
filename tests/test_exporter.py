# -*- coding: utf-8 -*-

import json
from pathlib import Path

from src.core.exporter import export_strings_to_rpy, _unescape_rpy


def _prepare_tl_dir(tmp_path: Path) -> tuple[Path, Path]:
    project_dir = tmp_path / "project"
    game_dir = project_dir / "game"
    tl_dir = game_dir / "tl" / "turkish"
    tl_dir.mkdir(parents=True)
    return project_dir, tl_dir


def test_exporter_accepts_project_root_and_skips_existing_entries(tmp_path: Path) -> None:
    project_dir, tl_dir = _prepare_tl_dir(tmp_path)
    (tl_dir / "strings.json").write_text(
        json.dumps({"Hello": "Merhaba", "Bye": "Gule gule"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tl_dir / "existing.rpy").write_text(
        'translate turkish strings:\n    old "Hello"\n    new "Merhaba"\n',
        encoding="utf-8-sig",
    )

    assert export_strings_to_rpy(str(project_dir), "turkish") is True

    exported_path = tl_dir / "zz_rl_exported_turkish.rpy"
    exported_text = exported_path.read_text(encoding="utf-8-sig")
    assert 'old "Bye"' in exported_text
    assert 'old "Hello"' not in exported_text


def test_exporter_accepts_game_directory_without_double_game_path(tmp_path: Path) -> None:
    project_dir, tl_dir = _prepare_tl_dir(tmp_path)
    (tl_dir / "strings.json").write_text(
        json.dumps({"Ready": "Hazir"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assert export_strings_to_rpy(str(project_dir / "game"), "turkish") is True
    assert (tl_dir / "zz_rl_exported_turkish.rpy").exists()


def test_unescape_rpy_roundtrips_literal_backslashes() -> None:
    # A literal backslash followed by "n"/"t" must survive as backslash+n/t,
    # not collapse into a real newline/tab (single-pass, order-independent).
    assert _unescape_rpy(r"A\\nB") == "A\\nB"      # escaped backslash + n
    assert _unescape_rpy(r"A\nB") == "A\nB"        # real newline
    assert _unescape_rpy(r"A\\tB") == "A\\tB"      # escaped backslash + t
    assert _unescape_rpy('A\\"B') == 'A"B'         # escaped quote
    assert _unescape_rpy(r"A\\B") == "A\\B"        # escaped backslash


def test_exporter_dedups_strings_with_literal_backslashes(tmp_path: Path) -> None:
    project_dir, tl_dir = _prepare_tl_dir(tmp_path)
    source = "A\\nB"  # A, backslash, n, B — NOT a newline
    (tl_dir / "strings.json").write_text(
        json.dumps({source: "X"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Existing tl file already carries the same entry as an escaped Ren'Py literal.
    (tl_dir / "existing.rpy").write_text(
        'translate turkish strings:\n    old "A\\\\nB"\n    new "X"\n',
        encoding="utf-8-sig",
    )

    assert export_strings_to_rpy(str(project_dir), "turkish") is True
    # Dedup must recognize the existing entry; nothing is re-exported.
    assert not (tl_dir / "zz_rl_exported_turkish.rpy").exists()
