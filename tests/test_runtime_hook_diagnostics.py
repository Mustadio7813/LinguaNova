# -*- coding: utf-8 -*-
"""
Behavioral tests for runtime hook diagnostics.
Replaces the old string-contains tests with actual execution traces.
"""

import json
from pathlib import Path
import sys
import pytest

from src.core import runtime_hook_template as rht

# ============================================================================
# MOCKING ENVIRONMENT
# ============================================================================

class MockRenpyCurrentScreen:
    def __init__(self, name="mock_screen"):
        self.screen_name = (name,)

class MockPreferences:
    def __init__(self, language="tr"):
        self.language = language

class MockRenpyConfig:
    def __init__(self, basedir):
        self.basedir = str(basedir)
        self.gamedir = str(Path(basedir) / "game")
        self.language = "tr"
        self.say_menu_text_filter = None
        self.replace_text = None

class MockRenpy:
    def __init__(self, basedir):
        self.config = MockRenpyConfig(basedir)
        self._current_screen = MockRenpyCurrentScreen()

    def current_screen(self):
        return self._current_screen

def extract_python_blocks(hook_code: str) -> list:
    """Extracts Python code from Ren'Py init blocks as a list of independent blocks."""
    lines = hook_code.split('\n')
    blocks = []
    current_block = []
    in_block = False
    
    for line in lines:
        if line.strip().startswith("init ") and "python:" in line:
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            in_block = True
            continue
        elif line.startswith("translate ") or line.startswith("screen "):
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            in_block = False
            continue
            
        if in_block:
            if line.startswith("    "):
                current_block.append(line[4:])
            elif line.strip() == "":
                current_block.append("")
            else:
                in_block = False
                if current_block:
                    blocks.append('\n'.join(current_block))
                    current_block = []
                    
    if current_block:
        blocks.append('\n'.join(current_block))
        
    return blocks

def setup_mock_env(tmp_path: Path, limit: int = 500, lang: str = "tr"):
    """Compiles and executes the runtime hook code in a mocked environment."""
    hook_code = rht.render_runtime_hook(lang, runtime_string_diagnostics=True)
    
    # Inject specific limits for testing
    hook_code = hook_code.replace("_rl_runtime_miss_limit = 500", f"_rl_runtime_miss_limit = {limit}")
    
    py_blocks = extract_python_blocks(hook_code)
    
    # Basic module mapping
    mock_config = MockRenpyConfig(tmp_path)
    mock_env = {
        "renpy": MockRenpy(tmp_path),
        "config": mock_config,
        "_preferences": MockPreferences(),
        "_rl_sys": sys,
        "_rl_json": json,
        "_rl_os": __import__('os'),
        "_rl_time": __import__('time'),
        "_rl_codecs": __import__('codecs'),
        "_rl_datetime": __import__('datetime'),
    }
    
    # Ensure sys caches are clear
    if hasattr(sys, '_rl_caches'):
        delattr(sys, '_rl_caches')
        
    for i, block in enumerate(py_blocks):
        try:
            exec(block, mock_env)
        except Exception as e:
            pytest.fail(f"Could not execute python block {i}: {e}\nBlock code snippet:\n{block[:100]}...")
            
    return mock_env

# ============================================================================
# BEHAVIORAL TESTS
# ============================================================================

def test_runtime_miss_logging_respects_limit(tmp_path: Path):
    """Verify miss logging stops writing after reaching the configured limit."""
    env = setup_mock_env(tmp_path, limit=3)
    log_func = env.get("_rl_log_runtime_miss")
    assert log_func is not None, "Missing log function in hook execution"
    
    # Execute 5 times with distinct texts to bypass deduplication
    for i in range(5):
        log_func("replace_text", f"Different text {i}", "exact_lookup_miss")
        
    log_file = tmp_path / "game" / "tl" / ".diagnostics" / "tr" / "runtime_missed_strings.jsonl"
    assert log_file.exists(), "Log file should be created"
    
    # Read the output
    content = log_file.read_text(encoding="utf-8").strip()
    lines = [line for line in content.split("\n") if line]
    
    # Should only contain 3 lines despite 5 calls
    assert len(lines) == 3, f"Expected 3 logs due to limit, got {len(lines)}"

def test_runtime_miss_deduplication(tmp_path: Path):
    """Same text from same layer should not produce duplicate log entries."""
    env = setup_mock_env(tmp_path)
    log_func = env["_rl_log_runtime_miss"]
    
    # Log the exact same miss 3 times
    log_func("replace_text", "Duplicated miss", "exact_lookup_miss")
    log_func("replace_text", "Duplicated miss", "exact_lookup_miss")
    log_func("replace_text", "Duplicated miss", "exact_lookup_miss")
    
    # Also log it from a different layer (which should be allowed once)
    log_func("say_menu_text_filter", "Duplicated miss", "no_exact_match_pre_interpolation")
    
    log_file = tmp_path / "game" / "tl" / ".diagnostics" / "tr" / "runtime_missed_strings.jsonl"
    content = log_file.read_text(encoding="utf-8").strip()
    lines = [line for line in content.split("\n") if line]
    
    # Expected: 2 lines total (1 for replace_text, 1 for say_menu_text_filter)
    assert len(lines) == 2
    
def test_runtime_miss_payload_structure(tmp_path: Path):
    """Verify JSONL output structure and included metadata."""
    env = setup_mock_env(tmp_path, lang="de")
    log_func = env["_rl_log_runtime_miss"]
    
    log_func("replace_text", "Hello [player]", "unknown")
    
    log_file = tmp_path / "game" / "tl" / ".diagnostics" / "tr" / "runtime_missed_strings.jsonl"
    content = log_file.read_text(encoding="utf-8").strip()
    
    entry = json.loads(content)
    assert entry["text"] == "Hello [player]"
    assert entry["layer"] == "replace_text"
    assert "ts" in entry
    assert entry["source_kind"] == "unknown"
    assert entry["word_count"] == 2
    assert entry["length"] == 14
    assert entry["stripped"] == "Hello [player]"
    assert entry["active_language"] == "tr"

def test_diagnostics_disabled_by_default(tmp_path: Path):
    """When False, logging function should not exist or fallback cleanly."""
    hook_code = rht.render_runtime_hook("tr", runtime_string_diagnostics=False)
    py_blocks = extract_python_blocks(hook_code)
    
    mock_config = MockRenpyConfig(tmp_path)
    mock_env = {
        "renpy": MockRenpy(tmp_path),
        "config": mock_config,
        "_preferences": MockPreferences(),
        "_rl_sys": sys,
        "_rl_json": json,
        "_rl_os": __import__('os')
    }
    for block in py_blocks:
        exec(block, mock_env)
    
    # Function exists but shouldn't do anything
    log_func = mock_env["_rl_log_runtime_miss"]
    log_func("replace_text", "Should not log", "unknown")
    
    log_file = tmp_path / "game" / "tl" / "tr" / "diagnostics" / "runtime_missed_strings.jsonl"
    assert not log_file.exists()

def test_string_scope_harvesting(tmp_path: Path):
    """Verify that screen string harvesting captures strings recursively."""
    # We test the pure logic part independent of renpy.get_screen logic
    # The actual get_screen is native to Ren'Py, so we verify _rl_harvest_strings logic.
    env = setup_mock_env(tmp_path)
    harvest_func = env.get("_rl_harvest_strings")
    
    if not harvest_func:
        pytest.skip("Scope harvesting not implemented in this version")
        return
        
    class MockTextWidget:
        text = ["Hello", "World"]
    class MockDisplayable:
        children = [MockTextWidget()]
    
    results = set()
    harvest_func(MockDisplayable(), results)
    
    assert "Hello" in results
    assert "World" in results