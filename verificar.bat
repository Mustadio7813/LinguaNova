@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title LinguaNova - Verificar proyecto

set "CHECK_PY="
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(sys.version_info < (3,10))" >nul 2>&1
    if not errorlevel 1 goto :use_venv
)
if not defined CHECK_PY (
    py -3.12 -c "import sys; raise SystemExit(sys.version_info < (3,10))" >nul 2>&1
    if not errorlevel 1 set "CHECK_PY=py -3.12"
)
if not defined CHECK_PY (
    py -3 -c "import sys; raise SystemExit(sys.version_info < (3,10))" >nul 2>&1
    if not errorlevel 1 set "CHECK_PY=py -3"
)
if not defined CHECK_PY (
    python -c "import sys; raise SystemExit(sys.version_info < (3,10))" >nul 2>&1
    if not errorlevel 1 set "CHECK_PY=python"
)
if not defined CHECK_PY (
    echo [ERROR] No se encontro Python 3.10 o superior.
    if not defined CI pause
    exit /b 1
)

%CHECK_PY% "%~dp0scripts\verificar_proyecto.py" %*
set "CHECK_EXIT=%ERRORLEVEL%"
goto :finish

:use_venv
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\verificar_proyecto.py" %*
set "CHECK_EXIT=%ERRORLEVEL%"

:finish
if not defined CI pause
exit /b %CHECK_EXIT%
