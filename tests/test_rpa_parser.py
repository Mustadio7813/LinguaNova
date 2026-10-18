# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
"""
Tests for rpa_parser.py — native RPA archive extraction + security hardening.

Covers:
  - _RestrictedRPAUnpickler.find_class() allowlist / security blocking
  - _safe_loads_rpa_index() restricted path + graceful fallback
  - End-to-end RPA-3.0 archive round-trip extraction
"""

import io
import os
import pickle
import zlib
from pathlib import Path

import pytest

from src.utils.rpa_parser import (
    RPAParser,
    _RestrictedRPAUnpickler,
    _safe_loads_rpa_index,
    _archive_index_keystream,
    _archive_index_xor,
    extract_rpa,
)


# ============================================================================
# Restricted unpickler — allowlist + security
# ============================================================================

class TestRestrictedRPAUnpickler:
    def test_allows_common_builtins(self):
        up = _RestrictedRPAUnpickler(io.BytesIO())
        assert up.find_class("builtins", "dict") is dict
        assert up.find_class("builtins", "list") is list
        assert up.find_class("builtins", "tuple") is tuple
        assert up.find_class("builtins", "bytes") is bytes
        assert up.find_class("builtins", "str") is str

    def test_allows_python2_builtins(self):
        up = _RestrictedRPAUnpickler(io.BytesIO())
        assert up.find_class("__builtin__", "unicode") is str
        assert up.find_class("__builtin__", "long") is int

    def test_blocks_disallowed_global(self):
        up = _RestrictedRPAUnpickler(io.BytesIO())
        with pytest.raises(pickle.UnpicklingError):
            up.find_class("os", "system")

    def test_blocks_arbitrary_module(self):
        up = _RestrictedRPAUnpickler(io.BytesIO())
        with pytest.raises(pickle.UnpicklingError):
            up.find_class("subprocess", "Popen")


class TestSafeLoadsRpaIndex:
    def test_loads_normal_dict_index(self):
        # A realistic RPA index: {filename: [(offset, length, prefix), ...]}
        index = {"images/bg.png": [(100, 2048, b"")], "script.rpyc": [(3000, 512, b"\x00\x01")]}
        data = pickle.dumps(index)
        result = _safe_loads_rpa_index(data)
        assert result == index

    def test_blocks_malicious_pickle_via_safe_loads(self):
        # A pickle that would execute os.system must NOT be executed —
        # _safe_loads_rpa_index must strictly raise UnpicklingError without fallback.
        class Evil:
            def __reduce__(self):
                return (os.system, ("echo pwned",))

        payload = pickle.dumps(Evil())
        with pytest.raises(pickle.UnpicklingError, match="Disallowed global"):
            _safe_loads_rpa_index(payload)

    def test_loads_complex_legitimate_index(self):
        index = {"archive/sub/file.rpy": [(1024, 2048, b"prefix_key")]}
        assert _safe_loads_rpa_index(pickle.dumps(index)) == index


# ============================================================================
# End-to-end archive round-trip
# ============================================================================

def _build_rpa3(tmp_path: Path, files: dict) -> Path:
    """Build a minimal valid RPA-3.0 archive and return its path."""
    # First pass: assemble body + index, then finalize header with offsets.
    header = b"RPA-3.0 " + b"0" * 16 + b" " + b"0" * 8 + b"\n"
    body_start = len(header)
    body = b""
    index = {}
    for name, content in files.items():
        start = body_start + len(body)
        body += content
        index[name] = [(start, len(content), b"")]

    key = 0
    index_pickle = zlib.compress(pickle.dumps(index))
    index_offset = body_start + len(body)
    header = (
        b"RPA-3.0 "
        + format(index_offset, "016x").encode("ascii")
        + b" "
        + format(key, "08x").encode("ascii")
        + b"\n"
    )

    rpa_path = tmp_path / "archive.rpa"
    rpa_path.write_bytes(header + body + index_pickle)
    return rpa_path


class TestExtractArchive:
    def test_rpa3_round_trip(self, tmp_path):
        files = {
            "game/script.rpy": b"label start:\n    \"Hello world\"\n",
            "game/images/logo.png": b"\x89PNG\r\n\x1a\nfakeimagedata",
        }
        rpa_path = _build_rpa3(tmp_path, files)
        out_dir = tmp_path / "out"

        parser = RPAParser()
        assert parser.extract_archive(rpa_path, out_dir) is True

        for name, content in files.items():
            extracted = out_dir / name
            assert extracted.exists(), f"missing {name}"
            assert extracted.read_bytes() == content

    def test_convenience_function(self, tmp_path):
        files = {"readme.txt": b"LinguaNova test"}
        rpa_path = _build_rpa3(tmp_path, files)
        out_dir = tmp_path / "out2"
        assert extract_rpa(rpa_path, out_dir) is True
        assert (out_dir / "readme.txt").read_bytes() == b"LinguaNova test"

    def test_missing_file_returns_false(self, tmp_path):
        parser = RPAParser()
        assert parser.extract_archive(tmp_path / "nope.rpa", tmp_path) is False

    def test_rpa_path_traversal_blocked(self, tmp_path):
        """Zip Slip / path traversal in RPA file names must be blocked."""
        files = {
            "../../escaped_secret.txt": b"MALICIOUS_PAYLOAD",
            "safe_folder/game.rpy": b"SAFE_CONTENT",
        }
        rpa_path = _build_rpa3(tmp_path, files)
        out_dir = tmp_path / "extracted_game"
        escaped_file = tmp_path / "escaped_secret.txt"

        parser = RPAParser()
        assert parser.extract_archive(rpa_path, out_dir) is True

        # Malicious file outside out_dir must NOT exist
        assert not escaped_file.exists()
        # Safe file must exist
        assert (out_dir / "safe_folder" / "game.rpy").exists()
        assert (out_dir / "safe_folder" / "game.rpy").read_bytes() == b"SAFE_CONTENT"

    def test_hhh_obfuscated_rpa_round_trip(self, tmp_path):
        """Test extraction of custom/obfuscated RPA (HHH-1.0 header + SHA-256 keystream XOR)."""
        files = {
            "game/scripts/story.rpyc": b"\x00\x01\x02fake_rpyc_data",
            "game/scripts/options.rpyc": b"renpy_options_binary",
        }
        key = 0x27EB4993
        # Assemble body + index
        header_placeholder = b"HHH-1.0 " + b"0" * 16 + b" " + b"0" * 8 + b"\n"
        body_start = len(header_placeholder)
        body = b""
        index = {}
        for name, content in files.items():
            start = body_start + len(body)
            body += content
            index[name] = [(start ^ key, len(content) ^ key, b"")]

        compressed_index = zlib.compress(pickle.dumps(index))
        xored_index = _archive_index_xor(compressed_index, key)
        index_offset = body_start + len(body)
        header = (
            b"HHH-1.0 "
            + format(index_offset, "016x").encode("ascii")
            + b" "
            + format(key, "08x").encode("ascii")
            + b"\n"
        )

        rpa_path = tmp_path / "custom_hhh.rpa"
        rpa_path.write_bytes(header + body + xored_index)
        out_dir = tmp_path / "out_hhh"

        parser = RPAParser()
        assert parser.extract_archive(rpa_path, out_dir) is True

        for name, content in files.items():
            extracted = out_dir / name
            assert extracted.exists(), f"missing {name}"
            assert extracted.read_bytes() == content


class TestArchiveDeobfuscation:
    def test_keystream_xor_roundtrip(self):
        key = 0x12345678
        data = b"Hello, LinguaNova obfuscation test payload!" * 10
        xored = _archive_index_xor(data, key)
        assert xored != data
        restored = _archive_index_xor(xored, key)
        assert restored == data

    def test_keystream_deterministic(self):
        key = 0xDEADBEEF
        ks1 = _archive_index_keystream(key, 64)
        ks2 = _archive_index_keystream(key, 64)
        assert ks1 == ks2
        assert len(ks1) == 64

