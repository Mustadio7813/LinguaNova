# -*- coding: utf-8 -*-
import pickle
import zlib
from pathlib import Path

from src.ui_mod.scanner import read_script_members


def _make_rpa3(path: Path, filename: str, payload: bytes) -> None:
    key = 0
    dummy_header = b"RPA-3.0 0000000000000000 00000000\n"
    data_offset = len(dummy_header)
    index_offset = data_offset + len(payload)
    header = f"RPA-3.0 {index_offset:016x} {key:08x}\n".encode("ascii")
    assert len(header) == len(dummy_header)
    index = {filename: [(data_offset ^ key, len(payload) ^ key, b"")]}
    blob = zlib.compress(pickle.dumps(index, protocol=2))
    path.write_bytes(header + payload + blob)


def test_mod_rpa_scanner_reads_only_script_members(tmp_path: Path):
    rpa = tmp_path / "scripts.rpa"
    _make_rpa3(rpa, "screens.rpy", b'screen menu():\n    text "Start"\n')
    members = read_script_members(rpa)
    assert members == [("screens.rpy", b'screen menu():\n    text "Start"\n')]


def test_visible_rpy_has_priority_over_same_rpa_script(tmp_path: Path):
    from src.ui_mod.scanner import ModProjectScanner

    game = tmp_path / "game"
    game.mkdir()
    (game / "screens.rpy").write_text('screen menu():\n    text "Visible source"\n', encoding="utf-8")
    _make_rpa3(game / "scripts.rpa", "screens.rpy", b'screen menu():\n    text "Archive source"\n')

    report = ModProjectScanner().scan(str(tmp_path))
    texts = set(report.unique_texts())
    assert "Visible source" in texts
    assert "Archive source" not in texts


def test_unreadable_orphan_compiled_scripts_are_counted_not_invented(tmp_path: Path):
    """Since 2026-10-17 orphan .rpyc are read in memory; garbage is reported as unreadable."""
    from src.ui_mod.scanner import ModProjectScanner

    game = tmp_path / "game"
    game.mkdir()
    (game / "paired.rpy").write_text('screen menu():\n    text "Visible source"\n', encoding="utf-8")
    (game / "paired.rpyc").write_bytes(b"compiled paired script")
    (game / "orphan.rpyc").write_bytes(b"orphan compiled script")
    (game / "orphan.rpymc").write_bytes(b"orphan compiled module")

    report = ModProjectScanner().scan(str(tmp_path))

    assert report.visible_rpy_files == 1
    assert report.decompiled_rpyc_files == 0
    assert report.skipped_compiled_files == 2          # orphan.rpyc + orphan.rpymc (garbage)
    assert set(report.unique_texts()) == {"Visible source"}
    assert sorted(p.name for p in game.iterdir()) == ["orphan.rpyc", "orphan.rpymc", "paired.rpy", "paired.rpyc"]
