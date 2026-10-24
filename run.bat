@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LinguaNova
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0start.py" %*
    goto result
)
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 (
    python "%~dp0start.py" %*
    goto result
)
echo No se encontro Python. Para ejecutar las fuentes se necesita Python 3.10 o superior.
echo La version compilada LinguaNova.exe no necesita Python instalado.
pause
exit /b 1
:result
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo No se pudo iniciar. Revisa inicio_error.log junto a este archivo.
    pause
)
exit /b %APP_EXIT%
