# LinguaNova 🌠

**English** · [Español](README.es.md)

> [!WARNING]
> **LinguaNova is in beta and under active development.** It modifies translation files inside the game folder: **back up the game before translating**, and check the result before sharing it. Please report problems in [Issues](../../issues) and include the log and the game's Ren'Py version.

> [!IMPORTANT]
> **LinguaNova is a separately maintained modified work, based in part on RenLocalizer 2.8.19.**
> It is not an official RenLocalizer release, it is not maintained by the original authors, and it does not imply any affiliation, endorsement or support from them.
>
> **Original project:** https://github.com/Lord0fTurk/RenLocalizer  
> **Original copyright notice preserved:** Copyright (C) 2025 RenLocalizer V2 Authors  
> **License of the modified work:** GNU General Public License v3.0 or later (**GPL-3.0-or-later**)  
> **Relevant modification-notice date:** 2026-10-16  
>
> See [`NOTICE.md`](NOTICE.md), [`UPSTREAM.md`](UPSTREAM.md), [`LICENSE_POLICY.md`](LICENSE_POLICY.md) and [`MODIFICATIONS_LINGUANOVA.md`](MODIFICATIONS_LINGUANOVA.md).

**LinguaNova translates Ren'Py games while preserving their script structure, variables, text tags and translation files.**

![Platforms](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-ff7a59?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-PyQt6%20%2B%20QML-41cd52?style=flat-square)
![Ren'Py](https://img.shields.io/badge/Ren'Py-7%20%26%208-ffb86b?style=flat-square)
![License](https://img.shields.io/badge/License-GPL--3.0--or--later-111827?style=flat-square)

## Relationship with RenLocalizer

LinguaNova **does not hide where it comes from**:

- it is derived in part from RenLocalizer;
- it keeps the corresponding attribution and license notices;
- it keeps an explicit record of every modification;
- it has its own name, visual identity and maintenance;
- LinguaNova's bugs, changes and decisions must not be attributed to the RenLocalizer authors;
- being a separate repository does not change the fact that LinguaNova is a modified work under GPL-3.0-or-later.

[`UPSTREAM.md`](UPSTREAM.md) documents the relationship with the original project.

## ⚡ Quick start

1. **Select the game:** its main folder, its `game` folder or a supported executable.
2. **Choose the language and the translation engine.**
3. **Start the translation** and review the result before distributing it.

## Main features

- Translation and generation of Ren'Py language files.
- Protection of variables, text tags and placeholders, with a check that tags stay in the order Ren'Py requires.
- Analysis of `.rpy`, `.rpyc` and packed content when the available tools allow it.
- Honest results: translated lines, lines identical to the original, engine failures and lines blocked by the syntax guard are reported separately.
- Translation editor.
- Font, glossary and diagnostic tools.
- Interface translation MOD, separate from the normal translation flow.
- Work queue that never cancels the running job.
- Interface available in nine languages, plus languages you add yourself (Utilities → *Create an interface language*).
- Windows installer with automatic, verified updates.

## 💾 Installation

| System | File in each [release](https://github.com/Mustadio7813/LinguaNova/releases) | Notes |
| --- | --- | --- |
| Windows 10/11 (64-bit) | `LinguaNova_Setup_<version>.exe` | Installer. You choose one of the PC's internal drives and LinguaNova goes to `<drive>:\LinguaNova`. No administrator rights; desktop shortcut and Start menu entry. Updates itself. |
| Windows (portable) | `LinguaNova-Windows-x64.zip` | Unzip and run `LinguaNova.exe`. Create an empty `.portable` file in the folder to keep settings inside it. |
| Linux (x64) | `LinguaNova-Linux-x64.AppImage` | Built and start-up tested by GitHub Actions. |
| macOS (Apple silicon) | `LinguaNova-macOS-arm64.dmg` | **Experimental:** built and start-up tested by GitHub Actions, not yet tried on a real Mac by the maintainer. Reports are welcome. |

The installer and the program pick the Windows language automatically (English if it is not one of the nine); you can change it in Settings. Windows does not allow installers to pin programs to the taskbar: open LinguaNova, right-click its taskbar icon and choose **Pin to taskbar**.

## 🛠️ Running from source

Requires Python 3.10 or later; Python 3.12 64-bit is recommended. Extract the
full source archive to a regular folder; do not run it from WinRAR or 7-Zip's
temporary archive view.

On Windows, run `run.bat`. The launcher creates `.venv`, installs or repairs
the declared dependencies, then starts the application. Internet access is
needed for the first dependency installation. If Python cannot create the
environment with `pip`, the launcher retries without `pip` and provisions it
from the selected Python installation.

On Linux/macOS, prepare the environment and start the application manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

To start the CLI, activate `.venv` first and run:

```bash
python run_cli.py --interactive
```

The source ZIP is not an installer and does not contain a packaged executable.
On Windows, use `run.bat`; for a packaged application, download the installer
or portable ZIP from [Releases](https://github.com/Mustadio7813/LinguaNova/releases).

## ✅ Translation results and output files

An empty response or a response identical to the source is not accepted as a
valid cached translation. The completion summary reports actual coverage and
marks lines the engine could not change as pending. The source-text fallback is
kept to avoid blank Ren'Py lines. When LinguaNova rewrites a supported
translation entry, it also removes a trailing `#ignore` comment from the
destination line.

## 📦 Building and distribution

The included build scripts are part of LinguaNova's corresponding source code.

Before publishing a binary:

1. build it from a specific commit or tag;
2. keep the exact source code used for that binary;
3. publish that source code with the binary, or by another method allowed by GPLv3;
4. include the notices and licenses of the third-party components that are actually part of that build;
5. generate and publish SHA-256 checksums of the artifacts.

See [`SOURCE_DISTRIBUTION.md`](SOURCE_DISTRIBUTION.md) and [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

On Windows, `build_windows.bat` builds `dist\LinguaNova\` and `build_installer.bat` turns it into the installer (needs [Inno Setup](https://jrsoftware.org/isdl.php) 6.5+), the portable ZIP and `SHA256SUMS.txt`. Pushing a `v*` tag makes GitHub Actions (`release.yml`) build all of this for Windows, Linux and macOS and publish it as a release.

## 🔄 LinguaNova updates

LinguaNova checks this repository's releases (`Mustadio7813/LinguaNova`) for a newer version at start-up (it can be turned off) and from **Utilities → Updates → Check for updates**.

- **Installed Windows version:** the notice offers **Update now**. LinguaNova downloads `LinguaNova_Setup_<version>.exe` from the release, checks it against the release's `SHA256SUMS.txt` (a file that does not match is deleted and never run), installs it in the same folder and reopens. Nothing is installed without your click.
- **Portable, Linux and macOS:** the notice opens the release page to download the new version.
- If the check fails (no connection, no published release…), LinguaNova says so instead of reporting that you are up to date.

The update channel never points to RenLocalizer. This concerns **updates of the LinguaNova program**, not AI models or external components, which are managed separately.

## 📄 License

LinguaNova is distributed under the **GNU GPL v3 or later (GPL-3.0-or-later)**.

- Full text: [`LICENSE`](LICENSE) and [`COPYING`](COPYING).
- Provenance and attribution: [`NOTICE.md`](NOTICE.md).
- License policy: [`LICENSE_POLICY.md`](LICENSE_POLICY.md).
- Changes from the base work: [`MODIFICATIONS_LINGUANOVA.md`](MODIFICATIONS_LINGUANOVA.md).
- Source code distribution: [`SOURCE_DISTRIBUTION.md`](SOURCE_DISTRIBUTION.md).
- Third parties: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

**No "non-commercial" restriction is added.** The rights granted by GPL-3.0-or-later, including the right to redistribute under the license, are not limited by the `README`, `CONTRIBUTING`, the code of conduct or any other project document.

## No warranty

LinguaNova is provided without any warranty, under the terms of the GNU GPL. Review the translations and keep backups before modifying third-party projects.
