# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
from pathlib import Path

import yaml


def test_linux_targz_artifact_uploaded_and_released():
    workflow = yaml.safe_load(Path(".github/workflows/release.yml").read_text(encoding="utf-8"))
    build_linux_steps = workflow["jobs"]["build-linux"]["steps"]

    install_launcher_steps = [s for s in build_linux_steps if s.get("name") == "Install portable launcher script (Linux tar.gz)"]
    assert len(install_launcher_steps) == 1
    assert "cp LinguaNova.sh dist/LinguaNova/LinguaNova.sh" in install_launcher_steps[0]["run"]
    assert "chmod +x dist/LinguaNova/LinguaNova.sh" in install_launcher_steps[0]["run"]

    portable_smoke_steps = [s for s in build_linux_steps if s.get("name") == "Smoke test portable launcher (Linux tar.gz payload)"]
    assert len(portable_smoke_steps) == 1
    assert "./dist/LinguaNova/LinguaNova.sh" in portable_smoke_steps[0]["run"]

    upload_targz_steps = [s for s in build_linux_steps if s.get("name") == "Upload artifact (tar.gz)"]
    assert len(upload_targz_steps) == 1
    assert upload_targz_steps[0]["with"]["name"] == "linux-build-targz"
    assert upload_targz_steps[0]["with"]["path"] == "LinguaNova-Linux-x64.tar.gz"

    release_steps = workflow["jobs"]["release"]["steps"]
    download_targz_steps = [s for s in release_steps if s.get("name") == "Download Linux tar.gz artifact"]
    assert len(download_targz_steps) == 1
    assert download_targz_steps[0]["with"]["name"] == "linux-build-targz"

    create_release = next(s for s in release_steps if s.get("name") == "Create Release")
    files = create_release["with"]["files"]
    assert "LinguaNova-Linux-x64.AppImage" in files
    assert "LinguaNova-Linux-x64.tar.gz" in files
