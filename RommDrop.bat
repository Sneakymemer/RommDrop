@echo off
:: %~dp0 is a special variable that means "the folder this bat is in"
set PYTHON_PATH=%~dp0python\python.exe
set SCRIPT_PATH=%~dp0romm_drop.py

echo Starting RomM Drop...
"%PYTHON_PATH%" "%SCRIPT_PATH%"
pause