"""Coloured pill badge widget — used in the toolbar to show live state."""
from PySide6.QtWidgets import QLabel

from theme import C


class StatusPill(QLabel):
    """Coloured pill badge for the topbar — shows live state at a glance."""
    def __init__(self, text="", color=None, parent=None):
        super().__init__(text, parent)
        self._color = color or C["subtext"]
        self._refresh()

    def _refresh(self):
        self.setStyleSheet(
            f"QLabel{{"
            f"  background:{self._color}22;"
            f"  color:{self._color};"
            f"  border:1px solid {self._color}55;"
            f"  border-radius:10px;"
            f"  padding:2px 10px;"
            f"  font-size:8pt;"
            f"  font-weight:bold;"
            f"  letter-spacing:0.4px;"
            f"}}"
        )

    def set_state(self, text, color):
        self._color = color
        self.setText(text)
        self._refresh()
