"""MainWindow — top-level Qt window that wires everything together.

Owns the video preview, toolbar, status bar, fullscreen HUD, all dialog
launchers, and the recording / clip / screenshot pipelines.

Imports flow strictly downward: this module pulls in `core/*`, `ui/widgets/*`,
and `ui/dialogs/*` — none of those import from here.
"""
import os
import time
import threading
from datetime import datetime

import cv2
from PySide6.QtCore import (
    Qt, QSize, QTimer, QByteArray, QPropertyAnimation, QEasingCurve,
)
from PySide6.QtGui import QAction, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QStatusBar,
    QToolBar, QWidget,
)

from constants import APP_NAME, RESOLUTIONS, FPS_OPTIONS
from config import load_config, save_config
from theme import C, STYLESHEET

from core.perf import PerfTracker
from core.video_thread import VideoThread
from core.audio_engine import AudioEngine
from core.mic_engine import MicEngine
from core.recorder import VideoRecorder
from core.clip_buffer import ClipBuffer, ClipSaveWorker
from core.system_stats import SystemStats

from hotkeys import GlobalHotkeyManager

from ui.widgets.video_widget import VideoWidget
from ui.widgets.status_pill import StatusPill

from ui.dialogs.audio_dialog import AudioDialog
from ui.dialogs.image_dialog import ImageDialog
from ui.dialogs.upscale_dialog import UpscaleDialog
from ui.dialogs.recording_dialog import RecordingDialog
from ui.dialogs.device_dialog import DeviceDialog
from ui.dialogs.hotkey_dialog import HotkeyDialog
from ui.dialogs.about_dialog import show_about


class MainWindow(QMainWindow):
    # Re-exported for legacy callers; canonical source is constants.RESOLUTIONS / FPS_OPTIONS
    RESOLUTIONS = RESOLUTIONS
    FPS_OPTIONS = FPS_OPTIONS

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.perf = PerfTracker()
        self.recorder = VideoRecorder()
        # ClipBuffer with JPEG compression; 15s default; off by default
        self.clip_buf = ClipBuffer(
            self.cfg.get("clip_duration", 15),
            self.cfg.get("fps", 60),
            jpeg_quality=self.cfg.get("clip_buffer_jpeg_quality", 85),
        )
        self.audio = None
        self.vthread = None
        self.running = False
        self._raw_frame = None
        self._frame_lock = threading.Lock()
        self._sys_data = {}
        self.mic = MicEngine(self.cfg)
        self.fs_mode = False

        # Global hotkey manager — bridges keyboard lib callbacks to the Qt thread
        self._global_hk = GlobalHotkeyManager(self)
        self._global_hk.triggered.connect(self._on_global_hotkey)

        self._build_ui()
        self._build_menu()
        self._bind_shortcuts()
        self._update_clip_action()
        # Apply preview FPS cap to VideoWidget
        self.video.set_render_fps(self.cfg.get("preview_fps_cap", 30))

        # SystemStats starts paused — only poll when overlay is visible
        self.sys_stats = SystemStats()
        self.sys_stats.updated.connect(self._on_sys_stats)
        self.sys_stats.start()

        if self.cfg.get("geometry"):
            try:
                self.restoreGeometry(
                    QByteArray.fromHex(bytes(self.cfg["geometry"], "ascii"))
                )
            except Exception:
                pass
        else:
            self.resize(1440, 860)

        self.setWindowTitle(APP_NAME)
        self.setStyleSheet(STYLESHEET)
        if self.cfg.get("always_on_top"):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        if self.cfg.get("auto_start", True):
            QTimer.singleShot(1500, self.start_stream)
        self._apply_global_hotkeys()

    def _update_clip_action(self):
        """Grey out / tooltip the CLIP toolbar button based on clip_buffer_enabled."""
        enabled = self.cfg.get("clip_buffer_enabled", False)
        dur = self.cfg.get("clip_duration", 15)
        if enabled:
            self._clip_action.setEnabled(True)
            self._clip_action.setToolTip(f"Save last {dur}s as instant clip  [F9]")
        else:
            self._clip_action.setEnabled(False)
            self._clip_action.setToolTip(
                "Enable clip buffer in Recording Settings first\n"
                "(Tools \u2192 Recording Settings\u2026 \u2192 Clip Buffer section)"
            )

    # ── UI CONSTRUCTION ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Central widget: video fills everything
        self.video = VideoWidget()
        self.video._ar_lock = self.cfg.get("aspect_ratio_lock", True)
        self.video.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video.customContextMenuRequested.connect(self._show_ctx_menu)
        self.setCentralWidget(self.video)

        # QToolBar (primary controls)
        self.toolbar = QToolBar("Main Controls", self)
        self.toolbar.setObjectName("main_toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setStyleSheet(
            f"QToolBar{{background:{C['toolbar']};border-bottom:1px solid {C['border2']};"
            f"padding:3px 8px;spacing:2px;}}"
        )
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        brand = QLabel(f"  \u2b21  {APP_NAME.upper()}  ")
        brand.setStyleSheet(
            f"color:{C['accent']};font-size:11pt;font-weight:bold;"
            f"letter-spacing:2px;border:none;padding:0 10px 0 4px;"
        )
        self.toolbar.addWidget(brand)

        self.status_pill = StatusPill("OFFLINE", C["danger"])
        self.status_pill.setToolTip("Capture stream state")
        self.toolbar.addWidget(self.status_pill)

        self.rec_pill = StatusPill("", C["record"])
        self.rec_pill.hide()
        self.rec_pill.setToolTip("Currently recording to file")
        self.toolbar.addWidget(self.rec_pill)

        self.mute_pill = StatusPill("", C["danger"])
        self.mute_pill.hide()
        self.mute_pill.setToolTip("Audio muted")
        self.toolbar.addWidget(self.mute_pill)

        self.toolbar.addSeparator()

        # Capture group
        self.start_action = self._tact(
            "\u25b6  START", self.toggle_stream,
            "Start / stop the capture stream  [F5]", checkable=False,
        )
        self.start_action.setObjectName("start_action")
        self.toolbar.addAction(self.start_action)
        self.toolbar.addSeparator()

        # Audio group
        self.toolbar.addWidget(self._toolbar_label("AUDIO"))
        self._mute_action = self._tact(
            "\U0001f50a  MUTE", self.toggle_mute, "Toggle audio mute  [M]",
        )
        self.toolbar.addAction(self._mute_action)
        self._mic_action = self._tact(
            "\U0001f3a4  MIC", self._toggle_mic_mute, "Toggle microphone mute",
        )
        self._mic_action.setCheckable(True)
        self.toolbar.addAction(self._mic_action)
        self.toolbar.addSeparator()

        # Recording group
        self.toolbar.addWidget(self._toolbar_label("CAPTURE"))
        self._rec_action = self._tact(
            "\u23fa  REC", self.toggle_recording,
            "Start / stop recording to file  [F10]",
        )
        self.toolbar.addAction(self._rec_action)
        self._clip_action = self._tact(
            "\U0001f4be  CLIP", self.save_clip,
            f"Save last {self.cfg.get('clip_duration', 15)}s as instant clip  [F9]",
        )
        self.toolbar.addAction(self._clip_action)
        self._shot_action = self._tact(
            "\U0001f4f7  SHOT", self.take_screenshot,
            "Capture a PNG screenshot  [F12]",
        )
        self.toolbar.addAction(self._shot_action)
        self.toolbar.addSeparator()

        # View group
        self.toolbar.addWidget(self._toolbar_label("VIEW"))
        self._overlay_action = self._tact(
            "\U0001f4ca  OVERLAY", self._toggle_overlay,
            "Toggle performance HUD overlay  [P]", checkable=True,
        )
        self.toolbar.addAction(self._overlay_action)
        self._fs_action = self._tact(
            "\u29c6  FULL", self.toggle_fullscreen, "Enter fullscreen mode  [F11]",
        )
        self.toolbar.addAction(self._fs_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        # Right-side info labels in toolbar
        self.res_lbl = QLabel("\u2014")
        self.res_lbl.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;border:none;padding:0 4px;"
        )
        self.res_lbl.setToolTip("Active capture resolution")
        self.toolbar.addWidget(self.res_lbl)

        _sep_a = QFrame()
        _sep_a.setFrameShape(QFrame.VLine)
        _sep_a.setStyleSheet(f"color:{C['border2']};margin:7px 4px;")
        self.toolbar.addWidget(_sep_a)

        self.fps_lbl = QLabel("\u2014")
        self.fps_lbl.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;border:none;padding:0 4px;"
        )
        self.fps_lbl.setToolTip("Live frames-per-second")
        self.toolbar.addWidget(self.fps_lbl)

        _sep_b = QFrame()
        _sep_b.setFrameShape(QFrame.VLine)
        _sep_b.setStyleSheet(f"color:{C['border2']};margin:7px 4px;")
        self.toolbar.addWidget(_sep_b)

        self.vol_lbl = QLabel("VOL 100%")
        self.vol_lbl.setStyleSheet(
            f"color:{C['subtext']};font-size:9pt;border:none;padding:0 4px;"
        )
        self.vol_lbl.setToolTip("Current audio volume level")
        self.toolbar.addWidget(self.vol_lbl)

        # Back-compat aliases
        self.rec_lbl = self.rec_pill
        self.mute_lbl = self.mute_pill
        self.shot_lbl = QLabel("")
        self.shot_lbl.hide()
        self.clip_lbl = QLabel("")
        self.clip_lbl.hide()

        self._build_statusbar()

        # Fullscreen floating HUD toolbar
        self.fs_bar = QWidget(self.video)
        self.fs_bar.setStyleSheet(
            f"QWidget{{background:rgba(13,13,30,215);border-radius:14px;"
            f"border:1px solid {C['border2']};}}"
        )
        self.fs_bar.hide()
        fs_layout = QHBoxLayout(self.fs_bar)
        fs_layout.setContentsMargins(14, 8, 14, 8)
        fs_layout.setSpacing(3)

        self._fs_info_lbl = QLabel("")
        self._fs_info_lbl.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;background:transparent;"
            f"border:none;padding:0 10px 0 0;"
        )
        fs_layout.addWidget(self._fs_info_lbl)

        fs_vsep = QFrame()
        fs_vsep.setFrameShape(QFrame.VLine)
        fs_vsep.setStyleSheet(f"color:{C['border2']};margin:4px 6px;")
        fs_layout.addWidget(fs_vsep)

        for text, cmd, oid, tip in [
            ("\u25a0 STOP",     self.stop_stream,       "danger", "Stop stream"),
            ("\U0001f507 MUTE", self.toggle_mute,       "",       "Mute audio  [M]"),
            ("\u23fa REC",      self.toggle_recording,  "danger", "Record  [F10]"),
            ("\U0001f4f7 SHOT", self.take_screenshot,   "",       "Screenshot  [F12]"),
            ("\U0001f4ca HUD",  self._toggle_overlay,   "",       "Performance overlay  [P]"),
            ("\u29c6 EXIT FS",  self.toggle_fullscreen, "accent", "Exit fullscreen  [F11/ESC]"),
        ]:
            btn = self._tbtn(text, cmd, tip=tip, small=True)
            if oid:
                btn.setObjectName(oid)
            fs_layout.addWidget(btn)
        self.fs_bar.adjustSize()

        # Opacity animation for smooth fade
        self._fs_opacity = QGraphicsOpacityEffect(self.fs_bar)
        self.fs_bar.setGraphicsEffect(self._fs_opacity)
        self._fs_anim = QPropertyAnimation(self._fs_opacity, b"opacity")
        self._fs_anim.setDuration(220)
        self._fs_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.video.setMouseTracking(True)
        self.video.mouseMoveEvent = self._video_mouse_move
        self._fs_timer = QTimer()
        self._fs_timer.setSingleShot(True)
        self._fs_timer.timeout.connect(self._fs_bar_fade_out)
        self.flash = QLabel(self.video)
        self.flash.hide()

    def _build_statusbar(self):
        """Build the bottom QStatusBar with segmented status sections."""
        sb = QStatusBar(self)
        self.setStatusBar(sb)
        sb.setSizeGripEnabled(False)

        self._sb_conn = QLabel("  \u2b58  Offline  ")
        self._sb_conn.setStyleSheet(
            f"color:{C['bad']};font-size:9pt;border-right:1px solid {C['border']};"
        )
        self._sb_conn.setToolTip("Stream connection state")
        sb.addWidget(self._sb_conn)

        self._sb_res = QLabel("  \u2014  ")
        self._sb_res.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};"
        )
        self._sb_res.setToolTip("Capture resolution")
        sb.addWidget(self._sb_res)

        self._sb_fps = QLabel("  \u2014  ")
        self._sb_fps.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};"
        )
        self._sb_fps.setToolTip("Live frame rate")
        sb.addWidget(self._sb_fps)

        self._sb_drop = QLabel("  DROP: \u2014  ")
        self._sb_drop.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};"
        )
        self._sb_drop.setToolTip("Dropped frame percentage")
        sb.addWidget(self._sb_drop)

        self._sb_audio = QLabel("  \U0001f50a 100%  ")
        self._sb_audio.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};"
        )
        self._sb_audio.setToolTip("Audio volume level")
        sb.addWidget(self._sb_audio)

        self._sb_rec = QLabel("  ")
        self._sb_rec.setStyleSheet(f"color:{C['subtext']};font-size:9pt;")
        sb.addPermanentWidget(self._sb_rec)

        self.notify_lbl = QLabel("")
        self.notify_lbl.setStyleSheet(f"color:{C['text2']};font-size:9pt;")
        sb.addPermanentWidget(self.notify_lbl)

        self._rec_start_time = None
        self._rec_timer = QTimer()
        self._rec_timer.setInterval(1000)
        self._rec_timer.timeout.connect(self._update_rec_duration)

    def _update_rec_duration(self):
        if self.recorder.recording and self._rec_start_time:
            elapsed = int(time.time() - self._rec_start_time)
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            dur = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            self._sb_rec.setText(f"  \u23fa REC {dur}  ")
            self._sb_rec.setStyleSheet(
                f"color:{C['record']};font-size:9pt;font-weight:bold;"
            )
        else:
            self._sb_rec.setText("  ")
            self._sb_rec.setStyleSheet(f"color:{C['subtext']};font-size:9pt;")

    def _tbtn(self, text, cmd, tip="", small=False):
        """Create a styled push button for use in the fullscreen HUD."""
        btn = QPushButton(text)
        btn.clicked.connect(cmd)
        btn.setFixedHeight(30 if small else 34)
        btn.setMinimumWidth(50)
        if tip:
            btn.setToolTip(tip)
        sz = "8" if small else "9"
        btn.setStyleSheet(
            f"QPushButton{{background:{C['panel2']};color:{C['text']};"
            f"border:1px solid {C['border2']};border-radius:7px;"
            f"padding:0 12px;font-size:{sz}pt;font-weight:bold;margin:0 2px;}}"
            f"QPushButton:hover{{background:{C['hover2']};color:{C['accent']};"
            f"border-color:{C['accent']}}}"
            f"QPushButton:pressed{{background:{C['panel']};color:{C['accent2']};}}"
            f"QPushButton#accent{{background:{C['accent']};color:#000;border:none;}}"
            f"QPushButton#danger{{background:{C['record']};color:#fff;border:none;}}"
        )
        return btn

    def _tact(self, text, cmd, tip="", checkable=False):
        """Create a QAction for the toolbar."""
        a = QAction(text, self)
        a.triggered.connect(cmd)
        if tip:
            a.setToolTip(tip)
            a.setStatusTip(tip)
        if checkable:
            a.setCheckable(True)
        return a

    def _toolbar_label(self, text):
        """Create a small section label for the toolbar."""
        lbl = QLabel(f"  {text}")
        lbl.setStyleSheet(
            f"color:{C['subtext']};font-size:7pt;font-weight:bold;"
            f"letter-spacing:1.2px;border:none;padding:0 2px;"
        )
        return lbl

    def _vline(self):
        """Thin vertical separator."""
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setFixedWidth(1)
        f.setStyleSheet(f"color:{C['border2']};margin:6px 8px;")
        return f

    def _build_menu(self):
        mb = self.menuBar()

        def menu(t):
            return mb.addMenu(t)

        def act(m, label, slot, shortcut=None):
            a = QAction(label, self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            m.addAction(a)
            return a

        # File
        fm = menu("&File")
        act(fm, "\U0001f4c1  Open Save Location",
            lambda: self._open_folder(self.cfg.get("recording_path", "")))
        act(fm, "\U0001f4be  Export Clip  [F9]", self.save_clip, "F9")
        fm.addSeparator()
        exit_act = QAction("\u2715  Exit", self)
        exit_act.triggered.connect(self.close)
        exit_act.setShortcut(QKeySequence("Ctrl+Q"))
        fm.addAction(exit_act)

        # Capture
        cm = menu("&Capture")
        act(cm, "\u25b6  Start Stream  [F5]", self.start_stream, "F5")
        act(cm, "\u25a0  Stop Stream   [F5]", self.stop_stream)
        cm.addSeparator()
        act(cm, "\u23fa  Start Recording  [F10]", self.start_recording, "F10")
        act(cm, "\u23f9  Stop Recording   [F10]", self.stop_recording)
        cm.addSeparator()
        act(cm, "\U0001f4f7  Take Screenshot  [F12]", self.take_screenshot, "F12")
        act(cm, "\U0001f4be  Save Clip         [F9]", self.save_clip)

        # View
        vm = menu("&View")
        act(vm, "\u29c6  Fullscreen  [F11]", self.toggle_fullscreen, "F11")
        vm.addSeparator()
        act(vm, "\U0001f4ca  Toggle Overlay  [P]", self._toggle_overlay, "P")
        vm.addSeparator()
        act(vm, "\U0001f50d  Toggle Upscale", self._open_upscale)
        vm.addSeparator()
        act(vm, "\u2295  Zoom In", lambda: self.video._zoom_in())
        act(vm, "\u2296  Zoom Out",
            lambda: setattr(self.video, "_zoom", max(1.0, self.video._zoom / 1.1))
            or self.video.update())
        act(vm, "\u21ba  Reset Zoom  [Z]", self.video.reset_zoom, "Z")
        vm.addSeparator()
        self._ar_action = QAction("\u2713  Lock Aspect Ratio", self, checkable=True)
        self._ar_action.setChecked(self.cfg.get("aspect_ratio_lock", True))
        self._ar_action.triggered.connect(self._toggle_ar_lock)
        vm.addAction(self._ar_action)

        vm.addSeparator()
        rm = vm.addMenu("Resolution")
        self._res_actions = {}
        for label, val in self.RESOLUTIONS.items():
            a = QAction(label, self, checkable=True)
            a.setChecked(val == self.cfg.get("resolution", "1920x1080"))
            a.triggered.connect(lambda c, v=val: self._set_resolution(v))
            rm.addAction(a)
            self._res_actions[val] = a
        frm = vm.addMenu("Frame Rate")
        self._fps_actions = {}
        for f in self.FPS_OPTIONS:
            a = QAction(f"{f} fps", self, checkable=True)
            a.setChecked(f == self.cfg.get("fps", 60))
            a.triggered.connect(lambda c, fps=f: self._set_fps(fps))
            frm.addAction(a)
            self._fps_actions[f] = a

        # Tools
        tm = menu("&Tools")
        act(tm, "\U0001f50a  Audio Settings...", self._open_audio)
        act(tm, "\u25c8  Image Settings...", self._open_image)
        act(tm, "\U0001f50d  Upscale Settings...", self._open_upscale)
        act(tm, "\u23fa  Recording Settings...", self._open_recording)
        act(tm, "\u2699  Device Settings...", self._open_devices)
        tm.addSeparator()
        act(tm, "\U0001f4c1  Open Recordings Folder",
            lambda: self._open_folder(self.cfg.get("recording_path", "")))
        act(tm, "\U0001f4f7  Open Screenshots Folder",
            lambda: self._open_folder(self.cfg.get("screenshot_path", "")))
        tm.addSeparator()
        act(tm, "\u21ba  Reset Image  [R]", self._reset_image, "R")
        act(tm, "\u21ba  Reset Perf Stats", self.perf.reset)
        tm.addSeparator()
        act(tm, "\U0001f50a  Mute / Unmute  [M]", self.toggle_mute, "M")
        act(tm, "\u25b2  Volume Up  [=]", lambda: self._nudge_vol(0.1), "=")
        act(tm, "\u25bc  Volume Down  [-]", lambda: self._nudge_vol(-0.1), "-")
        tm.addSeparator()
        act(tm, "\u2328  Hotkeys\u2026", self._open_hotkeys)
        tm.addSeparator()
        self._aot_action = QAction("Always on Top", self, checkable=True)
        self._aot_action.setChecked(self.cfg.get("always_on_top", False))
        self._aot_action.triggered.connect(self._toggle_aot)
        tm.addAction(self._aot_action)

        # Help
        hm = menu("&Help")
        act(hm, "?  About", self._show_about)

    def _show_ctx_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(STYLESHEET)

        start_lbl = "\u25a0 Stop Stream  [F5]" if self.running else "\u25b6 Start Stream  [F5]"
        menu.addAction(start_lbl, self.toggle_stream)
        menu.addSeparator()

        menu.addAction("\U0001f4f7 Screenshot  [F12]", self.take_screenshot)
        copy_act = menu.addAction("\U0001f4cb Copy Frame", self._copy_frame)
        copy_act.setEnabled(self.running)
        menu.addAction("\U0001f4be Save Clip  [F9]", self.save_clip)
        menu.addSeparator()

        zm = menu.addMenu("\U0001f50d Zoom")
        zm.addAction("\u2295 Zoom In",
                     lambda: self.video._zoom_in() or self.video.update())
        zm.addAction("\u2296 Zoom Out",
                     lambda: setattr(self.video, "_zoom", max(1.0, self.video._zoom / 1.1))
                     or self.video.update())
        zm.addAction("\u21ba Reset Zoom  [Z]", self.video.reset_zoom)

        menu.addAction("\u29c6 Fullscreen  [F11]", self.toggle_fullscreen)
        menu.addSeparator()

        overlay_lbl = ("\U0001f4ca Hide Overlay  [P]"
                       if self.video._overlay_on
                       else "\U0001f4ca Show Overlay  [P]")
        menu.addAction(overlay_lbl, self._toggle_overlay)
        menu.exec(self.video.mapToGlobal(pos))

    def _copy_frame(self):
        """Copy the current video frame to the clipboard as an image."""
        with self._frame_lock:
            frame = self._raw_frame
        if frame is None:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()
        QApplication.clipboard().setPixmap(QPixmap.fromImage(img))

    def _bind_shortcuts(self):
        """(Re-)register all keyboard shortcuts, reading from cfg["hotkeys"] with defaults."""
        hk = self.cfg.get("hotkeys", {})

        def k(action, default):
            return hk.get(action, default)

        bindings = [
            (k("toggle_stream",     "F5"),  self.toggle_stream),
            (k("save_clip",         "F9"),  self.save_clip),
            (k("toggle_recording",  "F10"), self.toggle_recording),
            (k("toggle_fullscreen", "F11"), self.toggle_fullscreen),
            (k("screenshot",        "F12"), self.take_screenshot),
            (k("toggle_mute",       "M"),   self.toggle_mute),
            (k("toggle_overlay",    "P"),   self._toggle_overlay),
            (k("reset_image",       "R"),   self._reset_image),
            (k("reset_zoom",        "Z"),   self.video.reset_zoom),
            (k("volume_up",         "="),   lambda: self._nudge_vol(0.1)),
            (k("volume_down",       "-"),   lambda: self._nudge_vol(-0.1)),
            ("Escape", lambda: self.toggle_fullscreen() if self.fs_mode else None),
        ]

        if hasattr(self, "_shortcuts"):
            for sc in self._shortcuts.values():
                try:
                    sc.setEnabled(False)
                    sc.deleteLater()
                except Exception:
                    pass
        self._shortcuts = {}

        for key, slot in bindings:
            if not key:
                continue
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)
            self._shortcuts[key] = sc

        exit_key = k("exit_app", "Ctrl+Q")
        sc_exit = QShortcut(QKeySequence(exit_key), self)
        sc_exit.activated.connect(self.close)
        self._shortcuts[exit_key] = sc_exit

        if hasattr(self, "_global_hk"):
            self._apply_global_hotkeys()

    # ── GLOBAL HOTKEY DISPATCH ────────────────────────────────────────────────
    def _on_global_hotkey(self, action_key: str):
        """Slot called (on the Qt main thread via Signal) when a global hotkey fires."""
        actions = {
            "toggle_stream":     self.toggle_stream,
            "save_clip":         self.save_clip,
            "toggle_recording":  self.toggle_recording,
            "toggle_fullscreen": self.toggle_fullscreen,
            "screenshot":        self.take_screenshot,
            "toggle_mute":       self.toggle_mute,
            "toggle_overlay":    self._toggle_overlay,
            "reset_image":       self._reset_image,
            "reset_zoom":        self.video.reset_zoom,
            "volume_up":         lambda: self._nudge_vol(0.1),
            "volume_down":       lambda: self._nudge_vol(-0.1),
        }
        fn = actions.get(action_key)
        if fn:
            fn()

    def _apply_global_hotkeys(self):
        """Register (or clear) global hotkeys based on current config."""
        if not self.cfg.get("global_hotkeys_enabled", False):
            self._global_hk.unregister_all()
            return
        self._global_hk.set_enabled(True)
        hk = self.cfg.get("hotkeys", {})
        defaults = {key: dflt for key, _name, dflt in HotkeyDialog.ACTIONS}
        for action_key in self.cfg.get("global_hotkey_actions", []):
            key_str = hk.get(action_key, defaults.get(action_key, ""))
            if key_str:
                self._global_hk.register(action_key, key_str)

    # ── FULLSCREEN ────────────────────────────────────────────────────────────
    def toggle_fullscreen(self):
        self.fs_mode = not self.fs_mode
        if self.fs_mode:
            self.toolbar.hide()
            self.statusBar().hide()
            self.menuBar().hide()
            self.showFullScreen()
            self._show_fs_hint()
        else:
            self.toolbar.show()
            self.statusBar().show()
            self.menuBar().show()
            self.showNormal()
            self.fs_bar.hide()

    def _show_fs_hint(self):
        hint = QLabel(
            "\u29c6  FULLSCREEN  \u2022  F11 or ESC to exit  \u2022  "
            "Move mouse to bottom edge for HUD",
            self.video,
        )
        hint.setStyleSheet(
            f"background:rgba(10,10,30,215);color:{C['text2']};"
            f"border-radius:8px;padding:8px 18px;font-size:9pt;"
            f"border:1px solid {C['border2']};"
        )
        hint.adjustSize()
        hint.move(
            self.video.width() // 2 - hint.width() // 2,
            self.video.height() - hint.height() - 28,
        )
        hint.show()
        QTimer.singleShot(3800, hint.deleteLater)

    def _fs_bar_fade_in(self):
        self._fs_anim.stop()
        self._fs_anim.setStartValue(self._fs_opacity.opacity())
        self._fs_anim.setEndValue(1.0)
        try:
            self._fs_anim.finished.disconnect(self._on_fs_fade_done)
        except Exception:
            pass
        self._fs_anim.start()
        self.fs_bar.show()
        self.fs_bar.raise_()

    def _fs_bar_fade_out(self):
        self._fs_anim.stop()
        self._fs_anim.setStartValue(self._fs_opacity.opacity())
        self._fs_anim.setEndValue(0.0)
        self._fs_anim.finished.connect(self._on_fs_fade_done)
        self._fs_anim.start()

    def _on_fs_fade_done(self):
        try:
            self._fs_anim.finished.disconnect(self._on_fs_fade_done)
        except Exception:
            pass
        if self._fs_opacity.opacity() < 0.05:
            self.fs_bar.hide()

    def _video_mouse_move(self, event):
        VideoWidget.mouseMoveEvent(self.video, event)
        if not self.fs_mode:
            return
        if event.position().y() > self.video.height() * 0.80:
            snap = self.perf.snapshot()
            fps = snap.get("fps", 0)
            drop = snap.get("drop_pct", 0)
            res = self.cfg.get("resolution", "")
            rec_tag = "  \u23fa REC" if self.recorder.recording else ""
            self._fs_info_lbl.setText(
                f"\u25cf {'LIVE' if self.running else 'OFFLINE'}  |  {res}  |  "
                f"{fps:.0f} fps  |  {drop:.1f}% drop{rec_tag}"
            )
            self.fs_bar.adjustSize()
            w = max(680, self.fs_bar.sizeHint().width())
            h = self.fs_bar.sizeHint().height()
            self.fs_bar.setGeometry(
                (self.video.width() - w) // 2,
                self.video.height() - h - 14, w, h,
            )
            self._fs_bar_fade_in()
            self._fs_timer.start(3200)
        else:
            if not self._fs_timer.isActive():
                self._fs_timer.start(1600)

    # ── STREAM CONTROL ────────────────────────────────────────────────────────
    def toggle_stream(self):
        if self.running:
            self.stop_stream()
        else:
            self.start_stream()

    def start_stream(self):
        if self.running:
            return
        in_idx = self.cfg.get("audio_input_index", 3)
        out_idx = self.cfg.get("audio_output_index", None)
        sr = self.cfg.get("audio_sample_rate", 48000)
        self.audio = AudioEngine(in_idx, out_idx, sample_rate=sr)
        self.audio.set_volume(self.cfg.get("volume", 1.0))
        if self.cfg.get("muted", False):
            self.audio.muted = True
        self.audio.start(delay_ms=self.cfg.get("audio_delay_ms", 0))
        self.vthread = VideoThread(self.cfg, self.perf)
        self.vthread.frame_ready.connect(self._on_frame)
        self.vthread.error.connect(self._on_video_error)
        self.vthread.start()
        self.vthread.set_image(
            self.cfg.get("brightness", 1.0),
            self.cfg.get("contrast", 1.0),
            self.cfg.get("saturation", 1.0),
        )
        self.mic.start()
        self._update_mic_action()
        self.running = True
        self.perf.reset()
        self.status_pill.set_state("\u25cf LIVE", C["live"])
        self.start_action.setText("\u25a0  STOP")
        res = self.cfg.get("resolution", "1920x1080")
        self.res_lbl.setText(res.replace("x", "\u00d7"))
        self._sb_conn.setText("  \u25cf  Live  ")
        self._sb_conn.setStyleSheet(
            f"color:{C['good']};font-size:9pt;"
            f"border-right:1px solid {C['border']};font-weight:bold;"
        )
        self._sb_res.setText(f"  {res.replace('x', chr(0x00d7))}  ")
        if self.cfg.get("muted", False):
            self.mute_pill.set_state("\U0001f507 MUTED", C["danger"])
            self.mute_pill.show()
        self._update_vol_label()

    def stop_stream(self):
        if not self.running:
            return
        self.running = False
        if self.recorder.recording:
            self.stop_recording()
        if self.vthread:
            self.vthread.stop()
            self.vthread = None
        self.mic.stop()
        if self.audio:
            self.audio.stop()
            self.audio = None
        self.status_pill.set_state("OFFLINE", C["danger"])
        self.start_action.setText("\u25b6  START")
        self.res_lbl.setText("\u2014")
        self.fps_lbl.setText("\u2014")
        self.fps_lbl.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;border:none;padding:0 4px;"
        )
        self._sb_conn.setText("  \u2b58  Offline  ")
        self._sb_conn.setStyleSheet(
            f"color:{C['bad']};font-size:9pt;border-right:1px solid {C['border']};"
        )
        self._sb_res.setText("  \u2014  ")
        self._sb_fps.setText("  \u2014  ")
        self._sb_drop.setText("  DROP: \u2014  ")
        with self.video._lock:
            self.video._px = None
        self.video.update()

    def _on_frame(self, frame):
        if not self.running:
            return
        with self._frame_lock:
            self._raw_frame = frame.copy()
        if self.cfg.get("clip_buffer_enabled", False):
            self.clip_buf.push(frame)
        if self.recorder.recording:
            self.recorder.write_video(frame)
        snap = self.perf.snapshot()
        self.video.set_frame(
            frame, snap, 0.0, self.recorder.recording,
            self.cfg.get("fps", 60), self.cfg.get("upscale_mode", "none"),
            self._sys_data,
        )
        fps = snap.get("fps", 0)
        if fps > 0:
            drop = snap.get("drop_pct", 0)
            if drop > 5:
                col = C["bad"]
            elif fps >= self.cfg.get("fps", 60) * 0.95:
                col = C["good"]
            else:
                col = C["warn"]
            self.fps_lbl.setText(f"{fps:.0f} fps")
            self.fps_lbl.setStyleSheet(
                f"color:{col};font-size:9pt;border:none;padding:0 4px;"
            )
            self._sb_fps.setText(f"  {fps:.0f} fps  ")
            self._sb_fps.setStyleSheet(
                f"color:{col};font-size:9pt;border-right:1px solid {C['border']};"
            )
            drop_col = C["good"] if drop < 1 else C["warn"] if drop < 5 else C["bad"]
            self._sb_drop.setText(f"  DROP: {drop:.1f}%  ")
            self._sb_drop.setStyleSheet(
                f"color:{drop_col};font-size:9pt;"
                f"border-right:1px solid {C['border']};"
            )

    def _on_video_error(self, msg):
        self.stop_stream()
        QMessageBox.critical(self, "No Signal", msg)

    def _on_sys_stats(self, data):
        self._sys_data = data

    # ── AUDIO ─────────────────────────────────────────────────────────────────
    def toggle_mute(self):
        if not self.audio:
            return
        m = self.audio.toggle_mute()
        self.cfg["muted"] = m
        if m:
            self.mute_pill.set_state("\U0001f507 MUTED", C["danger"])
            self.mute_pill.show()
            self._sb_audio.setText("  \U0001f507 MUTED  ")
            self._sb_audio.setStyleSheet(
                f"color:{C['bad']};font-size:9pt;"
                f"border-right:1px solid {C['border']};font-weight:bold;"
            )
        else:
            self.mute_pill.hide()
            self._update_vol_label()

    def _nudge_vol(self, d):
        v = max(0.0, min(2.0, self.cfg.get("volume", 1.0) + d))
        self.cfg["volume"] = v
        if self.audio:
            self.audio.set_volume(v)
        self._update_vol_label()

    def _update_vol_label(self):
        v = self.cfg.get("volume", 1.0)
        pct = int(v * 100)
        if pct < 50:
            col = C["warn"]
        elif pct > 150:
            col = C["accent"]
        else:
            col = C["subtext"]
        self.vol_lbl.setText(f"VOL {pct}%")
        self.vol_lbl.setStyleSheet(
            f"color:{col};font-size:9pt;border:none;padding:0 4px;"
        )
        self._sb_audio.setText(f"  \U0001f50a {pct}%  ")
        self._sb_audio.setStyleSheet(
            f"color:{col};font-size:9pt;border-right:1px solid {C['border']};"
        )

    def _toggle_mic_mute(self):
        """Toggle microphone mute and refresh the toolbar button state."""
        muted = self.mic.toggle_mute()
        self.cfg["mic_muted"] = muted
        self._update_mic_action()

    def _update_mic_action(self):
        """Refresh the MIC toolbar action appearance to reflect current state."""
        no_mic = self.cfg.get("mic_index", None) is None
        if no_mic:
            self._mic_action.setEnabled(False)
            self._mic_action.setChecked(False)
            self._mic_action.setToolTip(
                "No microphone configured — open Audio Settings to select one"
            )
        else:
            self._mic_action.setEnabled(True)
            muted = self.mic.muted
            self._mic_action.setChecked(muted)
            self._mic_action.setText(
                "\U0001f3a4  MIC OFF" if muted else "\U0001f3a4  MIC"
            )
            self._mic_action.setToolTip(
                "Microphone muted — click to unmute" if muted
                else "Microphone active — click to mute"
            )

    def _reset_image(self):
        if self.vthread:
            self.vthread.set_image(1.0, 1.0, 1.0)

    # ── RECORDING ─────────────────────────────────────────────────────────────
    def toggle_recording(self):
        if self.recorder.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if not self.running:
            QMessageBox.warning(self, "Recording", "Start stream first.")
            return
        with self._frame_lock:
            frame = self._raw_frame
        if frame is None:
            return
        h, w = frame.shape[:2]
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fmt = self.cfg.get("recording_format", "mp4")
        path = os.path.join(self.cfg["recording_path"], f"rec_{ts}.{fmt}")

        include_audio = self.cfg.get("recording_include_audio", True)

        self.recorder.start(
            path, w, h,
            fps=self.cfg.get("fps", 60),
            include_audio=include_audio,
            audio_input_index=self.cfg.get("audio_input_index"),
            sample_rate=self.cfg.get("audio_sample_rate", 48000),
            audio_codec=self.cfg.get("recording_audio_codec", "aac"),
            audio_bitrate=self.cfg.get("recording_audio_bitrate", 320),
        )

        if include_audio and self.audio is not None:
            self.audio.set_recorder(self.recorder)
        if include_audio:
            self.mic.set_recorder(self.recorder)

        self.rec_pill.set_state("\u23fa REC", C["record"])
        self.rec_pill.show()
        self._rec_start_time = time.time()
        self._rec_timer.start()

    def stop_recording(self):
        if self.audio is not None:
            self.audio.set_recorder(None)
        self.mic.set_recorder(None)
        path = self.recorder.stop()
        self.rec_pill.hide()
        self._rec_timer.stop()
        self._rec_start_time = None
        self._update_rec_duration()
        if path:
            QTimer.singleShot(
                100,
                lambda: QMessageBox.information(
                    self, "Saved", f"Recording saved:\n{path}"
                ),
            )

    def save_clip(self):
        if not self.running:
            QMessageBox.warning(self, "Clip", "Start stream first.")
            return
        if not self.cfg.get("clip_buffer_enabled", False):
            QMessageBox.information(
                self, "Clip Buffer Disabled",
                "Clip buffer is disabled — enable it in Recording Settings\n"
                "(Tools \u2192 Recording Settings\u2026 \u2192 Clip Buffer section).\n\n"
                "The buffer uses JPEG-compressed RAM to store recent footage."
            )
            return
        with self._frame_lock:
            frame = self._raw_frame
        if frame is None:
            return
        h, w = frame.shape[:2]
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        clip_dir = self.cfg.get("clip_path", self.cfg.get("recording_path", ""))
        path = os.path.join(clip_dir, f"clip_{ts}.mp4")
        os.makedirs(clip_dir, exist_ok=True)
        self._notify("\U0001f4be Saving clip\u2026", C["clip"])
        self._clip_worker = ClipSaveWorker(self.clip_buf, path, w, h)
        self._clip_worker.finished.connect(self._on_clip_saved)
        self._clip_worker.finished.connect(self._clip_worker.deleteLater)
        self._clip_worker.start()

    def _on_clip_saved(self, result):
        name = os.path.basename(result) if result else "Empty buffer"
        self._notify(f"\U0001f4be Saved: {name}", C["clip"])
        QTimer.singleShot(4000, lambda: self._notify("", C["subtext"]))

    def take_screenshot(self):
        with self._frame_lock:
            frame = self._raw_frame
        if frame is None:
            QMessageBox.warning(self, "Screenshot", "No frame \u2014 start stream first.")
            return
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
        sfmt = self.cfg.get("screenshot_format", "png")
        ext = {"png": "png", "jpeg": "jpg", "webp": "webp"}.get(sfmt, "png")
        path = os.path.join(self.cfg["screenshot_path"], f"capture_{ts}.{ext}")
        os.makedirs(self.cfg["screenshot_path"], exist_ok=True)
        if sfmt == "jpeg":
            q = self.cfg.get("screenshot_jpeg_quality", 92)
            ok = cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, q])
        elif sfmt == "webp":
            ok = cv2.imwrite(path, frame, [cv2.IMWRITE_WEBP_QUALITY, 90])
        else:
            ok = cv2.imwrite(path, frame)
        if not ok:
            QMessageBox.warning(self, "Screenshot", f"Failed to write screenshot:\n{path}")
            return
        name = os.path.basename(path)
        self._notify(f"\U0001f4f7 {name}", C["screenshot"])
        QTimer.singleShot(4000, lambda: self._notify("", C["subtext"]))
        # White flash effect
        self.flash.setStyleSheet("background:rgba(255,255,255,200);")
        self.flash.setGeometry(self.video.rect())
        self.flash.show()
        QTimer.singleShot(80, lambda: self.flash.setStyleSheet("background:rgba(200,200,200,100);"))
        QTimer.singleShot(160, self.flash.hide)

    def _notify(self, text, color):
        """Update the status bar notification area."""
        self.notify_lbl.setText(f"  {text}  " if text else "")
        self.notify_lbl.setStyleSheet(f"color:{color};font-size:9pt;")

    # ── MISC ACTIONS ──────────────────────────────────────────────────────────
    def _toggle_overlay(self):
        on = self.video.toggle_overlay()
        self._overlay_action.setChecked(on)
        # Only poll system stats when the overlay is actually visible
        if on:
            self.sys_stats.resume()
        else:
            self.sys_stats.pause()
            self._sys_data = {}

    def _toggle_ar_lock(self):
        self.video._ar_lock = self._ar_action.isChecked()
        self.cfg["aspect_ratio_lock"] = self.video._ar_lock

    def _set_resolution(self, val):
        self.cfg["resolution"] = val
        for v, a in self._res_actions.items():
            a.setChecked(v == val)

    def _set_fps(self, fps):
        self.cfg["fps"] = fps
        for f, a in self._fps_actions.items():
            a.setChecked(f == fps)

    def _toggle_aot(self):
        on = self._aot_action.isChecked()
        self.cfg["always_on_top"] = on
        flags = self.windowFlags()
        if on:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _open_folder(self, path):
        os.makedirs(path, exist_ok=True)
        os.startfile(path)

    def _open_audio(self):
        AudioDialog(self, self.cfg, self.audio, self.mic).exec()

    def _open_image(self):
        ImageDialog(self, self.vthread, self.cfg).exec()

    def _open_upscale(self):
        dlg = UpscaleDialog(self, self.cfg)
        if dlg.exec():
            self.cfg["upscale_mode"] = dlg.mode

    def _open_recording(self):
        dlg = RecordingDialog(self, self.cfg)
        if dlg.exec():
            self.clip_buf.update(
                self.cfg.get("clip_duration", 15),
                self.cfg.get("fps", 60),
                jpeg_quality=self.cfg.get("clip_buffer_jpeg_quality", 85),
            )
            self.video.set_render_fps(self.cfg.get("preview_fps_cap", 30))
            self._update_clip_action()

    def _open_devices(self):
        DeviceDialog(self, self.cfg).exec()

    def _open_hotkeys(self):
        HotkeyDialog(self, self.cfg).exec()

    def _show_about(self):
        show_about(self)

    def closeEvent(self, event):
        # Unregister keyboard library hooks first so the low-level hook is
        # released before any other teardown runs.
        self._global_hk.unregister_all()
        self.cfg["geometry"] = bytes(self.saveGeometry().toHex()).decode("ascii")
        save_config(self.cfg)
        self.stop_stream()
        self.sys_stats.stop()
        event.accept()
