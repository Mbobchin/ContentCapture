"""Legacy entry-point shim — the app is now the multi-file package next door.

Kept so existing launchers (ContentCapture.bat, desktop shortcuts, the
PyInstaller spec, etc.) continue to work after the v2.4.0 refactor.
The real entry point is `main.py` in the same directory.
"""
import os
import sys

# Make sure this directory is on sys.path so the sibling package modules
# (constants, config, ui/, core/, ...) import correctly even when this
# file is launched by absolute path.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from main import main  # noqa: E402

if __name__ == "__main__":
    main()
