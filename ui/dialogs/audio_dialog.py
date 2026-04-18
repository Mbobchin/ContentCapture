"""Audio settings dialog — capture-card audio, sample rate, AV sync, microphone."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QSlider, QSpinBox,
    QComboBox, QCheckBox, QPushButton, QWidget,
)

from devices import get_audio_device_cache
from theme import C
from ui.dialogs.base import BaseDialog


class AudioDialog(BaseDialog):
    def __init__(self, parent, cfg, audio, mic=None):
        super().__init__(parent, "Audio Settings")
        self.cfg = cfg
        self._audio_engine = audio
        self._mic = mic
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QLabel("\U0001f50a  AUDIO SETTINGS")
        hdr.setStyleSheet(
            f"color:{C['accent']};font-size:13pt;font-weight:bold;"
            f"letter-spacing:1.5px;background:transparent;"
        )
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # ── Capture Card Audio group ─────────────────────────────────────────
        grp_cc = self._section("Capture Card Audio")
        gcc = QVBoxLayout(grp_cc)
        gcc.setSpacing(12)
        gcc.setContentsMargins(12, 16, 12, 12)

        cc_note_top = QLabel("Stream restart required after changing devices.")
        cc_note_top.setStyleSheet(f"color:{C['warning']};font-size:9pt;background:transparent;")
        gcc.addWidget(cc_note_top)

        gcc_form = QFormLayout()
        gcc_form.setSpacing(10)
        gcc_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        _all_audio = get_audio_device_cache()

        # Audio Input combo (capture card input)
        self._cc_in_combo = QComboBox()
        self._cc_in_combo.setToolTip(
            "Select the audio output of your capture card device.\n"
            "This is what you HEAR from the game/console."
        )
        saved_in = cfg.get("audio_input_index", 3)
        for i, d in _all_audio:
            if d["max_input_channels"] > 0:
                label = f"{d['name'][:52]} ({i})"
                self._cc_in_combo.addItem(label, i)
                if i == saved_in:
                    self._cc_in_combo.setCurrentIndex(self._cc_in_combo.count() - 1)
        if self._cc_in_combo.count() == 0:
            self._cc_in_combo.addItem("No audio input devices found", None)

        lbl_cc_in = QLabel("Capture Card Input:")
        lbl_cc_in.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gcc_form.addRow(lbl_cc_in, self._cc_in_combo)
        hint_cc_in = QLabel("Select the audio output of your capture card device")
        hint_cc_in.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gcc_form.addRow("", hint_cc_in)

        # Audio Output combo (monitoring)
        self._cc_out_combo = QComboBox()
        self._cc_out_combo.setToolTip(
            "Where you hear the capture card audio (your headphones or speakers)."
        )
        self._cc_out_combo.addItem("System default", None)
        saved_out = cfg.get("audio_output_index", None)
        for i, d in _all_audio:
            if d["max_output_channels"] > 0:
                label = f"{d['name'][:52]} ({i})"
                self._cc_out_combo.addItem(label, i)
                if i == saved_out:
                    self._cc_out_combo.setCurrentIndex(self._cc_out_combo.count() - 1)

        lbl_cc_out = QLabel("Monitoring Output:")
        lbl_cc_out.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gcc_form.addRow(lbl_cc_out, self._cc_out_combo)
        hint_cc_out = QLabel("Where you hear the capture card audio (headphones / speakers)")
        hint_cc_out.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gcc_form.addRow("", hint_cc_out)

        gcc.addLayout(gcc_form)
        layout.addWidget(grp_cc)

        # Volume section
        grp = self._section("Volume & Monitoring")
        gl = QFormLayout(grp)
        gl.setSpacing(14)
        gl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gl.setContentsMargins(12, 16, 12, 12)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(10)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 200)
        self.vol_slider.setValue(int(cfg.get("volume", 1.0) * 100))
        self.vol_slider.setToolTip("Adjust playback volume (0=silent, 100=unity, 200=boost)")
        self.vol_spin = QSpinBox()
        self.vol_spin.setRange(0, 200)
        self.vol_spin.setSuffix("%")
        self.vol_spin.setFixedWidth(76)
        self.vol_spin.setValue(int(cfg.get("volume", 1.0) * 100))
        self.vol_spin.setToolTip("Type a value directly")

        def _on_vol_slider(v):
            self.vol_spin.blockSignals(True)
            self.vol_spin.setValue(v)
            self.vol_spin.blockSignals(False)
            if audio:
                audio.set_volume(v / 100)
            cfg["volume"] = v / 100

        def _on_vol_spin(v):
            self.vol_slider.blockSignals(True)
            self.vol_slider.setValue(v)
            self.vol_slider.blockSignals(False)
            if audio:
                audio.set_volume(v / 100)
            cfg["volume"] = v / 100

        self.vol_slider.valueChanged.connect(_on_vol_slider)
        self.vol_spin.valueChanged.connect(_on_vol_spin)
        vol_row.addWidget(self.vol_slider, 1)
        vol_row.addWidget(self.vol_spin)
        vol_widget = QWidget()
        vol_widget.setLayout(vol_row)
        lbl_vol = QLabel("Volume")
        lbl_vol.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gl.addRow(lbl_vol, vol_widget)

        # VU meter label (visual indicator of current level)
        self._vu_label = QLabel()
        self._vu_label.setFixedHeight(14)
        self._vu_label.setStyleSheet(f"background:{C['panel3']};border-radius:4px;")
        self._vu_label.setToolTip("Approximate volume level indicator")
        gl.addRow(QLabel(""), self._vu_label)
        self._update_vu(int(cfg.get("volume", 1.0) * 100))
        self.vol_slider.valueChanged.connect(self._update_vu)

        # Mute toggle — prominent button
        self.mute_btn = QPushButton()
        muted = cfg.get("muted", False)
        self.mute_btn.setText(
            "\U0001f507  MUTED  (click to unmute)" if muted
            else "\U0001f50a  Audio Active  (click to mute)"
        )
        self.mute_btn.setObjectName("danger" if muted else "accent")
        self.mute_btn.setFixedHeight(38)
        self.mute_btn.setToolTip("Toggle mute without stopping the stream")
        self._muted = muted

        def _toggle_mute_btn():
            self._muted = not self._muted
            cfg["muted"] = self._muted
            if audio:
                audio.muted = self._muted
            if self._muted:
                self.mute_btn.setText("\U0001f507  MUTED  (click to unmute)")
                self.mute_btn.setObjectName("danger")
            else:
                self.mute_btn.setText("\U0001f50a  Audio Active  (click to mute)")
                self.mute_btn.setObjectName("accent")
            self.mute_btn.setStyle(self.mute_btn.style())

        self.mute_btn.clicked.connect(_toggle_mute_btn)
        lbl_mute = QLabel("Mute")
        lbl_mute.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gl.addRow(lbl_mute, self.mute_btn)

        layout.addWidget(grp)

        # ── Sample Rate ───────────────────────────────────────────────────────
        grp_sr = self._section("Sample Rate")
        gsr = QFormLayout(grp_sr)
        gsr.setSpacing(12)
        gsr.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gsr.setContentsMargins(12, 16, 12, 12)
        self.sr_combo = QComboBox()
        self.sr_combo.setToolTip("Audio sample rate — must match your capture card / interface")
        cur_sr = cfg.get("audio_sample_rate", 48000)
        for sr in [44100, 48000, 96000]:
            self.sr_combo.addItem(f"{sr} Hz", sr)
            if sr == cur_sr:
                self.sr_combo.setCurrentIndex(self.sr_combo.count() - 1)
        lbl_sr = QLabel("Sample rate:")
        lbl_sr.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gsr.addRow(lbl_sr, self.sr_combo)
        sr_note = QLabel("Restart stream after changing sample rate.")
        sr_note.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gsr.addRow("", sr_note)
        layout.addWidget(grp_sr)

        # ── AV Sync Offset ────────────────────────────────────────────────────
        grp_sync = self._section("AV Sync Offset")
        gsync = QFormLayout(grp_sync)
        gsync.setSpacing(12)
        gsync.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gsync.setContentsMargins(12, 16, 12, 12)

        cur_delay = cfg.get("audio_delay_ms", 0)
        sync_row = QHBoxLayout()
        sync_row.setSpacing(10)
        self.sync_slider = QSlider(Qt.Horizontal)
        self.sync_slider.setRange(-500, 500)
        self.sync_slider.setSingleStep(10)
        self.sync_slider.setPageStep(50)
        self.sync_slider.setValue(cur_delay)
        self.sync_slider.setToolTip("Shift audio timing relative to video (-500 to +500 ms, step 10 ms)")
        self.sync_spin = QSpinBox()
        self.sync_spin.setRange(-500, 500)
        self.sync_spin.setSingleStep(10)
        self.sync_spin.setSuffix(" ms")
        self.sync_spin.setFixedWidth(88)
        self.sync_spin.setValue(cur_delay)
        self.sync_spin.setToolTip("Audio offset in milliseconds (negative = earlier, positive = later)")

        def _on_sync_slider(v):
            self.sync_spin.blockSignals(True)
            self.sync_spin.setValue(v)
            self.sync_spin.blockSignals(False)
            cfg["audio_delay_ms"] = v
            if audio:
                audio.set_delay(v)

        def _on_sync_spin(v):
            self.sync_slider.blockSignals(True)
            self.sync_slider.setValue(v)
            self.sync_slider.blockSignals(False)
            cfg["audio_delay_ms"] = v
            if audio:
                audio.set_delay(v)

        self.sync_slider.valueChanged.connect(_on_sync_slider)
        self.sync_spin.valueChanged.connect(_on_sync_spin)
        sync_row.addWidget(self.sync_slider, 1)
        sync_row.addWidget(self.sync_spin)
        sync_widget = QWidget()
        sync_widget.setLayout(sync_row)
        lbl_sync = QLabel("Sync offset")
        lbl_sync.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gsync.addRow(lbl_sync, sync_widget)

        sync_hint = QLabel("Negative = audio arrives earlier (before video).  Positive = audio arrives later (after video).")
        sync_hint.setWordWrap(True)
        sync_hint.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gsync.addRow("", sync_hint)
        layout.addWidget(grp_sync)

        # ── Microphone ────────────────────────────────────────────────────────
        grp_mic = self._section("Microphone Input")
        gmic = QVBoxLayout(grp_mic)
        gmic.setSpacing(12)
        gmic.setContentsMargins(12, 16, 12, 12)

        self._mic_enabled_chk = QCheckBox("Enable Microphone")
        self._mic_enabled_chk.setChecked(cfg.get("mic_enabled", False))
        self._mic_enabled_chk.setToolTip(
            "When unchecked the microphone is completely silent — no audio captured at all."
        )
        self._mic_enabled_chk.setStyleSheet("font-weight:bold;font-size:10pt;")
        gmic.addWidget(self._mic_enabled_chk)

        # Container widget for device/mute/volume controls — greys out when disabled
        mic_controls_widget = QWidget()
        mic_controls_inner = QVBoxLayout(mic_controls_widget)
        mic_controls_inner.setContentsMargins(0, 0, 0, 0)
        mic_controls_inner.setSpacing(10)

        # Device selector
        mic_dev_row = QHBoxLayout()
        mic_dev_row.setSpacing(8)
        mic_dev_lbl = QLabel("Device:")
        mic_dev_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        mic_dev_lbl.setFixedWidth(68)
        self._mic_combo = QComboBox()
        self._mic_combo.setToolTip(
            "Select a microphone input device. 'None' disables the mic track."
        )

        # Populate: None + all input devices (mark capture card to avoid confusion)
        capture_idx = cfg.get("audio_input_index", -1)
        self._mic_combo.addItem("None (disabled)", None)
        for i, d in _all_audio:
            if d["max_input_channels"] > 0:
                marker = "  [capture card]" if i == capture_idx else ""
                self._mic_combo.addItem(
                    f"\U0001f3a4  [{i}] {d['name'][:48]}{marker}", i
                )

        # Restore saved selection
        saved_mic_idx = cfg.get("mic_index", None)
        if saved_mic_idx is not None:
            for j in range(self._mic_combo.count()):
                if self._mic_combo.itemData(j) == saved_mic_idx:
                    self._mic_combo.setCurrentIndex(j)
                    break

        def _on_mic_device_changed(idx):
            cfg["mic_index"] = self._mic_combo.currentData()

        self._mic_combo.currentIndexChanged.connect(_on_mic_device_changed)
        mic_dev_row.addWidget(mic_dev_lbl)
        mic_dev_row.addWidget(self._mic_combo, 1)
        mic_controls_inner.addLayout(mic_dev_row)

        # Mute button — live toggle (survives dialog close via the MicEngine reference)
        self._mic_mute_btn = QPushButton()
        mic_muted_init = cfg.get("mic_muted", False) if mic is None else mic.muted
        self._mic_muted = mic_muted_init

        def _refresh_mic_btn():
            if self._mic_muted:
                self._mic_mute_btn.setText("\U0001f3a4  MIC MUTED  (click to unmute)")
                self._mic_mute_btn.setObjectName("danger")
            else:
                self._mic_mute_btn.setText("\U0001f3a4  MIC LIVE  (click to mute)")
                self._mic_mute_btn.setObjectName("accent")
            self._mic_mute_btn.setStyle(self._mic_mute_btn.style())

        def _toggle_mic_mute_btn():
            if mic is not None:
                self._mic_muted = mic.toggle_mute()
            else:
                self._mic_muted = not self._mic_muted
            cfg["mic_muted"] = self._mic_muted
            _refresh_mic_btn()

        self._mic_mute_btn.setFixedHeight(38)
        self._mic_mute_btn.setToolTip("Toggle microphone mute without restarting the stream")
        self._mic_mute_btn.clicked.connect(_toggle_mic_mute_btn)
        _refresh_mic_btn()
        mic_controls_inner.addWidget(self._mic_mute_btn)

        # Volume row: slider + spinbox (0–200%)
        mic_vol_row = QHBoxLayout()
        mic_vol_row.setSpacing(10)
        mic_vol_lbl = QLabel("Mic Volume:")
        mic_vol_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        mic_vol_lbl.setFixedWidth(80)

        init_mic_vol = int((cfg.get("mic_volume", 1.0) if mic is None else mic.volume) * 100)
        self._mic_vol_slider = QSlider(Qt.Horizontal)
        self._mic_vol_slider.setRange(0, 200)
        self._mic_vol_slider.setValue(init_mic_vol)
        self._mic_vol_slider.setToolTip("Microphone gain (0=silent, 100=unity, 200=boost)")
        self._mic_vol_spin = QSpinBox()
        self._mic_vol_spin.setRange(0, 200)
        self._mic_vol_spin.setSuffix("%")
        self._mic_vol_spin.setFixedWidth(76)
        self._mic_vol_spin.setValue(init_mic_vol)
        self._mic_vol_spin.setToolTip("Type mic volume directly")

        def _on_mic_vol_slider(v):
            self._mic_vol_spin.blockSignals(True)
            self._mic_vol_spin.setValue(v)
            self._mic_vol_spin.blockSignals(False)
            cfg["mic_volume"] = v / 100.0
            if mic is not None:
                mic.volume = v / 100.0

        def _on_mic_vol_spin(v):
            self._mic_vol_slider.blockSignals(True)
            self._mic_vol_slider.setValue(v)
            self._mic_vol_slider.blockSignals(False)
            cfg["mic_volume"] = v / 100.0
            if mic is not None:
                mic.volume = v / 100.0

        self._mic_vol_slider.valueChanged.connect(_on_mic_vol_slider)
        self._mic_vol_spin.valueChanged.connect(_on_mic_vol_spin)
        mic_vol_row.addWidget(mic_vol_lbl)
        mic_vol_row.addWidget(self._mic_vol_slider, 1)
        mic_vol_row.addWidget(self._mic_vol_spin)
        mic_controls_inner.addLayout(mic_vol_row)

        mic_note = QLabel(
            "Changes to device selection take effect on the next stream restart.\n"
            "Mute and volume adjust live."
        )
        mic_note.setWordWrap(True)
        mic_note.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        mic_controls_inner.addWidget(mic_note)

        gmic.addWidget(mic_controls_widget)
        layout.addWidget(grp_mic)

        # Wire Enable checkbox — grey out sub-controls and start/stop mic live
        def _on_mic_enabled_toggled(checked):
            mic_controls_widget.setEnabled(checked)
            cfg["mic_enabled"] = checked
            if mic is not None:
                if checked:
                    if not mic.is_running():
                        mic._cfg["mic_enabled"] = True
                        mic.start()
                else:
                    mic.stop()

        self._mic_enabled_chk.toggled.connect(_on_mic_enabled_toggled)
        mic_controls_widget.setEnabled(cfg.get("mic_enabled", False))

        note = QLabel("Volume above 100% amplifies the signal (may clip).")
        note.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        layout.addWidget(note)
        layout.addLayout(self._buttons("Close"))

    def _update_vu(self, val):
        """Draw a simple gradient bar as a visual volume level indicator."""
        pct = min(val, 200) / 200.0
        if pct <= 0.5:
            color = C["good"]
        elif pct <= 0.85:
            color = C["warn"]
        else:
            color = C["bad"]
        self._vu_label.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"  stop:0 {color}cc, stop:{pct:.2f} {color}88, "
            f"stop:{min(pct + 0.01, 1.0):.2f} {C['panel3']}, stop:1 {C['panel3']});"
            f"border-radius:4px;"
        )

    def accept(self):
        self.cfg["audio_sample_rate"] = self.sr_combo.currentData()
        self.cfg["audio_delay_ms"]    = self.sync_spin.value()
        self.cfg["audio_input_index"]  = self._cc_in_combo.currentData()
        self.cfg["audio_output_index"] = self._cc_out_combo.currentData()
        self.cfg["mic_enabled"] = self._mic_enabled_chk.isChecked()
        self.cfg["mic_index"]   = self._mic_combo.currentData()
        self.cfg["mic_muted"]   = self._mic_muted
        self.cfg["mic_volume"]  = self._mic_vol_spin.value() / 100.0
        self.close()
