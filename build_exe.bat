@echo off
REM Build BS_corr_plotter executable from this folder.
cd /d "%~dp0"

REM Optional override:
REM   set PYTHON_PATH=C:\Path\To\python.exe
if "%PYTHON_PATH%"=="" set PYTHON_PATH=python

echo Building BS_corr_plotter executable...
echo.

REM Check if PyInstaller is installed
"%PYTHON_PATH%" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    "%PYTHON_PATH%" -m pip install pyinstaller
)

REM Build using BS_corr_plotter.spec (icon uses .ico files from BS_corr_plotter\media)
"%PYTHON_PATH%" -m PyInstaller BS_corr_plotter.spec

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build complete! Executable is in this folder's dist directory.
pause
