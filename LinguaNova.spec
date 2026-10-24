# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
import os
import re
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
project_dir = os.path.abspath(os.getcwd())

# UPX stays OFF everywhere: GitHub runners ship no upx binary (so it was
# already a silent no-op in CI) and compressed unsigned bootloaders only
# raise antivirus ML-heuristic scores.
USE_UPX = False

# Windows version resource: proper PE metadata (ProductName/FileVersion/...)
# lowers generic packer-heuristic scores on unsigned builds and gives
# Defender submissions a legitimate identity to match against.
def _read_app_version() -> str:
    try:
        with open(os.path.join(project_dir, 'src', 'version.py'), encoding='utf-8') as fh:
            m = re.search(r'VERSION\s*=\s*"([^"]+)"', fh.read())
            return m.group(1) if m else '0.0.0'
    except OSError:
        return '0.0.0'

APP_VERSION = _read_app_version()
_ver_parts = [int(x) for x in APP_VERSION.split('.')] + [0] * 4
_ver_parts = _ver_parts[:4]

import tempfile

_version_info_path = os.path.join(
    tempfile.gettempdir(), f'LinguaNova_{APP_VERSION}_version_info.txt'
)
with open(_version_info_path, 'w', encoding='utf-8') as _vf:
    _vf.write(f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({_ver_parts[0]}, {_ver_parts[1]}, {_ver_parts[2]}, {_ver_parts[3]}),
    prodvers=({_ver_parts[0]}, {_ver_parts[1]}, {_ver_parts[2]}, {_ver_parts[3]}),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable("040904B0", [
        StringStruct("CompanyName", "LinguaNova"),
        StringStruct("FileDescription", "Ren'Py Visual Novel Localization Tool"),
        StringStruct("FileVersion", "{APP_VERSION}"),
        StringStruct("InternalName", "LinguaNova"),
        StringStruct("OriginalFilename", "LinguaNova.exe"),
        StringStruct("ProductName", "LinguaNova"),
        StringStruct("ProductVersion", "{APP_VERSION}"),
      ])
    ]),
    VarFileInfo([VarStruct("Translation")]),
  ])
""")

win_exe_kwargs = (
    {"version": _version_info_path} if sys.platform == "win32" else {}
)

# Automatically collect all submodules from src package
hidden_imports = collect_submodules('src')
hidden_imports += collect_submodules('linguanova_next')
for image_package in ('PIL', 'pillow_avif', 'resvg_py', 'defusedxml', 'numpy', 'cv2', 'rarfile'):
    hidden_imports += collect_submodules(image_package)

# Aggressively collect submodules for external libraries to prevent missing imports
hidden_imports += collect_submodules('aiohttp')
hidden_imports += collect_submodules('requests')
hidden_imports += collect_submodules('packaging')
hidden_imports += collect_submodules('charset_normalizer')
hidden_imports += collect_submodules('unrpa')
hidden_imports += collect_submodules('rpycdec')
hidden_imports += ['decompiler']  # unrpyc -> decompiler package
hidden_imports += collect_submodules('rich')
hidden_imports += collect_submodules('yaml')
hidden_imports += collect_submodules('certifi')
hidden_imports += collect_submodules('openai')
hidden_imports += collect_submodules('google.genai')
hidden_imports += collect_submodules('fontTools')
# Pandas submodules are too heavy (includes tests, matplotlib, etc). 
# Basic pandas import is usually enough or handled by auto-analysis.
# If needed, add only specific submodules manually.


# Manual additions for specific edge cases
hidden_imports.append('src.version')  # Ensure version module is bundled

if sys.platform == 'win32':
    hidden_imports.extend([
        'win32timezone',
    ])

# Force include PyQt6 specific plugins and hidden imports for Linux
if sys.platform != 'win32':
    hidden_imports.extend([
        'PyQt6.QtOpenGL',
        'PyQt6.QtNetwork',
        'PyQt6.QtPrintSupport',
    ])

# Define datas with absolute paths to avoid not found errors
datas_list = [
    (os.path.join(project_dir, 'linguanova_next', 'data'), 'linguanova_next/data'),
    (os.path.join(project_dir, 'locales'), 'locales'),
    (os.path.join(project_dir, 'linguanova.ico'), '.'),
    (os.path.join(project_dir, 'linguanova_logo.png'), '.'),
    # Add QML files
    (os.path.join(project_dir, 'src', 'gui', 'qml'), os.path.join('src', 'gui', 'qml')),
    # Add version.py for runtime reading
    (os.path.join(project_dir, 'src', 'version.py'), 'src'),
]

# A compiled app carries the OCR executable, its DLLs and traineddata. No pip,
# external Python or creator-side environment is used by the EXE.
ocr_component = Path(project_dir) / 'components' / 'tesseract'
if sys.platform == 'win32' and not (ocr_component / 'tesseract.exe').is_file():
    raise RuntimeError('Prepare OCR before building: python scripts/prepare_ocr_bundle.py. The compiled app must include Tesseract.')
if ocr_component.is_dir():
    datas_list.append((str(ocr_component), 'components/tesseract'))

# py3langid loads data/model.npz.xz at runtime and has no PyInstaller hook;
# without it offline language detection silently never runs in the exe.
try:
    datas_list += collect_data_files('py3langid')
except Exception:
    pass

# Add shell scripts only when building on non-Windows
if os.path.exists(os.path.join(project_dir, 'LinguaNova.sh')):
    datas_list.append((os.path.join(project_dir, 'LinguaNova.sh'), '.'))
if os.path.exists(os.path.join(project_dir, 'LinguaNovaCLI.sh')):
    datas_list.append((os.path.join(project_dir, 'LinguaNovaCLI.sh'), '.'))

binaries_list = []

if sys.platform == 'win32':
    try:
        import PyQt6

        pyqt_dir = Path(PyQt6.__file__).resolve().parent
        software_gl_dll = pyqt_dir / 'Qt6' / 'bin' / 'opengl32sw.dll'
        if software_gl_dll.exists():
            binaries_list.append((str(software_gl_dll), '.'))
    except Exception:
        pass


# =========================================================
# GUI Application Analysis (LinguaNova)
# =========================================================
a = Analysis(
    ['run.py'],
    pathex=[project_dir],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'tkinter', 'matplotlib', 'IPython', 'notebook', 'scipy.stats.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LinguaNova',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=USE_UPX,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, 'linguanova.ico') if sys.platform == 'win32' else None,
    manifest=os.path.join(project_dir, 'src', 'LinguaNova.manifest') if (sys.platform == 'win32' and os.path.exists(os.path.join(project_dir, 'src', 'LinguaNova.manifest'))) else None,
    **win_exe_kwargs,
)

# =========================================================
# CLI Application Analysis & Build (LinguaNovaCLI)
# =========================================================
a_cli = Analysis(
    ['run_cli.py'],
    pathex=[project_dir],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'tkinter', 'matplotlib', 'IPython', 'notebook', 'scipy.stats.tests',
              'PyQt6.QtQuick', 'PyQt6.QtQml', 'PyQt6.QtOpenGL', 'PyQt6.QtNetwork', 'PyQt6.QtPrintSupport',
              'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets', 'PyQt6.QtMultimedia', 'PyQt6.QtBluetooth'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_cli = PYZ(a_cli.pure, a_cli.zipped_data, cipher=block_cipher)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name='LinguaNovaCLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=USE_UPX,
    console=True,                       # CLI needs console!
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, 'linguanova.ico') if sys.platform == 'win32' else None,
    **win_exe_kwargs,
)

# =========================================================
# GUI Application COLLECT (LinguaNova)
# =========================================================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=USE_UPX,
    upx_exclude=[],
    name='LinguaNova',
)

# =========================================================
# CLI Application COLLECT (LinguaNovaCLI)
# =========================================================
coll_cli = COLLECT(
    exe_cli,
    a_cli.binaries,
    a_cli.zipfiles,
    a_cli.datas,
    strip=False,
    upx=USE_UPX,
    upx_exclude=[],
    name='LinguaNovaCLI',
)

# =========================================================
# macOS: BUNDLE → produces LinguaNova.app via PyInstaller
# Only active on macOS; other platforms skip this block.
# =========================================================
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='LinguaNova.app',
        icon=os.path.join(project_dir, 'linguanova.icns')
            if os.path.exists(os.path.join(project_dir, 'linguanova.icns'))
            else None,
        bundle_identifier='app.linguanova.desktop',
        version=APP_VERSION,
        info_plist={
            'CFBundleName': 'LinguaNova',
            'CFBundleDisplayName': 'LinguaNova',
            'CFBundleShortVersionString': APP_VERSION,
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
            'LSMinimumSystemVersion': '11.0',
            'LSApplicationCategoryType': 'public.app-category.utilities',
        },
    )

# =========================================================
# Post-build: Copy CLI binary into main GUI distribution folder
# =========================================================
import shutil

_gui_dist = os.path.join(project_dir, 'dist', 'LinguaNova')
_cli_dist = os.path.join(project_dir, 'dist', 'LinguaNovaCLI')

# Windows: one-click launcher that skips GPU rendering entirely, for machines
# where even the automatic OpenGL -> software GL -> raster chain cannot help.
if sys.platform == 'win32' and os.path.isdir(_gui_dist):
    try:
        with open(os.path.join(_gui_dist, 'LinguaNova_SafeGraphics.bat'), 'w', encoding='ascii', newline='\r\n') as _bf:
            _bf.write('@echo off\nstart "" "%~dp0LinguaNova.exe" --safe-graphics\n')
        print("[SPEC POST-BUILD] Wrote LinguaNova_SafeGraphics.bat")
    except Exception as e:
        print(f"[SPEC POST-BUILD] Warning: Could not write safe-graphics launcher: {e}")

if os.path.isdir(_gui_dist) and os.path.isdir(_cli_dist):
    for item in os.listdir(_cli_dist):
        if item.lower().startswith('linguanovacli'):
            src_file = os.path.join(_cli_dist, item)
            dst_file = os.path.join(_gui_dist, item)
            try:
                shutil.copy2(src_file, dst_file)
                print(f"[SPEC POST-BUILD] Merged {item} into dist/LinguaNova/")
            except Exception as e:
                print(f"[SPEC POST-BUILD] Warning: Could not merge {item}: {e}")





