@echo off
title Clinical Report Generator - First Time Setup
cd /d "%~dp0"

echo ====================================================
echo  Clinical Report Generator: First-Time Setup
echo ====================================================
echo.

:: 1. Verify if Python is installed and accessible in PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on your system!
    echo.
    echo Please download and install Python from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Make sure to check the box:
    echo "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/2] Upgrading Python package manager (pip)...
python -m pip install --upgrade pip

echo.
echo [2/2] Installing required clinical and PDF libraries...
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed. Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo  Setup Complete! You can now double-click 'run_app.bat'
echo ====================================================
echo.
pause