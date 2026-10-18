**English** · [Español](CONTRIBUTING.es.md)

# Contributing to LinguaNova

Thank you for helping to improve LinguaNova. Bug reports, translations of the interface, tests and code are all welcome.

> [!NOTE]
> LinguaNova is in beta and maintained by one person. Reviews can take a few days. Small, focused pull requests are reviewed faster.

## Before you start

- **Bugs:** open an issue with the bug template. Include the LinguaNova version, the Ren'Py version of the game, the engine you used and the relevant part of the log. Never paste API keys.
- **Large changes** (a new engine, a new file format, changes to the pipeline or the MOD): open an issue first so we can agree on the approach before you spend time on it.
- **Small fixes** (typos, a locale string, an obvious bug): you can open a pull request directly.

## Setting up

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run the tests and the repository check before opening a pull request:

```bash
python -m pytest tests/ -q
python scripts/check_repository_compliance.py
```

On Linux without a display, run the tests with `xvfb-run -a python -m pytest tests/ -q`.

## Workflow

1. Fork the repository and create a branch from `main` (for example `fix/escaped-quotes`).
2. Keep each pull request focused on one change.
3. Add or update tests. A bug fix should include a test that fails without the fix.
4. Update the documentation when the change affects users.
5. Sign off every commit (see below).
6. Open the pull request and fill in the template.

## Sign-off (Developer Certificate of Origin)

LinguaNova uses the [Developer Certificate of Origin 1.1](https://developercertificate.org/) (DCO). By adding a `Signed-off-by` line to a commit, you certify that you wrote the change, or otherwise have the right to submit it, and that it may be distributed under the project's license.

Add the line automatically with `-s`:

```bash
git commit -s -m "Fix escaped quotes in say statements"
```

This produces:

```text
Signed-off-by: Your Name <your-email@example.com>
```

You can use your GitHub noreply address (`username@users.noreply.github.com`) if you do not want to publish your email. If you forgot to sign off your last commit, run `git commit --amend -s --no-edit` and push again.

If you edit files through the GitHub website, add the `Signed-off-by:` line yourself at the end of the commit description.

## License of contributions

LinguaNova is a modified work of RenLocalizer and is distributed under **GPL-3.0-or-later**.

- Contributions to GPL-covered code are accepted under GPL-3.0-or-later, unless an independent file validly states another compatible license.
- No copyright assignment is required. You keep the copyright on your contribution.
- Contributors are credited in the git history and, for significant contributions, in `MODIFICATIONS_LINGUANOVA.md`.

**This document does not restrict the GPL.** It adds no ban on commercial use, sale or redistribution. Anyone, including the maintainer and contributors, may use, sell and redistribute LinguaNova as the GPL allows, provided the source code and license are passed on. Community preferences do not reduce the rights granted by GPL-3.0-or-later.

## What not to submit

- Proprietary code that you are not allowed to redistribute.
- API keys, tokens, passwords, cookies or private data, including inside logs, screenshots or test files.
- Graphics, fonts, models or other files under an incompatible license.
- Code copied from another project without keeping its license and attribution.
- Text, images or files extracted from commercial games. Use short, invented test strings instead.
- Changes whose purpose is to bypass the terms, limits or protections of a translation service.

If you include third-party code, state in the pull request: the source project, URL, license, affected files and why the license is compatible.

## Changes that need extra documentation

Update `MODIFICATIONS_LINGUANOVA.md`, `NOTICE.md` or `THIRD_PARTY_NOTICES.md` when a change significantly affects:

- provenance or licensing;
- distribution, the installer or the portable build;
- dependencies;
- security;
- the updater;
- the translation architecture;
- the format of the generated files.

## Translating the interface

The interface texts are in `locales/*.json`. When you add a key, add it to every locale file (English text is acceptable as a placeholder) so no language shows a raw key.

## Code of conduct

All participation is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). To report a security problem, follow [`SECURITY.md`](SECURITY.md) instead of opening a public issue.
