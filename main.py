import sys
import os
import webbrowser
from pathlib import Path

# Ensure bundled C-libraries and modules are in sys.path for child threads
if getattr(sys, "frozen", False):
    bundle_dir = sys._MEIPASS
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
else:
    bundle_dir = str(Path(__file__).resolve().parent)

import streamlit.web.cli as stcli


def run():
    app_path = os.path.join(bundle_dir, "app.py")

    # Set Streamlit CLI arguments directly
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=false",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]

    # Open the browser automatically
    webbrowser.open("http://localhost:8501")

    # Execute the CLI runner cleanly
    sys.exit(stcli.main())


if __name__ == "__main__":
    run()