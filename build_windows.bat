@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0scripts\build_main.py"
    goto result
)
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if not errorlevel 1 (
    python "%~dp0scripts\build_main.py"
    goto result
)
echo Se necesita Python 3.10 o superior para compilar.
pause
exit /b 1
:result
set "BUILD_EXIT=%ERRORLEVEL%"
if not "%BUILD_EXIT%"=="0" echo Revisa compilacion_error.log e inicio_error.log.
pause
exit /b %BUILD_EXIT%
