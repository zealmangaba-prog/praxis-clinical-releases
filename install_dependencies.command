#!/bin/bash
cd "$(dirname "$0")"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo ""
echo "===================================================="
echo " Setup Complete! You can now run 'run_app.command'"
echo "===================================================="
read -p "Press Enter to exit..."