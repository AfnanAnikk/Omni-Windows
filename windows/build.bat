@echo off
setlocal EnableDelayedExpansion

echo =======================================================
echo          Omni Desktop AI - Windows Build Script
echo =======================================================
echo.

cd /d "%~dp0\.."

:: 1. Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in PATH! Please install Python 3.11 or higher.
    pause
    exit /b 1
)

echo [1/4] Setting up Python virtual environment...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] Installing Windows requirements...
pip install -r windows\requirements_windows.txt

echo [3/4] Compiling Omni with PyInstaller...
pyinstaller windows\Omni.spec --noconfirm

if not exist "dist\Omni\Omni.exe" (
    echo [ERROR] PyInstaller build failed. Check logs above.
    pause
    exit /b 1
)

echo.
echo [4/4] Building Windows Installer with Inno Setup...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if exist %ISCC% (
    %ISCC% windows\installer.iss
    echo.
    echo =======================================================
    echo [SUCCESS] OmniSetup.exe generated in windows\Output\
    echo =======================================================
) else (
    echo [NOTE] Inno Setup 6 compiler (ISCC.exe) was not found in Program Files.
    echo Standalone executable is ready at: dist\Omni\Omni.exe
    echo To build the setup wizard installer, install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
)

echo.
pause
