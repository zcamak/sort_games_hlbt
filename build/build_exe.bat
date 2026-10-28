@echo off
setlocal

:: Get root directory
cd /d "%~dp0\.."

set "PYTHON_EXE=.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found at %PYTHON_EXE%
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

echo ==================================================
echo Building GameSorter.exe into app/ using PyInstaller
echo ==================================================

if not exist "app" mkdir app

"%PYTHON_EXE%" -m PyInstaller build\GameSorter.spec --distpath app --workpath build\temp --noconfirm

if exist "build\temp" rmdir /s /q "build\temp"

if exist "app\GameSorter.exe" (
    echo.
    echo [SUCCESS] Standalone executable created at: app\GameSorter.exe
) else (
    echo.
    echo [ERROR] Build failed.
)

pause
