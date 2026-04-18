"""ContentCapture v2 — application entry point.

Creates the QApplication, pre-populates the audio device cache, and shows
the main window.  Video device cache is populated lazily on first
DeviceDialog open — opening the capture card here and immediately
releasing it can cause MSMF drivers to enter a brief exclusive-access
lockout that prevents VideoThread from opening the same device seconds
later.
"""
import sys

from PySide6.QtWidgets import QApplication

from constants import APP_NAME, APP_VERSION
from devices import populate_audio_cache
from ui.main_window import MainWindow


def main():
    # psutil is optional at runtime — system stats just degrade gracefully
    # if it can't be imported.
    try:
        import psutil  # noqa: F401
    except ImportError:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    populate_audio_cache()

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
