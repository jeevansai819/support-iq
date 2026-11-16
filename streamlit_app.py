"""
Entry point for Streamlit Community Cloud.
Delegates execution to frontend/app.py.
"""
import sys
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app_path = ROOT / "frontend" / "app.py"
runpy.run_path(str(app_path), run_name="__main__")
