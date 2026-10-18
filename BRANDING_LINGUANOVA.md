# LinguaNova Branding Assets

This document records the active visual identity of this LinguaNova release.

## Active application assets

- `linguanova_logo.png`
  - High-resolution LinguaNova logo used inside the application.
  - Used by the startup splash and About dialog.
  - Preferred cross-platform GUI/tray source.

- `linguanova.ico`
  - Multi-resolution Windows application icon.
  - Used by PyInstaller and native Windows window/taskbar integration.

- `linguanova.icns`
  - Generated at macOS release-build time from `linguanova_logo.png`.
  - It is not stored as a permanent embedded binary in this source file.

- Linux desktop/application id: `linguanova`
  - `build/linux/linguanova.desktop` uses `Icon=linguanova`.

## Deliberately retained upstream references

References to RenLocalizer in `NOTICE.md`, GPL attribution, source-file
modification notices, `MODIFICATIONS_LINGUANOVA.md` and historical
`CHANGELOG.md` entries are intentionally retained. They document the GPL
provenance of the fork and are not active product branding.

## Interface symbols

Unicode/emoji symbols such as ✅, ⚠️, ❌, 📁, 🔤, 🩺 and 📚 are functional UI
glyphs, not logos, so they remain unchanged.

## Future artwork replacement

Future LinguaNova artwork can be changed by replacing the binary contents of
`linguanova_logo.png` and `linguanova.ico` while preserving those filenames.
The active QML, Python and build scripts already point to the LinguaNova names.
