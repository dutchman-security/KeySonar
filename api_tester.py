"""
🧭 Dutchman KeySonar - Backward Compatibility Alias
🛡️ Developed By Dutchman Security

This file is maintained for backward compatibility with previous scripts.
The primary application entrypoint is keysonar.py.

Usage:
    streamlit run keysonar.py
"""

from pathlib import Path
import runpy

if __name__ == "__main__" or "__streamlitmagic__" in globals():
    target_app = Path(__file__).parent / "keysonar.py"
    runpy.run_path(str(target_app), run_name="__main__")
