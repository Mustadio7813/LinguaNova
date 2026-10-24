"""Recovery from the reported ensurepip failure, without using ensurepip."""
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest
import start


def test_existing_pip_does_not_reinstall_or_create_an_environment(tmp_path):
    with patch.object(start, "works", return_value=True), patch.object(start, "checked") as execute:
        start.ensure_pip(tmp_path / "python.exe", tmp_path / "log")
        execute.assert_not_called()


def test_host_pip_repairs_a_pip_free_environment_and_quotes_paths(tmp_path):
    commands = []
    with patch.object(start, "works", return_value=False), patch.object(start, "checked", side_effect=lambda cmd, log: commands.append(cmd)):
        start.ensure_pip(tmp_path / "Matias Jaque/.venv/Scripts/python.exe", tmp_path / "log", host="C:/Python314/python.exe")
    assert commands[0][:4] == ["C:/Python314/python.exe", "-m", "pip", "--python"]
    assert commands[0][4].endswith("Matias Jaque/.venv/Scripts/python.exe")
    assert all("ensurepip" not in part for part in commands[0])


def test_bootstrap_retains_the_full_subprocess_error(tmp_path):
    log = tmp_path / "inicio_error.log"
    with patch.object(start.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "real internal failure\n")):
        with pytest.raises(RuntimeError, match="inicio_error.log"):
            start.checked(["python.exe", "-m", "pip"], log)
    assert "real internal failure" in log.read_text()
