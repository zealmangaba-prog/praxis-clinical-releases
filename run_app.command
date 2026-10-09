#!/bin/bash

# Navigate to the folder where this script lives
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Clear terminal screen for a clean interface
clear
echo "========================================================"
echo "          Starting Praxis Clinical Suite...             "
echo "========================================================"
echo ""
echo " Initializing local clinical environment..."

# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo " Error: Virtual environment not found. Please contact support."
    read -p "Press Enter to exit..."
    exit 1
fi

echo " Launching application in your browser..."
echo " Keep this window open while using Praxis Clinical."
echo " Press Ctrl + C to close the application when finished."
echo "--------------------------------------------------------"

# Launch Streamlit with seamless production flags
streamlit run app.py \
    --server.headless true \
    --server.port 8501 \
    --browser.gatherUsageStats false \
    --theme.base "light" \
    --theme.primaryColor "#2563EB" \
    --theme.secondaryBackgroundColor "#F8FAFC"