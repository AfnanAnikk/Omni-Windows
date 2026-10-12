@echo off
setlocal EnableDelayedExpansion

echo =======================================================
echo          Omni Desktop AI - One-Click Installer
echo =======================================================
echo.

cd /d "%~dp0\.."
set PROJECT_DIR=%CD%

:: Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.11+ from https://python.org and check "Add to PATH".
    pause
    exit /b 1
)

echo [*] Initializing virtual environment...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [*] Installing dependencies...
pip install -r windows\requirements_windows.txt

:: API Key Setup
if not exist ".env" (
    echo.
    echo -------------------------------------------------------
    set /p APIKEY="Enter your Google Gemini API Key: "
    if not "!APIKEY!"=="" (
        echo GEMINI_API_KEY=!APIKEY!> .env
        echo [*] GEMINI_API_KEY saved to .env!
    )
    echo -------------------------------------------------------
)

:: Create Desktop Shortcut using PowerShell
echo [*] Creating Desktop Shortcut...
set SHORTCUT_SCRIPT=$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([System.Environment]::GetFolderPath('Desktop'), 'Omni.lnk')); $s.TargetPath = '%PROJECT_DIR%\.venv\Scripts\pythonw.exe'; $s.Arguments = '\"%PROJECT_DIR%\main_windows.py\"'; $s.WorkingDirectory = '%PROJECT_DIR%'; if (Test-Path '%PROJECT_DIR%\resources\AppIcon.ico') { $s.IconLocation = '%PROJECT_DIR%\resources\AppIcon.ico' }; $s.Save()

powershell -NoProfile -ExecutionPolicy Bypass -Command "%SHORTCUT_SCRIPT%"

echo.
echo =======================================================
echo [SUCCESS] Omni has been installed!
echo - Desktop shortcut created: "Omni.lnk"
echo - Hotkey: Hold Ctrl + 0 to speak, release to answer.
echo =======================================================
echo.

set /p RUNNOW="Would you like to start Omni now? (Y/N): "
if /i "%RUNNOW%"=="Y" (
    start "" ".venv\Scripts\pythonw.exe" "main_windows.py"
)

exit /b 0
