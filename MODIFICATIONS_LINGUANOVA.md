# MODIFICATIONS — LinguaNova

## Scope and baseline

This document is the prominent modification record for the LinguaNova release dated **2026-10-16**.

Baseline: **RenLocalizer 2.8.19**, https://github.com/Lord0fTurk/RenLocalizer, compared against the supplied `RenLocalizer-main(5).zip` archive.

LinguaNova is not represented as an original RenLocalizer release.

## Complete functional modification record to date

### 16. MOD sandbox/point-and-click translation pipeline ? 2026-10-17
- The isolated MOD scanner now collects interface, menu, dialogue, literal Python/UI calls and screen-backed UI data without changing the normal parser or translator pipeline.
- Existing target-language `game/tl/<idioma>/` translations are scanned recursively and reused through the runtime hook instead of generating duplicate Ren'Py `translate` blocks. Repeated strings and repeated TL entries are deduplicated safely.
- Manual and generated translations use the MOD junk filter; invalid one-letter labels and standalone color codes are rejected, and exact source edge whitespace and Ren'Py interpolation/format tokens are preserved.
- Generated translations are stored in `game/tl/<idioma>/linguanova_mod_hook_data.json`; the `.rpy` hook keeps only a compressed embedded fallback and loads/caches JSON for the active Ren'Py language. `config.replace_text` and `config.say_menu_text_filter` are chained safely.
- MOD source scanning ignores `.rpyc` and `.rpymc` files; only visible `.rpy`/`.rpym` and readable source script members in RPA archives are processed.
- Consolidated MOD inventory metadata: `EXPECTED_FILES = 247` and `EXPECTED_PY_FILES = 189`.

### 1. Branding, identity and release metadata
- RenLocalizer branding changed to LinguaNova in application-facing code, launchers, build metadata and packaging resources.
- LinguaNova icon resources replace the original icon resources.
- Application/version presentation was separated from upstream release numbering.
- Upstream funding/promotional and static landing-page material were removed from this modified distribution.
- The update checker was changed so this fork does not silently present itself as or update itself from the upstream RenLocalizer release channel.

### 2. Startup, packaging and standalone operation
- Startup/import behavior was hardened to avoid eager-import failures.
- Dependency/startup handling was adjusted for the LinguaNova layout.
- The standalone edition does not require `run.bat` or a project-local `.venv` at runtime.
- A single-file Python launcher was created with private user-writable dependency/cache support and a `--build-exe` workflow.
- The single-file source is readable: project text is not stored in Base64. Text files are directly visible/searchable; only icon binaries are represented as hexadecimal data.
- Standalone-root compatibility was added for paths/resources/configuration after materialization.

### 3. Translation/extraction performance corrections
- The extraction/parsing path around the previously observed 30% progress stall was corrected.
- `.rpyc` processing avoids redundant work when equivalent `.rpy` source exists while still processing orphan `.rpyc` files.
- Repeated scanning in the affected extraction path was reduced and progress reporting made more granular.
- Ren'Py-specific parsing/protection behavior was preserved.

### 4. Main interface redesign
- Navigation, workspace headers, cards, buttons, settings areas and utilities were reorganized into the LinguaNova workspace design.
- The game/project selector remains directly accessible.
- The game path field is read-only to prevent accidental manual edits.

### 5. Game path session behavior
- The selected game path is not restored on the next launch.
- Legacy persisted `last_input_directory` use for the visible project field was neutralized.
- The visible project path is explicitly cleared at startup and remains session-only.

### 6. Language selectors and catalogue
- Source/target selection was redesigned as an adaptive searchable mosaic.
- Search supports interface-language names, native names and codes, including accent-insensitive Latin search.
- Native names remain visible as a secondary reference.
- Language names follow the selected interface locale.

### 7. Complete UI localization pass
- Redesigned-interface Spanish literals that remained visible in other UI languages were moved into localization keys.
- QML localization keys used by the redesigned interface were synchronized across German, English, Spanish, Persian, French, Japanese, Russian, Turkish and Simplified Chinese.
- The 135 translation-language entries receive localized display names while retaining native names.
- GPL/About legal text added in this release is localized in the same nine UI languages.

### 8. Utilities and supporting UI
- Utility/tool messages introduced by the LinguaNova redesign were normalized into the localization system.
- An About dialog was added and expanded with GPL/provenance/source/no-warranty information.
- Existing utility/core behavior remains available despite the visual redesign.

### 9. Native Ren'Py language-menu integration
- The former generated `zzz_<language>_language.rpy` path that forced `config.language` / startup `renpy.change_language()` was removed from normal integration.
- Stale legacy forcing helpers generated by prior runs are removed.
- `game/zzz_linguanova_language_menu.rpy` is generated only when a safe existing selector can be identified.
- Detection searches screens containing multiple `Language(...)` actions instead of depending on the name `preferences`.
- Direct `textbutton` lists are extended by cloning a native button in the same container without overwriting the developer's source file.
- Simple list/tuple/dictionary-driven selectors are extended through their data structure instead of redefining the screen.
- Highly custom/unsafe selectors are left untouched; `tl/<language>` remains valid.
- EXE workflows remain supported by reusing temporary `.rpyc` decompilation when needed for analysis.
- SDK-generated `game/tl/<language>` workflows remain supported.

### 10. GPL compliance corrections in this release
- The baseline archive's `LICENSE` was not a complete verbatim GNU GPL v3 text. It is replaced here with the complete GPLv3 text.
- Conventional `COPYING` was added with the same complete GPLv3 text.
- `NOTICE.md` now records provenance, upstream attribution, modification date, source/distribution obligations, third-party licensing and warranty information.
- `SOURCE_DISTRIBUTION.md` documents practical Complete Corresponding Source distribution.
- Modified source files that safely accept comments receive SPDX `GPL-3.0-or-later` and links to the legal/change records.
- The About dialog displays modified-work status, GPL licensing, corresponding-source entitlement and no-warranty notice.


### 11. Translation-session control lock

- When a translation starts, the project-selection card is disabled, including
  the folder and executable selectors.
- The translation engine, source language, target language and local-model
  selection card is disabled for the complete active run.
- Workspace navigation that could expose configuration or utility actions is
  disabled while the run is active; the translation dashboard remains visible.
- The Stop Translation action intentionally remains enabled.
- Native file/folder dialog callbacks refuse to replace the selected project if
  a translation has already started.
- Backend guards independently reject attempts to change the project path,
  source language, target language or translation engine while `_is_translating`
  is true. This prevents race conditions even if a UI callback arrives late.
- Controls are released after the normal `translationFinished` signal, including
  stopped and failed runs.


### 12. Branding and visual-asset cleanup

- Audited every embedded binary visual asset in this release.
- The project contains only two application bitmap resources; both already use
  the LinguaNova artwork rather than a RenLocalizer logo.
- Renamed the active source assets from generic `icon.png` / `icon.ico` to
  explicit `linguanova_logo.png` / `linguanova.ico`.
- Updated the Windows executable/taskbar icon, startup splash, system-tray icon,
  About dialog, PyInstaller specification, Linux release workflow and macOS
  `.icns` generation to use the LinguaNova asset names.
- The Linux desktop entry remains `Icon=linguanova` and `Name=LinguaNova`.
- Upstream names and RenLocalizer references in GPL provenance, attribution,
  modification notices and historical changelog entries are deliberately kept;
  those are legal/history records, not active product branding.
- Emoji/Unicode status symbols used by the interface are retained because they
  are functional UI glyphs and are not RenLocalizer logos.


### 13. Resolution-independent responsive desktop layout

- LinguaNova now starts maximized so the complete operating-system work area is
  available to the QML workspace immediately.
- The previous hard minimum of 1040×680 was replaced by screen-aware minimum
  dimensions so smaller desktop work areas are not forced outside the monitor.
- Added shared width/height breakpoints for compact-height, compact-width,
  narrow and very-narrow desktop layouts.
- The top workspace header and navigation bar reduce height, spacing and
  margins automatically on lower-resolution displays.
- Navigation buttons can contract safely and elide translated labels instead of
  forcing the window wider than the available work area.
- Dashboard, Configuration, Utilities and Glossary now expose explicit vertical
  scroll ranges rather than depending only on implicit ScrollView sizing.
- The Utilities page uses responsive one/two-column layout, compact card
  padding, compact spacing and compact button heights; all tools remain
  reachable at 1366×768 and smaller work areas through vertical scrolling.
- The translation editor reduces margins, selector widths and minimum list
  height when the available work area is compact.
- Large/HiDPI/ultrawide monitors keep centered maximum content widths so
  maximizing the program does not stretch cards indefinitely.
- This is a layout/accessibility change only; translation parsing, saving,
  engine behavior and Ren'Py output formats are unchanged.


### 14. Content-aware locale fitting and automatic scrollbar visibility

- On 1080p-class desktop work areas LinguaNova now uses a slightly denser
  fit-first layout before deciding that a page needs vertical scrolling.
- The behavior is not hard-coded to Spanish. QML uses the actual implicit
  height produced by the currently selected interface language, so longer
  German, Russian, French, Persian, Japanese, Chinese or other localized text
  can naturally increase the measured page height.
- Dashboard, Configuration, Utilities and Glossary hide their page scrollbar
  completely when their translated content fits inside the available viewport.
- If the selected language, DPI scaling, taskbar/dock size or any other layout
  factor makes the real content exceed the viewport, the vertical scrollbar
  automatically reappears.
- Large displays keep the normal spacious layout when there is no need to
  compress the interface.
- Functional list/editor scrollbars remain available where scrolling is part of
  the control itself; only page-level decorative overflow bars are hidden when
  unnecessary.
- This revision changes QML layout behavior and documentation only. It does not
  alter translation extraction, translation engines, saving logic, glossary
  extraction, Ren'Py parsing or generated translation contents.


### 15. Locale-adaptive option descriptions and product subtitle

- The small product subtitle in the main header was renamed from the generic
  “Workspace” label to “Ren'Py Translator”, localized across all nine bundled
  interface languages.
- Settings descriptions remain at approximately 11 px rather than being reduced
  to unreadably small text.
- Wrapped option descriptions use a modest line height and their natural
  implicit height.
- The Interface/System settings card no longer has a fixed 160 px height. Its
  height follows the real localized content, so a description that needs two or
  more lines in another UI locale expands only the containing card by the
  necessary amount.
- Shorter translations automatically return to the compact height when the UI
  language changes.
- This revision is presentation-only. Translation extraction, engines, Ren'Py
  parsing, saving, glossary extraction, font injection and generated game
  translation content are unchanged.


### 16. QML startup regression fix after adaptive-text update

- Fixed a QML startup regression introduced by the locale-adaptive text pass.
- Five `lineHeight: 1.15` assignments had been inserted one line after an
  inline `Label { ... }`, which made QML interpret them as properties of the
  surrounding `ColumnLayout`.
- `ColumnLayout` has no `lineHeight` property, so `Main.qml` could fail to load
  and LinguaNova would not open.
- The five properties are now inside their intended `Label` declarations.
- The adaptive 11 px descriptions, language-dependent card growth and all
  previous responsive behavior are preserved.
- Translation extraction, engines, parser, saving, glossary extraction, font
  injection and generated Ren'Py translation content are unchanged.


### 17. #MOD isolated interface-mod architecture

- Added a first-class navigation page named `MOD` with the `🧩` icon.
- Added `src/ui_mod/` as an isolated subsystem reserved for standalone
  interface-translation MOD generation.
- Added an exclusive MOD hook boundary in `src/ui_mod/ui_mod_hook_template.py`.
  It does not import, patch or modify `src/core/runtime_hook_template.py`.
- The normal translation hook is protected by a regression hash contract
  (`bee504f9327f240b7714949615b4077a5687feb7583e00ab9fa7e5f08782132a` at the time this boundary was introduced).
- MOD development is fail-closed for Ren'Py variables/tags: unsafe candidates
  must be rejected instead of heuristically rewriting variables.
- Original `.rpy`, `.rpyc` and `.rpa` game sources are defined as read-only
  inputs for this feature.
- Scanner/parser integration is intentionally not enabled in this revision.
  This staging keeps unfinished MOD logic from affecting the working translator.
- See `MOD_ARCHITECTURE.md`.

## Known boundaries
- The language-menu integrator intentionally refuses unsafe custom UI patterns rather than inventing code that may break a game.
- This environment can syntax-check Python and run synthetic integration checks but is not the final Windows Ren'Py runtime; each game's visual integration must still be tested in the actual game.
- A previously discussed transactional font-installation hardening is not claimed here as completed unless present in the source.

## File-level manifest
The following lists are generated by comparing this source tree with the RenLocalizer 2.8.19 baseline. Known renamed files are matched to their upstream equivalents.

- Upstream regular files: **207**
- LinguaNova regular files in this source tree: **210**
- Modified/renamed: **90**
- Added: **6**
- Removed: **3**
- Unchanged matched files: **114**

### Modified or renamed files

- `.gitattributes`
- `.github/workflows/release.yml`
- `.github/workflows/tests.yml`
- `.gitignore`
- `CHANGELOG.md`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `RenLocalizer.sh` → `LinguaNova.sh`
- `RenLocalizer.spec` → `LinguaNova.spec`
- `RenLocalizerCLI.sh` → `LinguaNovaCLI.sh`
- `README.md`
- `build/linux/AppRun`
- `build/linux/renlocalizer.desktop` → `build/linux/linguanova.desktop`
- `icon.ico` → `linguanova.ico`
- `icon.png` → `linguanova_logo.png`
- `locales/de.json`
- `locales/en.json`
- `locales/es.json`
- `locales/fa.json`
- `locales/fr.json`
- `locales/ja.json`
- `locales/ru.json`
- `locales/tr.json`
- `locales/zh-CN.json`
- `run.bat`
- `run.py`
- `run_cli.py`
- `scripts/compare_lexers.py`
- `src/__init__.py`
- `src/backend/app_backend.py`
- `src/cli_main.py`
- `src/core/__init__.py`
- `src/core/ai_translator.py`
- `src/core/constants.py`
- `src/core/diagnostics.py`
- `src/core/editor/project.py`
- `src/core/exceptions.py`
- `src/core/exporter.py`
- `src/core/marked_strings.py`
- `src/core/parser.py`
- `src/core/pipeline/extraction.py`
- `src/core/pipeline/orchestrator.py`
- `src/core/pipeline/saving.py`
- `src/core/pipeline/validating.py`
- `src/core/rpyc_reader.py`
- `src/core/runtime_hook_template.py`
- `src/core/syntax_guard.py`
- `src/core/tl_parser.py`
- `src/core/translator.py`
- `src/core/translators/__init__.py`
- `src/core/translators/services.py`
- `src/gui/qml/Main.qml`
- `src/gui/qml/components/EditorPage.qml`
- `src/gui/qml/components/GlossaryAddDialog.qml`
- `src/gui/qml/components/ToastNotification.qml`
- `src/gui/qml/components/WarningDialog.qml`
- `src/gui/qml/components/qmldir`
- `src/tools/__init__.py`
- `src/tools/font_helper.py`
- `src/tools/font_injector.py`
- `src/tools/glossary_extractor/extractor.py`
- `src/tools/lang_scripts.py`
- `src/utils/__init__.py`
- `src/utils/config.py`
- `src/utils/encoding.py`
- `src/utils/lang_detect.py`
- `src/utils/logger.py`
- `src/utils/path_manager.py`
- `src/utils/qt_runtime.py`
- `src/utils/unrpyc_adapter.py`
- `src/utils/update_checker.py`
- `src/version.py`
- `tests/test_cli_parity.py`
- `tests/test_desktop_notifications.py`
- `tests/test_editor_core.py`
- `tests/test_factory_reset.py`
- `tests/test_language_activation_tool.py`
- `tests/test_language_init.py`
- `tests/test_marked_strings.py`
- `tests/test_qt_runtime_fallback.py`
- `tests/test_release_linux_artifacts.py`
- `tests/test_renpy_specifics.py`
- `tests/test_rpa_parser.py`
- `tests/test_toolbox_fixes.py`
- `tests/test_toolbox_tools.py`
- `tests/test_update_checker.py`
- `tests/test_write_probe.py`

### Added files

- `COPYING`
- `MODIFICATIONS_LINGUANOVA.md`
- `NOTICE.md`
- `SOURCE_DISTRIBUTION.md`
- `build_windows.bat`
- `src/gui/qml/components/AboutDialog.qml`
- `src/core/work_queue.py`
- `src/ui_mod/models.py`
- `src/ui_mod/protect.py`
- `src/ui_mod/parser.py`
- `src/ui_mod/archive_scanner.py`
- `src/ui_mod/scanner.py`
- `src/ui_mod/generator.py`
- `tests/test_sdk_todo_incremental.py`
- `tests/test_mod_parser_isolation.py`
- `tests/test_mod_generator.py`
- `tests/test_mod_rpa_selective.py`
- `tests/test_serial_work_queue.py`

### Removed files

- `.github/FUNDING.yml`
- `_config.yml`
- `index.html`

The unchanged matched files are not enumerated because this record is specifically a modification manifest.

### 18. SDK-style incremental translation updates

- Incremental TL updates now follow Ren'Py's official append pattern: when a
  file receives genuinely new translation entries, LinguaNova appends
  `# TODO: Translation updated at YYYY-MM-DD HH:MM` immediately before the new
  update block.
- New TL files receive the same marker at creation time.
- If no new TLID/string survives de-duplication, the file is left unchanged and
  no extra TODO marker is added.
- Existing hand-edited translations are never rewritten during an incremental
  merge. If a merge itself fails, LinguaNova leaves the existing file untouched
  instead of falling back to an overwrite.

### 19. #MOD functional isolated interface-mod generator

- `MOD` is now functional as a first-class navigation page.
- Added an independent MOD parser/scanner for visible `.rpy`, orphan `.rpyc`
  and script members stored in `.rpa` archives.
- Visible `.rpy` files have priority; compiled/archive sources only fill gaps.
- Added strict MOD-only placeholder/tag protection with fail-closed rejection.
- Added a dedicated `ui_mod_hook_template.py`; the main
  `src/core/runtime_hook_template.py` is not imported or patched by MOD.
- Generated files use `trampa_<game>_<target-code>.rpy` and can be used without
  first creating a full LinguaNova translation.
- MOD translation operates only on interface candidates detected by its own
  scanner, not on the story/dialogue pipeline.

### 20. Non-interrupting FIFO work queue

- Added a serial application work queue shared by normal translation requests
  and MOD requests.
- Submitting new work while another operation is active never stops/replaces
  the active process; new requests are appended FIFO and start afterward.
- Explicit Stop remains a user action and is not triggered by queue submission.

### 21. #MOD in-game behavior and hook-difference documentation

- Documented directly in the MOD page that the generated interface MOD loads
  automatically with Ren'Py, without a `Trampa`/`Cheat` button or F8 hotkey.
- Documented that `linguanova_mod_` is a filename convention only.
- Documented preservation of the original game interface and coexistence with
  translations obtained elsewhere.
- Added a visible comparison of the main translation hook and the isolated MOD hook.
- Corrected the stale status string that still said the MOD scanner/parser was disabled.


### 22. #MOD selection flow, plain-language UI and final file name

- MOD now has its own temporary game path, independent from the Translation page.
- The MOD path is read-only in the interface and is never saved between sessions.
- Users can select a game executable or a game folder directly from the MOD page.
- Selecting a game immediately schedules the MOD analysis; Generate MOD uses the same temporary MOD path.
- The interface explains that LinguaNova inspects the complete `game/` folder and skips installed translations, saves and temporary data.
- The generated file was renamed from the earlier `trampa_...` convention to `linguanova_mod_<game>_<target>.rpy`.
- The MOD header now shows `MOD` with a short description instead of falling back to `LINGUANOVA`.
- User-facing MOD explanations were rewritten in plain language and no longer expose internal terms such as parser, hook, callback or pipeline.
- Spanish user-facing help text received an additional plain-language pass for common internal terminology.


### 23. #MOD responsive layout for 1366x768 and compact-height displays

- The MOD page now uses an explicit vertical scroll range, matching the behavior of LinguaNova's other long workspaces.
- Added `viewMod` and `modContent` with real content height, centered responsive width and an automatic vertical scrollbar only when needed.
- On compact-height screens with enough horizontal space, including 1366x768, the three explanatory MOD cards share one row instead of consuming most of the screen vertically.
- On narrower windows those cards automatically return to one column.
- MOD card padding, spacing, text size and action-button height now react to LinguaNova's existing responsive breakpoints.
- If translated interface text becomes taller, the lower MOD controls remain reachable by scrolling instead of being cut off.
- This revision changes presentation only. Translation logic, the main hook, the MOD hook, parsers, queue and generator remain unchanged.


### 24. Editable standalone source and readable apostrophes before compilation

- The standalone single-file development build now refreshes its extracted project automatically when the `.py` file itself changes.
- Small manual edits to embedded UI text can therefore be saved and tested immediately without manually deleting LinguaNova's extracted cache or recalculating `PROJECT_SHA256`.
- Frozen/compiled builds keep using the official project hash; the editable-source behavior applies only when running the standalone `.py` directly.
- The readable single-file serializer now writes embedded text with double-quoted Python literals, so normal apostrophes such as `Ren'Py`, `game's`, `it's` and `you're` no longer appear as visually broken `\'` words merely because of the outer container format.
- A few inner-source word escapes that were unnecessary in double-quoted contexts were normalized as well.
- Translation behavior, both runtime translation hooks, MOD generation logic, parsers and the work queue remain unchanged.

### 25. GitHub publication, provenance and GPL-governance hardening

- Prepared LinguaNova for publication as a new, separately maintained GitHub repository while keeping RenLocalizer provenance deliberately prominent.
- Reworked `README.md` and `NOTICE.md` so the upstream project, original copyright notice, GPL-3.0-or-later status, modification date and non-affiliation are visible without implying that LinguaNova is an original or official RenLocalizer release.
- Added `UPSTREAM.md` and `LICENSE_POLICY.md` to separate project identity from upstream copyright/licensing and to state explicitly that no additional non-commercial restriction is imposed on GPL rights.
- Replaced the previous contribution/community wording that purported to forbid sale or commercial redistribution. The current `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` govern contributions/community behavior without narrowing GPL-3.0-or-later rights.
- Added `THIRD_PARTY_NOTICES.md` with an explicit pre-release binary-audit requirement instead of claiming that the current source dependency list is already a complete compiled-binary license inventory.
- Added `SECURITY.md`, `SUPPORT.md`, GitHub Issue/PR templates, a first-upload guide and a release checklist/template.
- Added `scripts/check_repository_compliance.py` and a GitHub Actions compliance workflow to detect missing legal/provenance files, accidental upstream-update configuration, high-confidence secrets and reintroduction of conflicting non-commercial wording.
- The public update source remains unconfigured; this revision does not activate a LinguaNova download channel and does not fall back to RenLocalizer.
- Application translation/runtime behavior is unchanged by this documentation/publication hardening.

### 26. MOD language-mixing correction (root cause) — 2026-10-17

Confirmed on the Portuguese→Polish report (3,493 published pairs: ~990 still Portuguese, ~865 mixed, 236 only re-capitalised, 213 Python/debug strings "translated"):

- **Language codes:** MOD now resolves every language through the central catalogue (`src/ui_mod/languages.py`, 135 languages). The former 10-entry table forwarded Ren'Py folder names (`"polish"`) to the engines for 125 languages.
- **Source language:** `auto` is resolved like the main pipeline (offline py3langid, then the engine's detector). Before, `sl=auto` reached Google's batch-separator request, which detects one language for up to 50 joined, alphabetically sorted strings; batches full of English/debug strings were read as English and the Portuguese was left in place.
- **Acceptance policy** (`src/ui_mod/quality.py`): structure/placeholders, target writing system, language identification of the whole answer and of each sentence, verbatim source fragments and untranslated residue. Rejected answers are retried one by one with per-string detection and otherwise stay pending; identical or case-only answers are "unchanged", not translations.
- **Caches:** MOD bypasses the shared TranslationManager cache (keyed by target+text, ignoring the source) and keeps its own provenance in `linguanova_mod_hook_data.json` (schema 2). `linguanova_mod_manual.json` now holds only hand edits; the old file mirrored every machine answer and was re-read as "manual". Data without provenance is backed up and retranslated, never trusted.
- **Candidates** (`src/ui_mod/filters.py`): Python source, expressions, identifier lists and debug formats (`%r`, `key=%s`) are excluded; whole `_("...")` calls are unwrapped.
- **Engines** (`src/ui_mod/engine_support.py`): DeepL receives `ZH-HANT`/`ZH-HANS`/`NB`/`KMR` (the main mapping sent `ZH` for Traditional Chinese and unsupported `NO`/`KU`); targets DeepL does not document are refused before any request; OpenAI/Gemini prompts get English language names for codes the prompt table does not name. Main translators are unchanged.
- **Output:** readable multilanguage `.rpy` (one `"original": "translation",` line per entry, all languages embedded; previously a zlib+base85 blob). Files are staged, the hook is compiled and initialised against stubs (catches `NameError`), previous MOD files are backed up as `.bak` and everything is replaced together with rollback on failure. A run that translates nothing writes nothing.
- **Old MOD native files:** `game/tl/<language>/linguanova_mod_*` / `trampa_*` script files from earlier MOD builds are no longer reused as "existing translations"; they are listed in the report (Ren'Py still loads them, so they must be moved out by the user). MOD never deletes them.
- **Honest completion status:** a run that leaves texts pending is reported as "MOD incomplete" (warning colour and log level, pending/unchanged/excluded counts, report file) instead of the "MOD generated" success text. New locale key `mod_status_generated_partial` in the nine interface languages.
- **Hand edits at runtime:** the hook overlays `game/tl/<language>/linguanova_mod_manual.json` on load, so a corrected translation shows after restarting the game without regenerating; a damaged JSON is ignored. The generated `.rpy` explains in Spanish where and how to edit.
- **Isolation:** `app_backend.py` imports the MOD lazily inside the MOD job, so a broken MOD package cannot stop the main translator.
- Tests: `tests/test_mod_language_contract.py`, `tests/test_mod_ui_language_independence.py`, `tests/test_mod_engine_language_transmission.py`; three existing MOD tests were adapted to the corrected behaviour (real fake translations, readable hook, MOD cache reuse).

### 27. Removal of the Local LLM and Custom engines — 2026-10-17

- Removed the Local LLM engine (Ollama / LM Studio / built-in llama.cpp GGUF runner), its server manager `src/core/local_llm_server.py`, constants, settings, backend properties, CLI options and Settings UI.
- Removed the Hy-MT2 model profile (`ai_model_profile`, profile detection, Hy-MT prompt templates and sampling), which was only exposed for Local LLM. Generic OpenAI/DeepSeek/Gemini prompting is unchanged; `ai_batch_format="single"` remains available.
- Removed the Custom endpoint engine (`custom_endpoint_url`, `custom_endpoint_api_key`, UI and CLI). LibreTranslate remains.
- MyMemory was not present in this code base.
- Old configuration files load normally: unknown keys are ignored and a saved `selected_engine` of `local_llm`/`custom` falls back to Google.
- Locale keys used only by the removed engines were deleted from the nine interface languages; texts that pointed users to Ollama/LM Studio/Hy-MT were reworded.
- Inventory: `EXPECTED_FILES = 252`, `EXPECTED_PY_FILES = 194`.

### 28. MOD: compiled games, whole tagged text, fonts/RTL, language panel, glossary — 2026-10-17

- **Compiled games:** orphan `.rpyc`/`.rpymc` files and `.rpyc` members of `.rpa` archives are read in memory with the existing `src/core/rpyc_reader.py` (say, menu and screen text). Nothing is extracted or written into the game folder; unreadable files are counted (`compiled_scripts_unreadable`).
- **Whole tagged text (hook format 4):** every translation is registered once, whole, in Ren'Py's native string table at `config.start_callbacks` (after all of the game's `translate strings` blocks); texts the game already translates are skipped. Dialogue such as `Olá {b}Anna{/b}, leve a {color=#f00}chave{/color} [tower]` is sent as one request (tags/variables protected) and shown whole. `config.replace_text` now only fills printf/`{0}` templates. Say/menu strings follow Ren'Py's lexer rules (space collapsing, `\n`, escapes) so keys match the game.
- **Fonts and RTL** (`src/ui_mod/fonts.py`): game fonts (visible or in `.rpa`) are checked with fontTools against the letters the translation uses; only fonts that cannot draw them are mapped to a Google Fonts family (via the existing `font_injector`) stored in `game/linguanova_mod_fonts/`. Mapping is applied/reset per language with `translate <lang> python:` blocks. RTL languages enable `config.rtl`. If no font can be obtained, the translation is still published and the report says so.
- **Language panel:** overlay button "Idioma / Language" and Shift+L open a panel with "Original" plus every MOD language and its progress; the native `Language()` action switches immediately. New players get `config.default_language` only when the game defines none.
- **Glossary** (`src/ui_mod/glossary.py`): one file per language (`linguanova_mod_glossary.json`), seeded with `Character("...")` names kept as is; terms are protected as tokens before sending and restored; whole-string terms need no engine; cached lines inconsistent with the glossary are retranslated. LinguaNova's main glossary is not used (it has no language).
- **Self-check:** `src/ui_mod/hook_check.py` runs the generated hook against a stand-in of the Ren'Py pieces it uses (string table that refuses duplicates, config, loader) before publishing. It is not Ren'Py: screens and fonts are not rendered.
- Tests: `tests/test_mod_five_points.py` (synthetic `.rpyc`/`.rpa`, fontTools-built fonts, simulated engine); existing MOD tests moved to the new runtime model.
- **Localized MOD messages:** every message the MOD generator returns or reports as progress (`No interface text candidates were detected.`, unknown language, same language, engine unsupported, all rejected, analysis, generated/partial, old-files warning, progress lines) has a locale key `mod_msg_*` / `mod_progress_*` in the nine interface languages; the backend passes its translator to the generator, English remains the fallback. The JSON report stays in English (technical file).
- **Backend fix found while doing this:** `AppBackend._t()` did not accept format values, but the MOD finish handler already called it with them (`translated=`, `count=`...), so in the official base every finished MOD job raised `TypeError` inside the Qt slot: the status was never updated and the work queue was not released. `_t()` now forwards the values to `ConfigManager.get_ui_text()`.

### 29. Reliability audit: syntax safety, honest counters, language integration — 2026-10-18

Root causes reproduced with the strings from the user's "iNSight of you ver.13" runs (Ren'Py 8.0.3); regression tests in `tests/test_audit_20261018.py`.

- **SDK files: escaped quotes before "with" broke the game** (`src/core/tl_parser.py`). The say-line regexes used a lazy `.*?` that stopped at an escaped quote: in `s "Bring the \"results\" with you."` the text ended at `\"results\` and ` with you."` was taken for a `with` clause, so the rewrite produced `s "Y trae los \"resultados\"" with you."` ("is not terminated with a newline"). The string body is now escape-aware. Lines already damaged this way are detected (a clause never contains a quote), retranslated and rewritten with the comment line's real clauses. A comment line whose translation line did not match was silently dropped from the file; it is now kept.
- **Inverted tags crashed the game** (`src/core/tag_structure.py`, new). Tags were compared as a multiset, so `Encontré el perfil {/i} de este {i}Dude.` passed and Ren'Py raised `'/i' closes a text tag that isn't open`. A check that mirrors Ren'Py 8.0.3's `check_text_tags`/`tokenize` is applied by the main guard (`renpy_tag_order_invalid`), the MOD (`tag_order_invalid`) and `strings.json`; existing tl lines with this defect are reopened for retranslation.
- **U+FFFD**: translations carrying replacement characters not present in the source are rejected (`replacement_char`). Mostly-UTF-8 files with a few non-UTF-8 lines are now decoded line by line (cp1252/latin-1 for those lines) instead of `errors="replace"`, and `normalize_to_utf8_sig` only rewrites files that need it.
- **Empty slots showed empty lines in game**: Ren'Py displays `e ""`/`new ""` literally. Untranslated or failed slots are written with the source text (like Ren'Py's own template); files with empty slots are rewritten even when no new translation arrived; the game-folder flow now retries source copies like the TL-folder flow.
- **Honest counters**: `get_translation_stats` no longer counts source copies as translated (`same_as_source`, `empty`). Each run records engine failures, guard blocks, cache hits and technical lines not sent; the result carries `partial`, the completion text gives the breakdown (the TL flow reported `len(translations)` — ids and texts counted twice — and a Turkish literal). The GUI shows a warning banner/toast for partial runs; a post-save quote check reports any line Ren'Py could not parse; a stop caused by the engine quota is no longer reported as "stopped by the user".
- **MOD**: final progress line after retries, the execution banner is cleared when a MOD job starts and shows MOD numbers at the end, MOD page shows translated / no change / pending / excluded (they add up), the report explains each counter and lists pending texts per file plus long UI translations that may overflow fixed boxes. Native identity entries (`"Skip"`→`"Skip"`) no longer hide the MOD's translation. Native dialogue translations in `tl/` are reused. Whole-chunk failures are retried with a pause before single requests; retry concurrency 4→2.
- **In-game experience**: the MOD panel shows language names only (no counters, no "LinguaNova MOD"); its button appears only in the game's menus (Shift+L anywhere) and it also lists the game's other tl/ languages by their visible names.
- **Language integration**: a data-driven selector (`for label, code in languages:`) was skipped because it has one `Language()` action; it is now extended. A game with no selector at all gets a small picker (`zzz_linguanova_language_menu.rpy`) that uses `Language()` with the folder id and shows the native name ("Español"); nothing is forced at start-up and no game screen is modified. Games with their own selector that cannot be extended are left untouched.
- **Incremental merge**: `merge_tl_content` and `_extract_tl_string_entries` cut an `old` text at its first escaped quote, so `Say \"bye\" later` was taken for a duplicate of `Say \"hi\" now` and never added; both now use the escape-aware string body.
- **Locales**: new keys in the nine interface languages; `[DE ACUERDO]`/`[ADVERTIR]` log tags in Spanish became `[ÉXITO]`/`[AVISO]`; guard reasons are now found by `get_log_text` (they were only at top level and always showed in English).
- Inventory: `EXPECTED_FILES = 258`, `EXPECTED_PY_FILES = 200` (new `src/core/tag_structure.py`, `tests/test_audit_20261018.py`).

### 30. Repository: contribution guide, CI test drift — 2026-10-18

- `CONTRIBUTING.md` (English) and `CONTRIBUTING.es.md` (Spanish) with Developer Certificate of Origin sign-off (`git commit -s`); bilingual pull-request template. Neither adds any restriction to GPL-3.0-or-later.
- Seven tests had drifted from the code and failed in every CI job (they also failed before the 2026-10-18 audit): the zzz_<lang>_language.rpy tests (that file is no longer written; RTL is now checked in the runtime hook), the CLI menu test (its sample game already listed German), the `.rpyc` fake (missing `progress_callback`), the header label string, the stop-button text window, and the macOS stub (missing `_is_translating`). The tests now check the current behaviour; no product code changed.
- `tests/test_mod_isolation_contract.py` hashed `runtime_hook_template.py` byte for byte, so it failed on Windows, where git checks the file out with CRLF. The hash is now taken over the LF form.
- **Update check**: a check that failed (no network, no published release, HTTP error) was reported as "You are up to date". It now shows "Update check failed: <reason>" and the log names the repository being checked.
- **Update dialog**: it said "Press OK to download" although its button is "Download", showed "vv1.0.1" for a `v1.0.1` tag and closed on any click outside it. The text now names the installed and the new version and the Download button (nine languages), the duplicated "v" is removed and the dialog closes only with its buttons or Esc.

### 31. Windows installer, automatic update, user interface languages — 2026-10-18 (version 1.1.0)

- **Installer** (`installer/LinguaNova.iss`, new; `build_installer.bat`, new). A drive page lists only the PC's internal drives: fixed drives (`GetDriveType`), minus disks connected by USB (WMI `Win32_DiskDrive` InterfaceType `USB` and `MSFT_Disk` BusType 7, which also covers UAS enclosures). The folder is always `<drive>:\LinguaNova`; drives without 1 GB free are shown disabled. Per-user install (`PrivilegesRequired=lowest`), fixed `AppId`, previous folder reused on updates, Windows 10/11 x64 only, desktop (optional, on by default) and Start menu shortcuts with AppUserModelID `LinguaNova` (the same as `run.py`), a taskbar-pinning tip on the last page (Windows does not allow installers to pin). Nine wizard languages: seven from Inno Setup, Chinese Simplified and Farsi shipped in `installer/languages/` with the Inno Setup License. The installer writes `linguanova_installed.json` (installed build marker and wizard language).
- **Automatic update** (`src/utils/auto_updater.py`, new). Only for the installed Windows build. The update check now returns the release assets; the update needs `LinguaNova_Setup_<version>.exe` and `SHA256SUMS.txt` hosted under this repository's `releases/download/`. The installer is downloaded to `%TEMP%\LinguaNova_update` with progress and cancel, verified with SHA-256 (a mismatch deletes it), run with `/VERYSILENT /DIR=<current folder> /LNUPDATE`, LinguaNova quits and the installer reopens it; leftovers are removed on the next start. Any failure keeps the release-page button.
- **Utilities → Updates** card: installed version, manual check, start-up check option (the setting existed but had no control). The "no update" message includes the installed version.
- **First interface language**: `installer_ui_language()` uses the wizard's language when no language is saved yet; otherwise the existing system-language detection applies.
- **User interface languages**: `<data dir>/locales/*.json` are loaded after the built-in ones. A built-in name (`es.json`) overrides only the keys it contains; any other name adds a language listed in Settings with ✏️ and its `_language_name`. Missing keys fall back to English.
- **Utilities → Create an interface language** (`src/utils/ui_language_generator.py`, new): machine-translates `en.json` with the selected engine. Placeholders (`{x}`, `%s`, `%(x)s`, tags, line breaks, URLs) are split out and never sent, so they cannot be lost; texts whose pieces were not all translated are left out (English). The file is written atomically, keeping a `.bak` of a previous one.
- `release.yml`: installs Inno Setup on the Windows runner, builds `LinguaNova_Setup_<version>.exe`, uploads it and includes it in `SHA256SUMS.txt`.
- Version 1.1.0. Tests: `tests/test_updates_installer_20261018.py`.

### 32. Translation cache, Ren'Py output and Windows source startup — 2026-10-20

- Cache writes and every cache lookup reject blank translations and translations
  that only repeat the source text. When loading an older cache, these source
  copies are dropped and the cleaned cache is marked dirty so a later save
  removes them from disk.
- The pipeline does not accept an unchanged external-TM/cache/engine result as
  a new translation. Empty engine results are treated as failures; unchanged
  engine results are counted as pending and appear in the partial completion
  status. The Ren'Py source fallback remains in place to avoid empty dialogue.
- Existing valid manual translations are preserved when a candidate is only a
  source copy. Supported `old`/`new` and dialogue translation lines containing
  a trailing `#ignore` comment are parsed and rewritten without that suffix.
- On Windows, `run.bat` recovers from `venv` failing during `ensurepip` by
  creating the environment with `--without-pip` and installing `pip` into it
  from the selected Python installation.
- Regression tests cover poisoned legacy caches, retranslation, empty and
  unchanged results, pending statistics, preserving manual text, and clean
  `#ignore` output.
