cat << 'EOF' > "Start_Clinical_Generator.bat"
@echo off
title Clinical Report Generator (Offline / POPIA)

echo ======================================================
echo       CLINICAL REPORT GENERATOR (OFFLINE / POPIA)     
echo ======================================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not detected on this system.
    echo Please install Python 3.10+ from https://www.python.org/
    echo NOTE: Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

:: Auto-setup: Create virtual environment if missing
if not exist "venv" (
    echo.
    echo [First-Time Setup] Creating secure local environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    
    echo [First-Time Setup] Installing required clinical libraries...
    python -m pip install --quiet --upgrade pip
    if exist "requirements.txt" (
        pip install --quiet -r requirements.txt
    )
    echo [First-Time Setup] Setup complete!
    echo.
) else (
    call venv\Scripts\activate.bat
)

echo Starting local clinical report engine...
echo Your browser will open automatically at http://localhost:8501
echo.
echo Press Ctrl+C in this window at any time to close the app.
echo ======================================================

:: Launch Streamlit
streamlit run app.py --server.headless=false --browser.gatherUsageStats=false
pause
EOF