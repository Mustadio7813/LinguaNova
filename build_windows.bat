@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LinguaNova - Compilar para Windows

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
REM LinguaNova - Windows build script
REM Generates: dist\LinguaNova\LinguaNova.exe
REM Uses the SAME project-local .venv as run.bat.
REM ============================================================

echo ========================================
echo       LinguaNova - Compilacion Windows
echo ========================================
echo.

call :find_python
if errorlevel 1 (
    echo [ERROR] No se encontro Python 3.10 o superior de 64 bits.
    echo Se recomienda Python 3.12 de 64 bits.
    pause
    exit /b 1
)

echo [INFO] Interprete base: %PY_CMD%
%PY_CMD% --version
%PY_CMD% -c "import struct; print(str(struct.calcsize('P')*8) + ' bits')"

%PY_CMD% -c "import sys,struct; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] La compilacion requiere Python 3.10+ de 64 bits.
    pause
    exit /b 1
)

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

REM Existing environments can belong to a removed/old Python. Validate first.
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys,struct; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] El .venv existente no es compatible. Se reconstruira.
        rmdir /s /q "%VENV_DIR%"
    )
)

if not exist "%VENV_PY%" (
    echo [1/5] Creando entorno virtual...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
) else (
    echo [1/5] Entorno virtual encontrado y validado.
)

if not exist "%~dp0requirements.txt" (
    echo [ERROR] No se encontro requirements.txt.
    goto :fail
)
if not exist "%~dp0LinguaNova.spec" (
    echo [ERROR] No se encontro LinguaNova.spec.
    goto :fail
)

echo [2/5] Instalando dependencias en el entorno del proyecto...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

if exist "%~dp0constraints-release.txt" (
    "%VENV_PY%" -m pip install -c "%~dp0constraints-release.txt" pyinstaller
    if errorlevel 1 goto :fail
    "%VENV_PY%" -m pip install -c "%~dp0constraints-release.txt" -r "%~dp0requirements.txt"
    if errorlevel 1 goto :fail
) else (
    "%VENV_PY%" -m pip install pyinstaller
    if errorlevel 1 goto :fail
    "%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 goto :fail
)

echo [3/5] Verificando entorno antes de compilar...
"%VENV_PY%" -c "import PyQt6,aiohttp,requests,charset_normalizer,orjson,py3langid,openai,google.genai,unrpa,rpycdec,rich,yaml,fontTools; from src.version import VERSION; from src.utils.encoding import read_text_safely; print('       LinguaNova ' + VERSION + ' - entorno OK')"
if errorlevel 1 goto :fail
"%VENV_PY%" -m pip check
if errorlevel 1 goto :fail

"%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)" >nul 2>&1
if not errorlevel 1 if exist "%~dp0scripts\patch_aiohttp.py" (
    "%VENV_PY%" "%~dp0scripts\patch_aiohttp.py" >nul 2>&1
)

echo [4/5] Compilando con PyInstaller...
"%VENV_PY%" -m PyInstaller --noconfirm --clean "%~dp0LinguaNova.spec"
if errorlevel 1 goto :fail

echo [5/5] Compilacion finalizada.
echo.
echo Carpeta de salida: %~dp0dist\LinguaNova\
echo Ejecutable:        %~dp0dist\LinguaNova\LinguaNova.exe
echo.
echo Distribuye la carpeta completa dist\LinguaNova\; el EXE no funciona solo.
pause
exit /b 0

:fail
echo.
echo [ERROR] La compilacion fallo. Revisa los mensajes mostrados arriba.
echo El entorno usado es: %VENV_PY%
pause
exit /b 1

:find_python
set "PY_CMD="

py -3.12 -c "import sys,struct; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
if not errorlevel 1 set "PY_CMD=py -3.12"

if not defined PY_CMD (
    py -3.11 -c "import sys,struct; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.11"
)

if not defined PY_CMD (
    py -3.10 -c "import sys,struct; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.10"
)

if not defined PY_CMD (
    python -c "import sys,struct; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    py -3 -c "import sys,struct; raise SystemExit(0 if sys.version_info >= (3,10) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD exit /b 1
exit /b 0
