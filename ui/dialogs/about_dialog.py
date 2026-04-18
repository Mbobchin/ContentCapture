"""About box — shows app version, CUDA status, RAM, config path.

Implemented as a function (not a QDialog subclass) since the original used
QMessageBox.information.  Kept here so the main window does not need to know
the message text.
"""
from PySide6.QtWidgets import QMessageBox

from config import get_available_ram_gb
from constants import APP_NAME, APP_VERSION, APP_TAGLINE, CONFIG_FILE
from cuda_support import CUDA_AVAILABLE


def show_about(parent):
    ram = get_available_ram_gb()
    QMessageBox.information(
        parent, "About",
        f"{APP_NAME}  v{APP_VERSION}\n{APP_TAGLINE}\n\n"
        f"CUDA:  {'yes' if CUDA_AVAILABLE else 'no'}\n"
        f"RAM:   {ram:.1f}GB detected\n\n"
        f"Config: {CONFIG_FILE}"
    )
