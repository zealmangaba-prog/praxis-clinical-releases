#!/bin/bash
cd "$(dirname "$0")"

echo "======================================================"
echo "      CLINICAL REPORT GENERATOR (OFFLINE / POPIA)     "
echo "======================================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 was not detected on this Mac."
    echo "Please install Python from https://www.python.org or macOS Command Line Tools."
    read -p "Press [Enter] to exit..."
    exit 1
fi

# Auto-setup: Create virtual environment if missing
if [ ! -d "venv" ]; then
    echo ""
    echo "[First-Time Setup] Creating secure local environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "[First-Time Setup] Installing required clinical libraries (ReportLab, Streamlit, etc.)..."
    pip install --quiet --upgrade pip
    if [ -f "requirements.txt" ]; then
        pip install --quiet -r requirements.txt
    fi
    echo "[First-Time Setup] Setup complete!"
    echo ""
else
    source venv/bin/activate
fi

echo "Starting local clinical report engine..."
echo "Your browser will open automatically at http://localhost:8501"
echo ""
echo "Press Ctrl+C in this window at any time to close the app."
echo "======================================================"

# Launch Streamlit silently into default browser
streamlit run app.py --server.headless=false --browser.gatherUsageStats=false
