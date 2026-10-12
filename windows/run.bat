@echo off
cd /d "%~dp0\.."
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    start "" ".venv\Scripts\pythonw.exe" "main_windows.py"
) else (
    start "" pythonw "main_windows.py"
)
