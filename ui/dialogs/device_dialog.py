"""Device settings dialog — pick video, audio I/O, resolution, fps."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox, QCheckBox,
    QPushButton, QFrame, QWidget,
)

from devices import find_video_devices, get_audio_device_cache, refresh_device_cache
from theme import C
from ui.dialogs.base import BaseDialog


class DeviceDialog(BaseDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent, "Device Settings")
        self.cfg = cfg
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr = QLabel("\u2699  DEVICE SETTINGS")
        hdr.setStyleSheet(
            f"color:{C['accent']};font-size:13pt;font-weight:bold;"
            f"letter-spacing:1.5px;background:transparent;"
        )
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # ── Devices form ──────────────────────────────────────────────────────
        grp = self._section("Capture Devices")
        gfl = QFormLayout(grp)
        gfl.setSpacing(14)
        gfl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gfl.setContentsMargins(12, 16, 12, 12)

        def _build_vid_combo():
            self.vid_combo.clear()
            for idx, name in find_video_devices():
                self.vid_combo.addItem(f"\U0001f4f9  [{idx}] {name}", idx)
                if idx == cfg.get("video_index", 0):
                    self.vid_combo.setCurrentIndex(self.vid_combo.count() - 1)
            if self.vid_combo.count() == 0:
                self.vid_combo.addItem("No video devices found", 0)

        self.vid_combo = QComboBox()
        self.vid_combo.setToolTip("Select your capture card or camera as the video source")
        _build_vid_combo()

        vid_row = QHBoxLayout()
        vid_row.setSpacing(6)
        vid_row.addWidget(self.vid_combo, 1)

        refresh_btn = QPushButton("\u21ba  Refresh Devices")
        refresh_btn.setFixedWidth(140)
        refresh_btn.setToolTip("Clear device cache and rescan for new capture cards / audio interfaces")

        def _refresh_all():
            refresh_device_cache()
            _build_vid_combo()
            _build_aud_combos()

        refresh_btn.clicked.connect(_refresh_all)
        vid_row.addWidget(refresh_btn)
        vw = QWidget()
        vw.setLayout(vid_row)
        lbl_vid = QLabel("Video device:")
        lbl_vid.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_vid, vw)

        vid_tip = QLabel("Select your capture card (usually 'USB Video' or 'USB Capture')")
        vid_tip.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gfl.addRow("", vid_tip)

        # Resolution + FPS linked dropdowns
        res_fps_row = QHBoxLayout()
        res_fps_row.setSpacing(10)
        self.res_combo = QComboBox()
        self.res_combo.setToolTip("Target capture resolution (device must support it)")
        for label, val in {
            "1920x1080 (1080p)": "1920x1080",
            "1280x720 (720p)":   "1280x720",
            "854x480 (480p)":    "854x480",
            "640x360 (360p)":    "640x360",
        }.items():
            self.res_combo.addItem(label, val)
            if val == cfg.get("resolution", "1920x1080"):
                self.res_combo.setCurrentIndex(self.res_combo.count() - 1)
        self.fps_combo = QComboBox()
        self.fps_combo.setToolTip("Target frame rate (device must support it)")
        for f in [60, 30, 24, 15]:
            self.fps_combo.addItem(f"{f} fps", f)
            if f == cfg.get("fps", 60):
                self.fps_combo.setCurrentIndex(self.fps_combo.count() - 1)
        res_fps_row.addWidget(self.res_combo, 2)
        res_fps_row.addWidget(self.fps_combo, 1)
        rfw = QWidget()
        rfw.setLayout(res_fps_row)
        lbl_res = QLabel("Resolution / FPS:")
        lbl_res.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_res, rfw)

        # Audio device combos — use cache, format "[index] name (Nch)"
        self.aud_combo = QComboBox()
        self.aud_combo.setToolTip(
            "Select the audio output of your capture card\n"
            "(also configurable in Audio Settings \u2192 Capture Card Audio)"
        )
        self.aud_out_combo = QComboBox()
        self.aud_out_combo.setToolTip(
            "Select your headphones or speakers for monitoring\n"
            "(also configurable in Audio Settings \u2192 Capture Card Audio)"
        )

        def _build_aud_combos():
            self.aud_combo.clear()
            self.aud_out_combo.clear()
            self.aud_out_combo.addItem("\U0001f508  System default", None)

            all_devs = get_audio_device_cache()

            saved_in  = cfg.get("audio_input_index", 3)
            saved_out = cfg.get("audio_output_index", None)

            for idx, d in all_devs:
                if d["max_input_channels"] > 0:
                    ch = int(d["max_input_channels"])
                    label = f"\U0001f50a  [{idx}] {d['name'][:46]} ({ch}ch)"
                    self.aud_combo.addItem(label, idx)
                    if idx == saved_in:
                        self.aud_combo.setCurrentIndex(self.aud_combo.count() - 1)
                if d["max_output_channels"] > 0:
                    label = f"\U0001f508  [{idx}] {d['name'][:50]}"
                    self.aud_out_combo.addItem(label, idx)
                    if idx == saved_out:
                        self.aud_out_combo.setCurrentIndex(self.aud_out_combo.count() - 1)

            if self.aud_combo.count() == 0:
                self.aud_combo.addItem("No audio input devices found", 0)

        _build_aud_combos()

        lbl_aud = QLabel("Audio input:")
        lbl_aud.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_aud, self.aud_combo)
        aud_in_tip = QLabel("Select the audio output of your capture card  (also in Audio Settings)")
        aud_in_tip.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gfl.addRow("", aud_in_tip)

        lbl_aud_out = QLabel("Audio output:")
        lbl_aud_out.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_aud_out, self.aud_out_combo)
        aud_out_tip = QLabel("Select your headphones or speakers for monitoring  (also in Audio Settings)")
        aud_out_tip.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gfl.addRow("", aud_out_tip)

        layout.addWidget(grp)

        # ── Behaviour ─────────────────────────────────────────────────────────
        grp_beh = self._section("Behaviour")
        gbeh = QVBoxLayout(grp_beh)
        gbeh.setSpacing(8)
        gbeh.setContentsMargins(12, 16, 12, 12)
        self.autostart_chk = QCheckBox("Auto-start stream on launch")
        self.autostart_chk.setChecked(cfg.get("auto_start", True))
        self.autostart_chk.setToolTip("Automatically start capturing when the app opens")
        gbeh.addWidget(self.autostart_chk)
        layout.addWidget(grp_beh)

        # Warning note
        note_bar = QFrame()
        note_bar.setStyleSheet(
            f"background:{C['warning']}18;border:1px solid {C['warning']}44;"
            f"border-radius:7px;padding:2px;"
        )
        note_layout = QHBoxLayout(note_bar)
        note_layout.setContentsMargins(10, 6, 10, 6)
        note_icon = QLabel("\u26a0")
        note_icon.setStyleSheet(f"color:{C['warning']};font-size:12pt;background:transparent;")
        note_text = QLabel("Changes take effect on the next stream start  (F5 to restart).")
        note_text.setStyleSheet(f"color:{C['warning']};font-size:9pt;background:transparent;")
        note_layout.addWidget(note_icon)
        note_layout.addWidget(note_text, 1)
        layout.addWidget(note_bar)

        layout.addLayout(self._buttons())

    def accept(self):
        self.cfg["video_index"]        = self.vid_combo.currentData()
        self.cfg["audio_input_index"]  = self.aud_combo.currentData()
        self.cfg["audio_output_index"] = self.aud_out_combo.currentData()
        self.cfg["auto_start"]         = self.autostart_chk.isChecked()
        if self.res_combo.currentData():
            self.cfg["resolution"] = self.res_combo.currentData()
        if self.fps_combo.currentData():
            self.cfg["fps"] = self.fps_combo.currentData()
        super().accept()
