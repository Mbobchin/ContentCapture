"""Recording settings dialog — paths, format, clip buffer, audio track, preview FPS."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QSlider, QSpinBox,
    QCheckBox, QPushButton, QLineEdit, QFileDialog, QRadioButton, QButtonGroup,
    QFrame, QWidget,
)

from theme import C
from ui.dialogs.base import BaseDialog


class RecordingDialog(BaseDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent, "Recording Settings")
        self.cfg = cfg
        self.setMinimumWidth(540)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr = QLabel("\u23fa  RECORDING SETTINGS")
        hdr.setStyleSheet(
            f"color:{C['accent']};font-size:13pt;font-weight:bold;"
            f"letter-spacing:1.5px;background:transparent;"
        )
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # ── Output Paths ──────────────────────────────────────────────────────
        grp = self._section("Output Paths")
        gfl = QFormLayout(grp)
        gfl.setSpacing(12)
        gfl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gfl.setContentsMargins(12, 16, 12, 12)

        for attr, label, key, tip in [
            ("rec_path",       "Recordings",  "recording_path",  "Folder where recordings are saved"),
            ("scr_path",       "Screenshots", "screenshot_path", "Folder where screenshots are saved"),
            ("clip_path_edit", "Clips",       "clip_path",       "Folder where instant clips (F9) are saved"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(6)
            le = QLineEdit(cfg.get(key, ""))
            le.setToolTip(tip)
            br = QPushButton("\U0001f4c2  Browse")
            br.setFixedWidth(100)
            br.setToolTip(f"Choose {label.lower()} folder")

            def _browse(checked, le=le, lbl=label):
                d = QFileDialog.getExistingDirectory(self, f"Choose {lbl} Folder", le.text())
                if d:
                    le.setText(d)

            br.clicked.connect(_browse)
            row.addWidget(le, 1)
            row.addWidget(br)
            w = QWidget()
            w.setLayout(row)
            lbl = QLabel(label + ":")
            lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
            gfl.addRow(lbl, w)
            setattr(self, attr, le)

        layout.addWidget(grp)

        # ── Screenshot Format ─────────────────────────────────────────────────
        grp_sfmt = self._section("Screenshot Format")
        gsfmt = QVBoxLayout(grp_sfmt)
        gsfmt.setSpacing(10)
        gsfmt.setContentsMargins(12, 16, 12, 12)
        sfmt_row = QHBoxLayout()
        sfmt_row.setSpacing(10)
        self.sfmt_bg = QButtonGroup()
        cur_sfmt = cfg.get("screenshot_format", "png")
        for bid, (fmt, label_f) in enumerate([("png", "PNG"), ("jpeg", "JPEG"), ("webp", "WebP")]):
            rb = QRadioButton(label_f)
            rb.setChecked(fmt == cur_sfmt)
            rb.setStyleSheet("font-size:10pt;background:transparent;")
            self.sfmt_bg.addButton(rb, bid)
            sfmt_row.addWidget(rb)
        sfmt_row.addStretch()
        gsfmt.addLayout(sfmt_row)
        jpeg_row = QHBoxLayout()
        jpeg_row.setSpacing(10)
        jpeg_qlbl = QLabel("JPEG quality:")
        jpeg_qlbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        self.jpeg_quality_spin = QSpinBox()
        self.jpeg_quality_spin.setRange(1, 100)
        self.jpeg_quality_spin.setValue(cfg.get("screenshot_jpeg_quality", 92))
        self.jpeg_quality_spin.setFixedWidth(80)
        self.jpeg_quality_spin.setSuffix("%")
        self.jpeg_quality_spin.setToolTip("JPEG compression quality (higher = larger file, better quality)")
        jpeg_row.addWidget(jpeg_qlbl)
        jpeg_row.addWidget(self.jpeg_quality_spin)
        jpeg_row.addStretch()
        self._jpeg_qual_w = QWidget()
        self._jpeg_qual_w.setLayout(jpeg_row)
        self._jpeg_qual_w.setVisible(cur_sfmt == "jpeg")
        gsfmt.addWidget(self._jpeg_qual_w)
        self.sfmt_bg.idClicked.connect(lambda bid: self._jpeg_qual_w.setVisible(bid == 1))
        layout.addWidget(grp_sfmt)

        # ── Format & Buffer ───────────────────────────────────────────────────
        grp2 = self._section("Format & Clip Buffer")
        gl2 = QVBoxLayout(grp2)
        gl2.setSpacing(12)
        gl2.setContentsMargins(12, 16, 12, 12)

        # Format cards
        fmt_lbl = QLabel("Container format:")
        fmt_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        gl2.addWidget(fmt_lbl)
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(10)
        self.fmt_bg = QButtonGroup()
        for fmt, icon, title, desc, tip in [
            ("mp4", "\U0001f3ac", "MP4", "H.264 / best compat",  "Standard MP4 — plays everywhere"),
            ("mkv", "\U0001f4e6", "MKV", "H.264 / recoverable",  "Matroska — safe if interrupted"),
        ]:
            border_color = C["accent"] if fmt == cfg.get("recording_format", "mp4") else C["border2"]
            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:{C['panel3']};border:1px solid {border_color};"
                f"border-radius:8px;padding:4px;}}"
                f"QFrame:hover{{border-color:{C['accent2']};}}"
            )
            cl = QVBoxLayout(card)
            cl.setSpacing(3)
            cl.setContentsMargins(12, 10, 12, 10)
            rb = QRadioButton(f"{icon} {title}")
            rb.setChecked(fmt == cfg.get("recording_format", "mp4"))
            rb.setStyleSheet("font-weight:bold;font-size:10pt;background:transparent;")
            rb.setToolTip(tip)
            rb.toggled.connect(lambda c, f=fmt: cfg.__setitem__("recording_format", f) if c else None)
            desc_l = QLabel(desc)
            desc_l.setStyleSheet(
                f"color:{C['subtext']};font-size:8pt;background:transparent;padding-left:4px;"
            )
            self.fmt_bg.addButton(rb)
            cl.addWidget(rb)
            cl.addWidget(desc_l)
            fmt_row.addWidget(card)
        fmt_row.addStretch()
        gl2.addLayout(fmt_row)

        gl2.addWidget(self._divider())

        # ── Enable Instant Clip Buffer checkbox ───────────────────────────────
        self.clip_buf_enabled_chk = QCheckBox("Enable Instant Clip Buffer")
        self.clip_buf_enabled_chk.setChecked(cfg.get("clip_buffer_enabled", False))
        self.clip_buf_enabled_chk.setStyleSheet("font-weight:bold;font-size:10pt;")
        self.clip_buf_enabled_chk.setToolTip(
            "Keeps recent footage in memory for instant clip saving (F9).\n"
            "Disable to save RAM — JPEG compression is used to reduce memory usage."
        )
        gl2.addWidget(self.clip_buf_enabled_chk)

        clip_note = QLabel(
            "Keeps recent footage in RAM for instant clip saving.  "
            "Uses JPEG compression — disable to save RAM."
        )
        clip_note.setWordWrap(True)
        clip_note.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gl2.addWidget(clip_note)

        # Container for clip buffer sub-controls (greys out when disabled)
        clip_controls = QWidget()
        clip_controls_layout = QVBoxLayout(clip_controls)
        clip_controls_layout.setContentsMargins(0, 4, 0, 0)
        clip_controls_layout.setSpacing(10)

        # Clip buffer duration + RAM estimate
        clip_row = QHBoxLayout()
        clip_row.setSpacing(10)
        clip_label = QLabel("Buffer duration:")
        clip_label.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        clip_label.setFixedWidth(110)
        self.clip_spin = QSpinBox()
        self.clip_spin.setRange(5, 120)
        self.clip_spin.setSuffix(" seconds")
        self.clip_spin.setValue(cfg.get("clip_duration", 15))
        self.clip_spin.setFixedWidth(120)
        self.clip_spin.setToolTip(
            "Seconds of footage kept in rolling buffer — press F9 to save as instant clip"
        )
        self._clip_ram_lbl = QLabel()
        self._clip_ram_lbl.setStyleSheet(f"color:{C['accent']};font-size:9pt;background:transparent;")
        clip_row.addWidget(clip_label)
        clip_row.addWidget(self.clip_spin)
        clip_row.addWidget(self._clip_ram_lbl)
        clip_row.addStretch()
        clip_controls_layout.addLayout(clip_row)

        # JPEG quality slider
        jpeg_q_row = QHBoxLayout()
        jpeg_q_row.setSpacing(10)
        jpeg_q_lbl = QLabel("Clip Buffer Quality:")
        jpeg_q_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        jpeg_q_lbl.setFixedWidth(130)
        self.clip_jpeg_slider = QSlider(Qt.Horizontal)
        self.clip_jpeg_slider.setRange(50, 100)
        self.clip_jpeg_slider.setValue(cfg.get("clip_buffer_jpeg_quality", 85))
        self.clip_jpeg_slider.setToolTip(
            "JPEG quality for clip buffer frames (50-100).\n"
            "85 is visually lossless.  Lower = smaller RAM, slightly lower quality."
        )
        self.clip_jpeg_spin = QSpinBox()
        self.clip_jpeg_spin.setRange(50, 100)
        self.clip_jpeg_spin.setSuffix("%")
        self.clip_jpeg_spin.setFixedWidth(76)
        self.clip_jpeg_spin.setValue(cfg.get("clip_buffer_jpeg_quality", 85))
        self.clip_jpeg_spin.setToolTip("JPEG quality (85 = visually lossless, lower = less RAM)")

        def _on_clip_jpeg_slider(v):
            self.clip_jpeg_spin.blockSignals(True)
            self.clip_jpeg_spin.setValue(v)
            self.clip_jpeg_spin.blockSignals(False)
            self._update_clip_ram_estimate()

        def _on_clip_jpeg_spin(v):
            self.clip_jpeg_slider.blockSignals(True)
            self.clip_jpeg_slider.setValue(v)
            self.clip_jpeg_slider.blockSignals(False)
            self._update_clip_ram_estimate()

        self.clip_jpeg_slider.valueChanged.connect(_on_clip_jpeg_slider)
        self.clip_jpeg_spin.valueChanged.connect(_on_clip_jpeg_spin)

        jpeg_q_row.addWidget(jpeg_q_lbl)
        jpeg_q_row.addWidget(self.clip_jpeg_slider, 1)
        jpeg_q_row.addWidget(self.clip_jpeg_spin)
        clip_controls_layout.addLayout(jpeg_q_row)

        self.clip_spin.valueChanged.connect(lambda _: self._update_clip_ram_estimate())
        gl2.addWidget(clip_controls)

        def _on_clip_buf_toggled(checked):
            clip_controls.setEnabled(checked)
            cfg["clip_buffer_enabled"] = checked

        self.clip_buf_enabled_chk.toggled.connect(_on_clip_buf_toggled)
        clip_controls.setEnabled(cfg.get("clip_buffer_enabled", False))

        self._update_clip_ram_estimate()

        layout.addWidget(grp2)

        # ── Preview FPS Cap ───────────────────────────────────────────────────
        grp_prev = self._section("Preview Performance")
        gp = QFormLayout(grp_prev)
        gp.setSpacing(12)
        gp.setContentsMargins(12, 16, 12, 12)
        gp.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        prev_fps_row = QHBoxLayout()
        prev_fps_row.setSpacing(10)
        self.preview_fps_spin = QSpinBox()
        self.preview_fps_spin.setRange(10, 60)
        self.preview_fps_spin.setValue(cfg.get("preview_fps_cap", 30))
        self.preview_fps_spin.setSuffix(" fps")
        self.preview_fps_spin.setFixedWidth(90)
        self.preview_fps_spin.setToolTip(
            "Maximum repaint rate for the preview window.\n"
            "30fps is smooth and uses half the Qt rendering overhead of 60fps."
        )
        prev_fps_row.addWidget(self.preview_fps_spin)
        prev_fps_row.addStretch()
        prev_fps_w = QWidget()
        prev_fps_w.setLayout(prev_fps_row)
        lbl_prev = QLabel("Preview FPS cap:")
        lbl_prev.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gp.addRow(lbl_prev, prev_fps_w)
        prev_hint = QLabel("30fps preview is smooth and halves Qt repaint overhead vs 60fps.")
        prev_hint.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gp.addRow("", prev_hint)
        layout.addWidget(grp_prev)

        # ── Audio Track ───────────────────────────────────────────────────────
        grp_aud = self._section("Audio Track")
        gaud = QVBoxLayout(grp_aud)
        gaud.setSpacing(10)
        gaud.setContentsMargins(12, 16, 12, 12)

        self.aud_include_chk = QCheckBox("Include audio in recordings")
        self.aud_include_chk.setChecked(cfg.get("recording_include_audio", True))
        self.aud_include_chk.setToolTip(
            "Mux the captured audio stream into the output file (built-in encoder)"
        )
        gaud.addWidget(self.aud_include_chk)

        codec_row = QHBoxLayout()
        codec_row.setSpacing(14)
        codec_lbl = QLabel("Codec:")
        codec_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        codec_row.addWidget(codec_lbl)
        self._aud_codec_bg = QButtonGroup()
        cur_codec = cfg.get("recording_audio_codec", "aac")
        self._aud_rb_aac = QRadioButton("AAC")
        self._aud_rb_mp3 = QRadioButton("MP3")
        self._aud_rb_pcm = QRadioButton("PCM (lossless, large)")
        for i, (rb, val) in enumerate([
            (self._aud_rb_aac, "aac"),
            (self._aud_rb_mp3, "mp3"),
            (self._aud_rb_pcm, "pcm"),
        ]):
            rb.setChecked(val == cur_codec)
            rb.setStyleSheet("font-size:10pt;background:transparent;")
            self._aud_codec_bg.addButton(rb, i)
            codec_row.addWidget(rb)
        codec_row.addStretch()
        gaud.addLayout(codec_row)

        bitrate_row = QHBoxLayout()
        bitrate_row.setSpacing(10)
        bitrate_lbl = QLabel("Bitrate:")
        bitrate_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        self.aud_bitrate_spin = QSpinBox()
        self.aud_bitrate_spin.setRange(64, 320)
        self.aud_bitrate_spin.setSingleStep(64)
        self.aud_bitrate_spin.setSuffix(" kbps")
        self.aud_bitrate_spin.setFixedWidth(110)
        cur_br = cfg.get("recording_audio_bitrate", 320)
        for snap in [64, 128, 192, 320]:
            if cur_br <= snap:
                cur_br = snap
                break
        self.aud_bitrate_spin.setValue(cur_br)
        self.aud_bitrate_spin.setToolTip("Audio bitrate for AAC/MP3 (ignored for PCM)")
        bitrate_row.addWidget(bitrate_lbl)
        bitrate_row.addWidget(self.aud_bitrate_spin)
        bitrate_row.addStretch()
        self._bitrate_widget = QWidget()
        self._bitrate_widget.setLayout(bitrate_row)
        gaud.addWidget(self._bitrate_widget)

        def _update_aud_controls():
            enabled = self.aud_include_chk.isChecked()
            self._aud_rb_aac.setEnabled(enabled)
            self._aud_rb_mp3.setEnabled(enabled)
            self._aud_rb_pcm.setEnabled(enabled)
            is_pcm = self._aud_rb_pcm.isChecked()
            self.aud_bitrate_spin.setEnabled(enabled and not is_pcm)

        self.aud_include_chk.stateChanged.connect(lambda _: _update_aud_controls())
        self._aud_codec_bg.idClicked.connect(lambda _: _update_aud_controls())
        _update_aud_controls()

        layout.addWidget(grp_aud)
        layout.addLayout(self._buttons())

    def _update_clip_ram_estimate(self):
        """Show approximate RAM usage for the clip buffer at current settings."""
        dur     = self.clip_spin.value()
        quality = self.clip_jpeg_spin.value()
        fps     = self.cfg.get("fps", 60)
        raw_mb  = 1920 * 1080 * 3 / (1024 * 1024)
        quality_factor = quality / 100.0 * 0.05
        est_mb  = int(fps * dur * raw_mb * quality_factor)
        if est_mb < 1:
            est_mb = 1
        self._clip_ram_lbl.setText(f"\u2248 {est_mb} MB RAM")
        tip = (
            f"At {fps}fps \u00d7 {dur}s \u00d7 JPEG {quality}% quality \u2248 {est_mb}MB\n"
            f"(raw uncompressed would be {int(fps * dur * raw_mb / 1024)}GB)"
        )
        self._clip_ram_lbl.setToolTip(tip)

    def accept(self):
        self.cfg["recording_path"]   = self.rec_path.text()
        self.cfg["screenshot_path"]  = self.scr_path.text()
        self.cfg["clip_path"]        = self.clip_path_edit.text()
        self.cfg["clip_duration"]    = self.clip_spin.value()
        fmt_map = {0: "png", 1: "jpeg", 2: "webp"}
        self.cfg["screenshot_format"]        = fmt_map.get(self.sfmt_bg.checkedId(), "png")
        self.cfg["screenshot_jpeg_quality"]  = self.jpeg_quality_spin.value()
        self.cfg["clip_buffer_enabled"]      = self.clip_buf_enabled_chk.isChecked()
        self.cfg["clip_buffer_jpeg_quality"] = self.clip_jpeg_spin.value()
        self.cfg["preview_fps_cap"]          = self.preview_fps_spin.value()
        self.cfg["recording_include_audio"]  = self.aud_include_chk.isChecked()
        codec_map = {0: "aac", 1: "mp3", 2: "pcm"}
        self.cfg["recording_audio_codec"]    = codec_map.get(self._aud_codec_bg.checkedId(), "aac")
        self.cfg["recording_audio_bitrate"]  = self.aud_bitrate_spin.value()
        super().accept()
