@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv-next-worker
if errorlevel 1 goto failed
.venv-next-worker\Scripts\python.exe -m pip install -r requirements-next-inference.txt
if errorlevel 1 goto failed
.venv-next-worker\Scripts\python.exe -m PyInstaller --noconfirm --clean LinguaNova_next_worker.spec
if errorlevel 1 goto failed
echo Worker folder: dist\LinguaNovaInference
echo Add all dependency licenses and create component_manifest.json with scripts\next_prepare_component.py.
echo No model weights are included. Run the actual inference acceptance test before distribution.
exit /b 0
:failed
echo Inference worker build failed.
pause
exit /b 1
