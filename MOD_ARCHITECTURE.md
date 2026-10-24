# LinguaNova MOD Architecture

SPDX-License-Identifier: GPL-3.0-or-later

## #MOD purpose

`MOD` is a first-class LinguaNova feature that generates a standalone Ren'Py
interface-translation mod. It is intentionally separate from the normal
full-game translation pipeline.

The generated file follows this naming rule:

`linguanova_mod_<normalized_game_name>_multilang.rpy`

One file per game holds every generated language (e.g. `linguanova_mod_my_game_multilang.rpy`).

## Isolation contract

The existing main translation hook is protected. At the time the MOD boundary
was introduced, its SHA-256 was:

`bee504f9327f240b7714949615b4077a5687feb7583e00ab9fa7e5f08782132a`

The MOD subsystem does not import, patch, wrap or rewrite
`src/core/runtime_hook_template.py`. It has a separate hook in
`src/ui_mod/ui_mod_hook_template.py`.

The MOD parser is also separate from the normal LinguaNova Ren'Py parser. Game
`.rpy`, `.rpyc` and `.rpa` files are read-only inputs. Visible `.rpy` sources
have priority; orphan `.rpyc` and script members found inside `.rpa` archives
only fill missing sources. RPA inspection is selective and does not unpack
multimedia files into the game directory.

## Parser and variable safety

MOD is fail-closed:

- Ren'Py `[interpolation]`, text tags, `%` format fields and format placeholders
  are protected before translation and must be restored exactly.
- A candidate with missing/changed variables or tags is rejected instead of
  being heuristically repaired.
- Python source, expressions and debug formats found by the scanner are excluded
  (`src/ui_mod/filters.py`) and listed in the report.
- Original game scripts are never rewritten.
- The generated MOD chains to an existing `config.replace_text` callback rather
  than replacing unrelated translation behavior.
- Since hook format 4 every text (including text with `{tags}` and `[variables]`)
  is registered WHOLE in Ren'Py's native string table, so Ren'Py translates it
  before substitution, exactly like a hand-written `translate <lang> strings`
  block. `config.replace_text` is only used for runtime-built printf/`{0}`
  templates (`"Coins: %d"`).

## Language contract (2026-10-17)

- Every MOD language value goes through `src/ui_mod/languages.py` (the five
  supported languages): Ren'Py folder id for `game/tl/<folder>/`, API code for engines.
- `auto` source is resolved before translating (offline py3langid, then the
  engine detector); an undetermined source is reported, never assumed English.
- Engine-specific codes come from `src/ui_mod/engine_support.py`.
- Every answer passes `src/ui_mod/quality.py`; rejected answers are retried
  individually and otherwise stay pending. Only accepted answers are published
  and cached.
- MOD never reads or writes the shared translation cache; its own cache is
  `game/tl/<folder>/linguanova_mod_hook_data.json` with per-entry provenance.
- Hand edits live in `game/tl/<folder>/linguanova_mod_manual.json` (schema 2,
  only edits) and win over machine output.
- Per-language glossary `game/tl/<folder>/linguanova_mod_glossary.json`
  (`src/ui_mod/glossary.py`): `Character("Name")` names are seeded as "keep";
  terms are replaced by neutral tokens before sending and restored afterwards;
  cached lines that disagree with the glossary are translated again.

## Generated files

- `game/linguanova_mod_<game>_multilang.rpy` — readable hook; embeds every language.
- `game/tl/<folder>/linguanova_mod_hook_data.json` — active data + provenance.
- `game/tl/<folder>/linguanova_mod_manual.json` — hand edits.
- `game/tl/<folder>/linguanova_mod_report.json` — counts, pending texts and reasons,
  excluded code strings, source detection, engine codes, validation level.
- `game/tl/<folder>/linguanova_mod_glossary.json` — names/terms for that language.
- `game/tl/<folder>/linguanova_mod_backup/<timestamp>/*.bak` — previous MOD files.
- `game/linguanova_mod_fonts/` — replacement fonts, only when a game font lacks
  the language's letters (outside `tl/`, so Ren'Py never takes it for a language).

## In-game behavior

Ren'Py automatically loads `linguanova_mod_<game>_multilang.rpy` during normal
startup. The MOD translates the game's existing text in place, preserving the
original screens, layout, buttons, styles and actions.

- Language panel: a small "Idioma / Language" button (bottom-right overlay) or
  Shift+L opens a modal panel listing "Original" and every MOD language with its
  progress; choosing one calls Ren'Py's native `Language()` action (hot switch).
  The button can be hidden from the panel (`persistent._lnmod_hide_button`).
- New players start in the last generated language through
  `config.default_language` only when the game sets none; the original language
  always stays untranslated.
- Fonts: `translate <lang> python:` blocks apply/reset the per-language
  `config.font_replacement_map` entries; RTL languages set `config.rtl`.
- A text the game already translates for that language is never registered
  again (Ren'Py would stop with "A translation for ... already exists").

The MOD can be used independently from a full LinguaNova translation and may
coexist with a translation obtained elsewhere.

## Main hook vs MOD hook

- `src/core/runtime_hook_template.py`: normal full-game translation hook; general
  runtime translation, dynamic recovery, caches, templates and pipeline support.
- `src/ui_mod/ui_mod_hook_template.py`: interface-MOD-only hook; restricted UI
  mapping and screen context, chains any prior `config.replace_text`, and never
  imports, patches or rewrites the main hook.

## Source coverage

The MOD scanner currently covers:

1. visible `.rpy` / `.rpym` files;
2. orphan `.rpyc` / `.rpymc` files, read in memory with LinguaNova's own RPYC
   reader (no `.rpy` is written into the game); unreadable ones are counted;
3. `.rpy` / `.rpyc` script members and font files inside `.rpa` archives, using
   read-only selective archive inspection;
4. direct `screen` text (`text`, `textbutton`, `tooltip`, `prompt`);
5. explicitly marked translatable strings (`_()`, `__()`, `___()`, `_p()`);
6. simple literal UI data assigned to variables referenced by screens.

Image-only text cannot be translated by a text hook and remains outside this
module's scope.

## Serial work queue policy

Long-running translation and MOD requests share a FIFO work queue. Submitting a
new request never cancels, replaces or interrupts the active request. It is
appended to the queue and begins only after the active request finishes. Only an
explicit user stop or application shutdown may request cancellation.

## Current status

The MOD page, independent scanner/parser, selective RPA reader, RPYC fallback,
strict placeholder guard, autonomous MOD hook, builder, backend execution path,
queue integration and regression tests are implemented. The main translation
hook remains outside the MOD dependency graph.
