"""Shared base class for all settings dialogs."""
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QGroupBox, QFrame, QHBoxLayout, QPushButton,
    QGraphicsDropShadowEffect,
)

from theme import C, STYLESHEET


class BaseDialog(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(460)
        # Drop shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 140))
        self.setGraphicsEffect(shadow)

    def _section(self, label):
        return QGroupBox(label)

    def _divider(self):
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setStyleSheet(
            f"color:{C['border2']};max-height:1px;"
            f"margin:2px 0 6px 0;background:{C['border2']};"
        )
        return f

    def _buttons(self, ok_text="Save"):
        bf = QHBoxLayout()
        bf.addStretch()
        bf.setSpacing(10)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        cancel.setToolTip("Discard changes and close")
        cancel.setMinimumWidth(90)
        ok = QPushButton(ok_text)
        ok.setObjectName("accent")
        ok.clicked.connect(self.accept)
        ok.setToolTip("Apply and close")
        ok.setMinimumWidth(90)
        bf.addWidget(cancel)
        bf.addWidget(ok)
        return bf
