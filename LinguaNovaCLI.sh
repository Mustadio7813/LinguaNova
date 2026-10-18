#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova modified work; relevant modification date: 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
# LinguaNova CLI launcher for Linux/macOS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_BINARY="$SCRIPT_DIR/LinguaNovaCLI"
RUN_PY="$SCRIPT_DIR/run_cli.py"
VENV_DIR="$SCRIPT_DIR/venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

# Try PyInstaller bundle first, fallback to source
if [ -f "$APP_BINARY" ]; then
    exec "$APP_BINARY" "$@"
elif [ -f "$RUN_PY" ]; then
    # Auto-bootstrap venv if missing
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/pip" install -q -r "$REQ_FILE" 2>/dev/null || true
    fi
    exec "$VENV_DIR/bin/python" "$RUN_PY" "$@"
else
    echo "Error: LinguaNovaCLI not found in $SCRIPT_DIR"
    exit 1
fi
