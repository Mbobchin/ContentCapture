"""Upscale settings dialog — choose CPU vs CUDA Lanczos resize."""
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QRadioButton, QButtonGroup, QFrame,
)

from cuda_support import CUDA_AVAILABLE
from theme import C
from ui.dialogs.base import BaseDialog


class UpscaleDialog(BaseDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent, "Upscaling Settings")
        self.mode = cfg.get("upscale_mode", "none")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr = QLabel("\U0001f50d  GPU UPSCALING")
        hdr.setStyleSheet(
            f"color:{C['accent']};font-size:13pt;font-weight:bold;"
            f"letter-spacing:1.5px;background:transparent;"
        )
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        grp = self._section("Upscale Mode")
        gl = QVBoxLayout(grp)
        gl.setSpacing(10)
        gl.setContentsMargins(12, 16, 12, 12)
        self.bg = QButtonGroup()

        cuda_avail_text = "(\u2713 Available)" if CUDA_AVAILABLE else "(\u2717 Not available)"
        card_defs = [
            ("none", "\u25a0  Off  \u2014  No upscaling",
             "Pass frames through at captured resolution.\n"
             "Lowest CPU/GPU overhead — best for 1080p60 direct capture.", True),
            ("cuda", f"\u26a1  CUDA Lanczos  \u2014  GPU resize  {cuda_avail_text}",
             "Use NVIDIA CUDA to upscale via Lanczos4 interpolation.\n"
             "Best quality for 720p\u21921080p or 1080p\u21921440p.",
             CUDA_AVAILABLE),
        ]
        for val, label, desc, avail in card_defs:
            card = QFrame()
            card.setObjectName("upscale_card")
            border_color = C["accent"] if val == self.mode else C["border2"]
            card.setStyleSheet(
                f"QFrame#upscale_card{{"
                f"  background:{C['card']};"
                f"  border:1px solid {border_color};"
                f"  border-radius:10px;"
                f"  padding:4px;"
                f"}}"
                f"QFrame#upscale_card:hover{{"
                f"  border-color:{C['accent2']};"
                f"}}"
            )
            cl = QVBoxLayout(card)
            cl.setSpacing(4)
            cl.setContentsMargins(12, 10, 12, 10)
            rb = QRadioButton(label)
            rb.setChecked(val == self.mode)
            rb.setEnabled(avail)
            rb.setToolTip(desc)
            text_color = C["text"] if avail else C["subtext"]
            rb.setStyleSheet(
                f"font-weight:bold;font-size:10pt;color:{text_color};background:transparent;"
            )
            desc_lbl = QLabel(desc.replace(".", "\n.", 1) if "." in desc else desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color:{C['text2']};font-size:9pt;background:transparent;padding-left:26px;"
            )

            def _on_rb(checked, v=val, c=card):
                if checked:
                    setattr(self, "mode", v)
                    for ch in grp.findChildren(QFrame):
                        ch.setStyleSheet(ch.styleSheet())

            rb.toggled.connect(_on_rb)
            self.bg.addButton(rb)
            cl.addWidget(rb)
            cl.addWidget(desc_lbl)
            gl.addWidget(card)

        layout.addWidget(grp)
        layout.addLayout(self._buttons())
