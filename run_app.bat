@echo off
cd /d "%~dp0"
set PYTHONPATH=.;%PYTHONPATH%

echo ==========================================================
echo     Starting Clinical Treatment Plan ^& Report Generator   
echo ==========================================================
echo.

:: 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on your system.
    echo Please install Python 3 from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 2. Check Ollama
echo [1/4] Verifying Local AI Copilot Engine (Ollama)...
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Ollama is not installed. AI Copilot will be disabled.
    echo Download from: https://ollama.com/download
) else (
    tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul
    if %errorlevel% neq 0 (
        echo Starting Ollama background service...
        start /b ollama serve >nul 2>&1
        timeout /t 2 >nul
    )
    echo [OK] Ollama engine detected and running.
)

:: 3. Setup Virtual Environment
set FIRST_RUN=0
if not exist "venv" (
    echo [2/4] Creating virtual environment (first-time setup)...
    python -m venv venv
    set FIRST_RUN=1
)

call venv\Scripts\activate.bat

if %FIRST_RUN%==1 (
    echo [3/4] Installing required packages...
    python -m pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
) else (
    echo [3/4] Environment ready.
)

:: 4. Launch Streamlit
echo [4/4] Launching interface in default browser...
python -m streamlit run app.py --server.port=8501 --server.headless=false --browser.serverAddress=localhost
pause