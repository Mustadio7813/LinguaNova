@echo off
setlocal EnableExtensions
title LinguaNova - Instalador de Windows
cd /d "%~dp0"

REM ======================================================================
REM  Genera el instalador de Windows de LinguaNova:
REM    installer\Output\LinguaNova_Setup_{version}.exe
REM    installer\Output\LinguaNova-Windows-x64.zip   (version portable)
REM    installer\Output\SHA256SUMS.txt               (huellas para el actualizador)
REM  Necesita Inno Setup 6.5 o superior: https://jrsoftware.org/isdl.php
REM  Si dist\LinguaNova\ no existe, ejecuta antes build_windows.bat.
REM ======================================================================

echo.
echo ==========================================================
echo   LinguaNova - Generar instalador de Windows
echo ==========================================================
echo.

if not exist "dist\LinguaNova\LinguaNova.exe" (
    echo [INFO] No existe dist\LinguaNova\LinguaNova.exe. Se compila primero con build_windows.bat.
    echo.
    call "%~dp0build_windows.bat"
    if not exist "dist\LinguaNova\LinguaNova.exe" (
        echo [ERROR] La compilacion no genero dist\LinguaNova\LinguaNova.exe.
        goto :fail
    )
)

REM --- Inno Setup ----------------------------------------------------------
set "ISCC="
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
    if not defined ISCC if exist %%P set "ISCC=%%~P"
)
if not defined ISCC (
    for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
)
if not defined ISCC (
    echo [ERROR] No se encontro Inno Setup 6.5 o superior.
    echo Descargalo e instalalo desde https://jrsoftware.org/isdl.php y vuelve a ejecutar este archivo.
    goto :fail
)
echo [INFO] Inno Setup: %ISCC%

REM --- Version ---------------------------------------------------------------
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (
    py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
)
if not defined PY set "PY=python"
set "VER="
for /f "delims=" %%V in ('%PY% -c "from src.version import VERSION; print(VERSION)"') do set "VER=%%V"
if not defined VER (
    echo [ERROR] No se pudo leer la version de src\version.py.
    goto :fail
)
echo [INFO] Version: %VER%
echo.

REM --- Compilar el instalador -------------------------------------------------
"%ISCC%" /Qp "/DMyAppVersion=%VER%" "installer\LinguaNova.iss"
if errorlevel 1 (
    echo [ERROR] Inno Setup no pudo generar el instalador.
    goto :fail
)

REM --- Portable y huellas ----------------------------------------------------------
set "OUT=installer\Output"
if exist "%OUT%\LinguaNova-Windows-x64.zip" del /f /q "%OUT%\LinguaNova-Windows-x64.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\LinguaNova' -DestinationPath '%OUT%\LinguaNova-Windows-x64.zip'"
if errorlevel 1 (
    echo [ERROR] No se pudo crear el ZIP portable.
    goto :fail
)
powershell -NoProfile -Command "Get-ChildItem '%OUT%' -File | Where-Object { $_.Name -like 'LinguaNova*' -and $_.Name -ne 'SHA256SUMS.txt' } | ForEach-Object { (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower() + '  ' + $_.Name }" > "%OUT%\SHA256SUMS.txt"
if errorlevel 1 (
    echo [ERROR] No se pudo generar SHA256SUMS.txt.
    goto :fail
)

echo.
echo ==========================================================
echo   Listo. Archivos en %~dp0%OUT%\
echo ==========================================================
dir /b "%OUT%"
echo.
echo   Para publicar una version, sube LOS TRES archivos a la Release:
echo     LinguaNova_Setup_%VER%.exe, LinguaNova-Windows-x64.zip y SHA256SUMS.txt
echo   Sin SHA256SUMS.txt el programa no actualiza solo: abre la pagina.
echo.
pause
exit /b 0

:fail
echo.
pause
exit /b 1
