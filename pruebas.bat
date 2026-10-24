@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title LinguaNova - Pruebas del proyecto
set "TEST_PY=%~dp0.venv\Scripts\python.exe"

if not exist "%TEST_PY%" (
    echo [ERROR] Falta el entorno .venv. Ejecuta run.bat primero.
    goto :fail
)
"%TEST_PY%" "%~dp0scripts\verificar_proyecto.py" --dependencias
if errorlevel 1 goto :fail

"%TEST_PY%" -c "import pytest" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias de desarrollo en .venv...
    "%TEST_PY%" -m pip install -r "%~dp0requirements-dev.txt"
    if errorlevel 1 goto :fail
)

REM No arguments: run all original tests. Arguments: choose files or filters.
if "%~1"=="" (
    "%TEST_PY%" -m pytest tests/ -q --rootdir .
) else (
    "%TEST_PY%" -m pytest -q --rootdir . %*
)
set "TEST_EXIT=%ERRORLEVEL%"
if not defined CI pause
exit /b %TEST_EXIT%

:fail
echo [ERROR] No se pudieron ejecutar las pruebas. Revisa el mensaje anterior.
if not defined CI pause
exit /b 1
