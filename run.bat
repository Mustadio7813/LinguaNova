@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LinguaNova

REM Do not run the project from inside WinRAR/7-Zip temporary extraction folders.
echo(%~dp0| findstr /L /I /C:"Rar$" /C:"7z" >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] LinguaNova parece estar ejecutandose desde una carpeta temporal del compresor.
    echo Extrae TODO el ZIP a una carpeta normal y ejecuta este BAT desde alli.
    echo.
    pause
    exit /b 1
)

REM ============================================================
REM LinguaNova - Windows launcher
REM Uses one project-local environment (.venv) for install + run.
REM ============================================================

echo ========================================
echo        LinguaNova - Iniciando...
echo ========================================
echo.

set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

REM A virtual environment copied from a WinRAR temporary folder is not portable.
if exist "%VENV_DIR%\pyvenv.cfg" (
    findstr /L /I /C:"Rar$" "%VENV_DIR%\pyvenv.cfg" >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] Se detecto un .venv creado dentro de WinRAR. Se reconstruira.
        rmdir /s /q "%VENV_DIR%"
    )
)

call :find_python
if errorlevel 1 (
    echo [ERROR] No se encontro Python 3.10 o superior.
    echo Se recomienda Python 3.12 de 64 bits.
    echo.
    pause
    exit /b 1
)

REM Recreate a stale/broken environment instead of silently reusing it.
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] El entorno .venv existente no es valido. Se reconstruira.
        rmdir /s /q "%VENV_DIR%"
    )
)

if not exist "%VENV_PY%" (
    echo [1/4] Creando entorno virtual local...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :venv_fail
) else (
    echo [1/4] Entorno virtual local encontrado.
)

echo       Interprete del proyecto: %VENV_PY%
"%VENV_PY%" --version

if not exist "%~dp0requirements.txt" (
    echo [ERROR] No se encontro requirements.txt junto a run.bat.
    pause
    exit /b 1
)

REM The import check uses the SAME interpreter that will launch the app.
echo [2/4] Verificando dependencias...
"%VENV_PY%" -c "import PyQt6,aiohttp,requests,charset_normalizer,orjson,py3langid,openai,google.genai,unrpa,rpycdec,rich,yaml,fontTools; from src.version import VERSION; from src.utils.encoding import read_text_safely; print('       LinguaNova ' + VERSION + ' - dependencias OK')" >nul 2>&1
if errorlevel 1 (
    echo       El entorno esta incompleto. Instalando o reparando...
    "%VENV_PY%" -m pip install --upgrade pip
    if errorlevel 1 goto :pip_fail

    if exist "%~dp0constraints-release.txt" (
        "%VENV_PY%" -m pip install -c "%~dp0constraints-release.txt" -r "%~dp0requirements.txt"
    ) else (
        "%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
    )
    if errorlevel 1 goto :pip_fail
)

REM Final smoke check. This catches broken installs before the GUI starts.
echo [3/4] Comprobacion final del entorno...
"%VENV_PY%" -c "import PyQt6,charset_normalizer; from PyQt6.QtWidgets import QApplication; from src.version import VERSION; from src.utils.encoding import read_text_safely; print('       LinguaNova ' + VERSION + ' - entorno OK')"
if errorlevel 1 goto :pip_fail

"%VENV_PY%" -m pip check >nul 2>&1
if errorlevel 1 echo [AVISO] pip detecto un conflicto de dependencias; el programa intentara iniciar igualmente.

"%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" >nul 2>&1
if not errorlevel 1 if exist "%~dp0scripts\patch_aiohttp.py" (
    "%VENV_PY%" "%~dp0scripts\patch_aiohttp.py" >nul 2>&1
)

echo [4/4] Abriendo LinguaNova...
echo.
"%VENV_PY%" "%~dp0run.py"
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo [ERROR] LinguaNova termino con el codigo %APP_EXIT%.
    echo Revisa el mensaje mostrado arriba.
    pause
)
exit /b %APP_EXIT%

:venv_fail
echo.
echo [ERROR] No se pudo crear .venv.
echo Comprueba que Python incluya el modulo venv.
pause
exit /b 1

:pip_fail
echo.
echo [ERROR] No se pudieron instalar o cargar las dependencias dentro de:
echo         %VENV_PY%
echo.
echo No instales los paquetes en otro Python global; LinguaNova usa este .venv.
pause
exit /b 1

:find_python
set "PY_CMD="

py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3.12"

if not defined PY_CMD (
    py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.11"
)

if not defined PY_CMD (
    py -3.10 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.10"
)

if not defined PY_CMD (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD exit /b 1
exit /b 0
