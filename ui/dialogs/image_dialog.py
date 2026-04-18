"""Image / colour adjustment dialog — brightness, contrast, saturation."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QSlider,
    QDoubleSpinBox, QPushButton, QWidget,
)

from config import save_config
from theme import C
from ui.dialogs.base import BaseDialog


class ImageDialog(BaseDialog):
    def __init__(self, parent, vthread, cfg=None):
        super().__init__(parent, "Image & Filters")
        self.vthread = vthread
        self.cfg = cfg
        self.setMinimumWidth(520)
        self.vals = {
            "brightness": cfg.get("brightness", 1.0) if cfg else 1.0,
            "contrast":   cfg.get("contrast",   1.0) if cfg else 1.0,
            "saturation": cfg.get("saturation", 1.0) if cfg else 1.0,
        }
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr = QLabel("\u25c8  IMAGE & FILTERS")
        hdr.setStyleSheet(
            f"color:{C['accent']};font-size:13pt;font-weight:bold;"
            f"letter-spacing:1.5px;background:transparent;"
        )
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        grp = self._section("Colour Adjustments")
        gl = QFormLayout(grp)
        gl.setSpacing(14)
        gl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gl.setContentsMargins(12, 16, 12, 12)
        self.sliders = {}
        self.spins = {}

        slider_defs = [
            ("brightness", "\u2600  Brightness", 20, 200, "Boost or reduce overall luminance (100 = neutral)"),
            ("contrast",   "\u25d1  Contrast",   20, 200, "Expand or compress the tonal range (100 = neutral)"),
            ("saturation", "\u2b21  Saturation",  0, 200, "Increase or reduce colour intensity (100 = neutral)"),
        ]
        for key, label, lo, hi, tip in slider_defs:
            row = QHBoxLayout()
            row.setSpacing(10)
            init_val = self.vals.get(key, 1.0)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(int(init_val * 100))
            sl.setToolTip(tip)
            spin = QDoubleSpinBox()
            spin.setRange(lo / 100.0, hi / 100.0)
            spin.setDecimals(2)
            spin.setSingleStep(0.05)
            spin.setValue(init_val)
            spin.setFixedWidth(80)
            spin.setToolTip("Type a value directly (1.0 = neutral)")

            def _on_slider(v, k=key, sp=spin):
                sp.blockSignals(True)
                sp.setValue(v / 100.0)
                sp.blockSignals(False)
                self.vals[k] = v / 100.0
                self._apply()

            def _on_spin(v, k=key, s=sl):
                s.blockSignals(True)
                s.setValue(int(v * 100))
                s.blockSignals(False)
                self.vals[k] = v
                self._apply()

            sl.valueChanged.connect(_on_slider)
            spin.valueChanged.connect(_on_spin)
            row.addWidget(sl, 1)
            row.addWidget(spin)
            container = QWidget()
            container.setLayout(row)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
            gl.addRow(lbl, container)
            self.sliders[key] = sl
            self.spins[key] = spin

        layout.addWidget(grp)

        reset_row = QHBoxLayout()
        reset_row.addStretch()
        reset = QPushButton("\u21ba  Reset All to Neutral")
        reset.setToolTip("Set brightness, contrast, and saturation back to 1.0 (no effect)")
        reset.clicked.connect(self._reset)
        reset_row.addWidget(reset)
        layout.addLayout(reset_row)
        layout.addLayout(self._buttons("Close"))

    def _apply(self):
        if self.vthread:
            self.vthread.set_image(
                self.vals["brightness"], self.vals["contrast"], self.vals["saturation"]
            )
        if self.cfg:
            self.cfg["brightness"] = self.vals["brightness"]
            self.cfg["contrast"]   = self.vals["contrast"]
            self.cfg["saturation"] = self.vals["saturation"]
            save_config(self.cfg)

    def _reset(self):
        for key in self.sliders:
            self.sliders[key].setValue(100)

    def accept(self):
        self.close()
