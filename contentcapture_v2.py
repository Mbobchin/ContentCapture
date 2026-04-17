"""
ContentCapture v2.0.0
Native Windows — PySide6 + MSMF + WASAPI
No WSL, no usbipd, no PulseAudio.
"""
import sys, os, cv2, time, threading, collections, json, subprocess
import queue, wave
import numpy as np
import sounddevice as sd
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QSlider, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QDialog, QRadioButton, QButtonGroup,
    QGroupBox, QGridLayout, QSizePolicy, QSpinBox, QLineEdit,
    QFrame, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QScrollArea, QToolBar, QStatusBar, QDockWidget, QFormLayout,
    QDoubleSpinBox, QAbstractItemView, QMenu, QSplitter, QStackedWidget,
    QKeySequenceEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve,
    QRect, QPoint, QSize, QRectF, QObject
)
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen,
    QAction, QKeySequence, QShortcut, QBrush, QFontMetrics,
    QPainterPath, QCursor
)

APP_NAME    = "ContentCapture"
APP_VERSION = "2.0.0"
APP_TAGLINE = "Capture card viewer for Windows with GPU acceleration"
CONFIG_FILE = os.path.join(os.environ.get("APPDATA",""), "ContentCapture", "config.json")

# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
C = {
    # Layered backgrounds — deep navy/charcoal
    "bg":           "#0d0d1e",
    "bg2":          "#0f0f22",
    "panel":        "#12122a",
    "panel2":       "#171730",
    "panel3":       "#1c1c38",
    "card":         "#191932",
    # Borders
    "border":       "#22224a",
    "border2":      "#2e2e58",
    # Accent — cyan/blue brand colour
    "accent":       "#00d4ff",
    "accent2":      "#0099cc",
    "accent_dim":   "#0099cc",
    "accent_glow":  "#00d4ff33",
    # State indicators
    "live":         "#00e676",
    "danger":       "#f5284a",
    "warning":      "#ffb300",
    "record":       "#f5284a",
    "clip":         "#ff9f43",
    "screenshot":   "#c44dff",
    "good":         "#00e676",
    "warn":         "#ffb300",
    "bad":          "#f5284a",
    # Typography
    "text":         "#e8e8f4",
    "text2":        "#9898c0",
    "subtext":      "#484870",
    # Interactive surfaces
    "hover":        "#1e1e42",
    "hover2":       "#26264e",
    "selected":     "#00d4ff1a",
    # Toolbar / dock
    "toolbar":      "#0f0f28",
    "statusbar":    "#0a0a1a",
}

# ── STYLESHEET ────────────────────────────────────────────────────────────────
STYLESHEET = f"""
/* ── Base ── */
QMainWindow, QDialog, QWidget {{
    background: {C["bg"]};
    color: {C["text"]};
    font-family: 'Segoe UI';
    font-size: 10pt;
}}

/* ── Menu Bar ── */
QMenuBar {{
    background: {C["panel"]};
    color: {C["text"]};
    border-bottom: 1px solid {C["border"]};
    padding: 1px 6px;
    spacing: 2px;
    font-size: 10pt;
}}
QMenuBar::item {{
    padding: 5px 12px;
    border-radius: 6px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {C["hover2"]};
    color: {C["accent"]};
}}
QMenuBar::item:pressed {{
    background: {C["hover2"]};
    color: {C["accent"]};
}}

/* ── Menus ── */
QMenu {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 8px;
    padding: 6px 4px;
    font-size: 10pt;
}}
QMenu::item {{
    padding: 7px 32px 7px 16px;
    border-radius: 6px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background: {C["hover2"]};
    color: {C["accent"]};
}}
QMenu::item:disabled {{
    color: {C["subtext"]};
}}
QMenu::separator {{
    height: 1px;
    background: {C["border"]};
    margin: 5px 12px;
}}
QMenu::indicator {{
    width: 16px;
    height: 16px;
    left: 6px;
}}

/* ── Toolbar ── */
QToolBar {{
    background: {C["toolbar"]};
    border: none;
    border-bottom: 1px solid {C["border"]};
    padding: 3px 6px;
    spacing: 3px;
}}
QToolBar::separator {{
    background: {C["border2"]};
    width: 1px;
    margin: 5px 6px;
}}
QToolButton {{
    background: transparent;
    color: {C["text"]};
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 9pt;
    font-weight: 600;
    min-width: 52px;
}}
QToolButton:hover {{
    background: {C["hover2"]};
    border-color: {C["border2"]};
    color: {C["accent"]};
}}
QToolButton:pressed {{
    background: {C["panel"]};
    border-color: {C["accent2"]};
    color: {C["accent"]};
}}
QToolButton:checked {{
    background: {C["selected"]};
    border-color: {C["accent"]};
    color: {C["accent"]};
}}
QToolButton:disabled {{
    color: {C["subtext"]};
    background: transparent;
}}

/* ── Buttons ── */
QPushButton {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 8px;
    padding: 7px 20px;
    font-size: 10pt;
}}
QPushButton:hover {{
    background: {C["hover2"]};
    border-color: {C["accent"]};
    color: {C["accent"]};
}}
QPushButton:pressed {{
    background: {C["panel"]};
    border-color: {C["accent2"]};
    color: {C["accent2"]};
}}
QPushButton:focus {{
    border-color: {C["accent"]};
    outline: none;
}}
QPushButton:disabled {{
    background: {C["panel"]};
    color: {C["subtext"]};
    border-color: {C["border"]};
}}
QPushButton#accent {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {C["accent"]}, stop:1 {C["accent2"]});
    color: #000c14;
    border: none;
    font-weight: bold;
    font-size: 10pt;
}}
QPushButton#accent:hover {{
    background: {C["accent"]};
    color: #000;
}}
QPushButton#accent:pressed {{
    background: {C["accent2"]};
    color: #000;
}}
QPushButton#accent:disabled {{
    background: {C["border"]};
    color: {C["subtext"]};
}}
QPushButton#danger {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #f53050, stop:1 #c01030);
    color: #fff;
    border: none;
    font-weight: bold;
}}
QPushButton#danger:hover {{
    background: {C["danger"]};
}}
QPushButton#danger:pressed {{
    background: #a00020;
}}

/* ── Sliders ── */
QSlider {{ min-height: 26px; }}
QSlider::groove:horizontal {{
    height: 5px;
    background: {C["border"]};
    border-radius: 3px;
    margin: 0 4px;
}}
QSlider::handle:horizontal {{
    background: {C["accent"]};
    width: 18px;
    height: 18px;
    margin: -7px -4px;
    border-radius: 9px;
    border: 2px solid {C["bg"]};
}}
QSlider::handle:horizontal:hover {{
    background: #40e8ff;
    border-color: {C["accent"]};
}}
QSlider::handle:horizontal:focus {{
    border-color: #fff;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {C["accent2"]}, stop:1 {C["accent"]});
    border-radius: 3px;
}}
QSlider::groove:horizontal:disabled {{
    background: {C["border"]};
}}
QSlider::handle:horizontal:disabled {{
    background: {C["subtext"]};
}}

/* ── ComboBox ── */
QComboBox {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    padding: 6px 12px;
    min-height: 30px;
    font-size: 10pt;
}}
QComboBox:hover {{ border-color: {C["accent"]}; }}
QComboBox:focus {{ border-color: {C["accent"]}; background: {C["panel3"]}; outline: none; }}
QComboBox:disabled {{ color: {C["subtext"]}; border-color: {C["border"]}; }}
QComboBox::drop-down {{
    border: none;
    width: 28px;
    border-left: 1px solid {C["border"]};
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 10px; height: 10px;
}}
QComboBox QAbstractItemView {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    selection-background-color: {C["hover2"]};
    selection-color: {C["accent"]};
    padding: 4px;
    outline: none;
}}

/* ── CheckBox / RadioButton ── */
QCheckBox {{
    color: {C["text"]};
    spacing: 10px;
    padding: 4px 0;
    font-size: 10pt;
}}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 2px solid {C["border2"]};
    border-radius: 5px;
    background: {C["panel2"]};
}}
QCheckBox::indicator:hover {{ border-color: {C["accent"]}; }}
QCheckBox::indicator:focus {{ border-color: {C["accent"]}; }}
QCheckBox::indicator:checked {{
    background: {C["accent"]};
    border-color: {C["accent"]};
}}
QCheckBox::indicator:checked:hover {{ background: #40e8ff; }}
QRadioButton {{
    color: {C["text"]};
    spacing: 10px;
    padding: 4px 0;
    font-size: 10pt;
}}
QRadioButton::indicator {{
    width: 17px; height: 17px;
    border: 2px solid {C["border2"]};
    border-radius: 9px;
    background: {C["panel2"]};
}}
QRadioButton::indicator:hover {{ border-color: {C["accent"]}; }}
QRadioButton::indicator:checked {{
    background: {C["accent"]};
    border-color: {C["accent"]};
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {C["border"]};
    border-radius: 10px;
    margin-top: 16px;
    padding: 12px 10px 10px 10px;
    background: {C["card"]};
    color: {C["accent"]};
    font-weight: bold;
    font-size: 9pt;
    letter-spacing: 0.5px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: -1px;
    padding: 1px 8px;
    background: {C["card"]};
    border-radius: 4px;
}}

/* ── Labels ── */
QLabel {{
    color: {C["text"]};
    background: transparent;
    font-size: 10pt;
}}

/* ── LineEdit ── */
QLineEdit {{
    background: {C["panel2"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    padding: 7px 12px;
    color: {C["text"]};
    selection-background-color: {C["accent2"]};
    font-size: 10pt;
    min-height: 30px;
}}
QLineEdit:focus {{ border-color: {C["accent"]}; background: {C["panel3"]}; outline: none; }}
QLineEdit:disabled {{ color: {C["subtext"]}; border-color: {C["border"]}; }}

/* ── SpinBox / DoubleSpinBox ── */
QSpinBox, QDoubleSpinBox {{
    background: {C["panel2"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    padding: 6px 10px;
    color: {C["text"]};
    min-height: 30px;
    font-size: 10pt;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {C["accent"]}; outline: none; }}
QSpinBox:disabled, QDoubleSpinBox:disabled {{ color: {C["subtext"]}; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 20px;
    border: none;
    background: {C["panel3"]};
    border-radius: 4px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {C["hover2"]};
}}

/* ── ListWidget ── */
QListWidget {{
    background: {C["panel2"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    color: {C["text"]};
    padding: 4px;
    outline: none;
}}
QListWidget::item {{ padding: 6px 10px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {C["hover2"]}; color: {C["accent"]}; }}
QListWidget::item:hover {{ background: {C["hover"]}; }}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {C["bg2"]};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["border2"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C["accent2"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {C["bg2"]};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {C["border2"]};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {C["accent2"]}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Dock Widget ── */
QDockWidget {{
    color: {C["text"]};
    font-size: 10pt;
    font-weight: bold;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background: {C["panel2"]};
    padding: 6px 12px;
    border-bottom: 1px solid {C["border"]};
    text-align: left;
}}
QDockWidget::close-button, QDockWidget::float-button {{
    background: transparent;
    border: none;
    padding: 2px;
    border-radius: 4px;
}}
QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background: {C["hover2"]};
}}

/* ── Status Bar ── */
QStatusBar {{
    background: {C["statusbar"]};
    color: {C["text2"]};
    border-top: 1px solid {C["border"]};
    padding: 0 8px;
    font-size: 9pt;
}}
QStatusBar::item {{
    border: none;
}}
QStatusBar QLabel {{
    color: {C["text2"]};
    font-size: 9pt;
    padding: 0 6px;
    background: transparent;
}}

/* ── Frame separators ── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {C["border2"]};
}}

/* ── Tooltip ── */
QToolTip {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["accent2"]};
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 9pt;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {C["border"]};
}}
QSplitter::handle:horizontal {{
    width: 3px;
    border-radius: 2px;
}}
QSplitter::handle:hover {{
    background: {C["accent2"]};
}}
"""

# ── RAM AUTO-DETECT ───────────────────────────────────────────────────────────
def get_available_ram_gb():
    try:
        import psutil
        return psutil.virtual_memory().total / (1024**3)
    except Exception:
        return 16.0

def get_recommended_settings():
    ram = get_available_ram_gb()
    print(f"[RAM] Detected {ram:.1f}GB total RAM")
    if ram < 12:
        print("[RAM] Low memory mode — 720p default, 10s clip buffer")
        return {"clip_duration":10,"resolution":"1280x720"}
    elif ram < 20:
        print("[RAM] Standard memory mode — 1080p, 20s clip buffer")
        return {"clip_duration":20,"resolution":"1920x1080"}
    else:
        print("[RAM] High memory mode — 1080p, 30s clip buffer")
        return {"clip_duration":30,"resolution":"1920x1080"}

# ── FFMPEG DETECTION ─────────────────────────────────────────────────────────
def _find_ffmpeg():
    """Return path to ffmpeg executable, or None if not found."""
    bundled = r"C:/ContentCapture_v2/bin/ffmpeg.exe"
    if os.path.isfile(bundled):
        print(f"[FFmpeg] Found bundled: {bundled}")
        return bundled
    # Fall back to PATH
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("[FFmpeg] Found on PATH")
            return "ffmpeg"
    except Exception:
        pass
    print("[FFmpeg] Not found — audio will not be included in recordings")
    return None

FFMPEG_PATH = _find_ffmpeg()

DEFAULT_CONFIG = {
    "video_index":0,"audio_input_index":3,"audio_output_index":None,
    "resolution":"1920x1080","fps":60,"volume":1.0,"muted":False,
    "upscale_mode":"none","sharpen":False,"deinterlace":False,
    "screenshot_path":os.path.join(os.environ.get("USERPROFILE","~"),"Pictures","ContentCapture"),
    "recording_path":os.path.join(os.environ.get("USERPROFILE","~"),"Videos","ContentCapture"),
    "clip_path":os.path.join(os.environ.get("USERPROFILE","~"),"Videos","ContentCapture","Clips"),
    "clip_duration":30,"recording_format":"mp4",
    "screenshot_format":"png","screenshot_jpeg_quality":92,
    "always_on_top":False,"auto_start":True,"geometry":None,"aspect_ratio_lock":True,
    "brightness":1.0,"contrast":1.0,"saturation":1.0,
    "audio_sample_rate":48000,
    "audio_delay_ms":0,
    "hotkeys":{},
    "global_hotkeys_enabled": False,
    "global_hotkey_actions": [],
    # Audio recording settings
    "recording_include_audio": True,
    "recording_audio_codec": "aac",
    "recording_audio_bitrate": 320,
}

def load_config():
    cfg = dict(DEFAULT_CONFIG)
    first_run = not os.path.exists(CONFIG_FILE)
    try:
        if not first_run:
            with open(CONFIG_FILE) as f: cfg.update(json.load(f))
    except Exception: pass
    if first_run:
        rec = get_recommended_settings()
        cfg.update(rec)
    return cfg

def save_config(cfg):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=2)
    except Exception as e: print(f"[Config] {e}")

# ── CUDA ──────────────────────────────────────────────────────────────────────
def check_cuda():
    try:
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            print("[CUDA] Available via OpenCV ✓"); return True
    except Exception: pass
    try:
        import torch
        if torch.cuda.is_available():
            print(f"[CUDA] Available via PyTorch ✓ ({torch.cuda.get_device_name(0)})")
            torch.cuda.empty_cache()
            return True
    except Exception: pass
    print("[CUDA] Not available — CPU fallback"); return False

CUDA_AVAILABLE = check_cuda()

# Precomputed sharpen kernel — avoids reallocating a NumPy array every frame.
_SHARPEN_KERNEL = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]], dtype=np.float32)

# Cache PyTorch CUDA availability once at startup so we don't query it per frame.
try:
    import torch as _torch_mod
    _TORCH_CUDA = _torch_mod.cuda.is_available()
except Exception:
    _torch_mod = None
    _TORCH_CUDA = False

def cuda_resize(frame, tw, th):
    try:
        import torch, torch.nn.functional as F
        t = torch.from_numpy(frame).permute(2,0,1).unsqueeze(0).float().mul_(1.0/255.0)
        if _TORCH_CUDA: t = t.cuda(non_blocking=True)
        out = F.interpolate(t,size=(th,tw),mode="bilinear",align_corners=False)
        out = out.squeeze(0).permute(1,2,0).mul_(255.0).clamp_(0,255).byte().cpu().numpy()
        return out
    except Exception:
        return cv2.resize(frame,(tw,th),interpolation=cv2.INTER_LINEAR)

def upscale_frame(frame, mode, tw, th):
    t0 = time.perf_counter()
    if mode == "cuda" and CUDA_AVAILABLE:
        try:
            gpu = cv2.cuda_GpuMat(); gpu.upload(frame)
            r = cv2.cuda.resize(gpu,(tw,th),interpolation=cv2.INTER_LANCZOS4)
            return r.download(),(time.perf_counter()-t0)*1000
        except Exception: pass
        try:
            return cuda_resize(frame,tw,th),(time.perf_counter()-t0)*1000
        except Exception: pass
    return cv2.resize(frame,(tw,th),interpolation=cv2.INTER_LINEAR),(time.perf_counter()-t0)*1000

def apply_filters(frame, sharpen, deinterlace):
    if deinterlace:
        frame = frame.copy()
        frame[1::2] = frame[::2]
    if sharpen:
        frame = cv2.filter2D(frame, -1, _SHARPEN_KERNEL)
    return frame

# ── DEVICE DETECT ─────────────────────────────────────────────────────────────
def find_video_devices():
    devs=[]
    for i in range(8):
        cap=cv2.VideoCapture(i,cv2.CAP_MSMF)
        if cap.isOpened():
            w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            devs.append((i,f"Device {i} ({w}x{h})")); cap.release()
    return devs

def find_audio_devices():
    devs=[]
    try:
        for i,d in enumerate(sd.query_devices()):
            if d["max_input_channels"]>0: devs.append((i,d["name"]))
    except Exception: pass
    return devs

# ── PERF TRACKER ──────────────────────────────────────────────────────────────
class PerfTracker:
    W=60
    def __init__(self):
        self.ct=collections.deque(maxlen=self.W); self.rt=collections.deque(maxlen=self.W)
        self.gt=collections.deque(maxlen=self.W); self.fg=collections.deque(maxlen=self.W)
        self.dropped=self.total=0; self._last=None; self._lock=threading.Lock()
    def rc(self,ms):
        with self._lock:
            self.ct.append(ms); self.total+=1
            if self._last: self.fg.append((time.perf_counter()-self._last)*1000)
            self._last=time.perf_counter()
    def rd(self):
        with self._lock: self.dropped+=1; self.total+=1
    def rr(self,ms):
        with self._lock: self.rt.append(ms)
    def rg(self,ms):
        with self._lock: self.gt.append(ms)
    def snapshot(self):
        with self._lock:
            def avg(d): return sum(d)/len(d) if d else 0
            def mx(d): return max(d) if d else 0
            g=list(self.fg)
            gap_avg=avg(g)
            return {"fps":1000/gap_avg if gap_avg>0 else 0,
                    "cap_avg":avg(self.ct),"cap_max":mx(self.ct),
                    "ren_avg":avg(self.rt),"ren_max":mx(self.rt),
                    "gpu_avg":avg(self.gt),"gap_avg":gap_avg,"gap_max":mx(g),
                    "dropped":self.dropped,"total":self.total,
                    "drop_pct":(self.dropped/self.total*100) if self.total else 0}
    def reset(self):
        with self._lock:
            self.ct.clear(); self.rt.clear(); self.gt.clear(); self.fg.clear()
            self.dropped=self.total=0; self._last=None

# ── SYSTEM STATS ──────────────────────────────────────────────────────────────
class SystemStats(QThread):
    updated=Signal(dict)
    def __init__(self):
        super().__init__(); self._stop=threading.Event()
    def run(self):
        while not self._stop.is_set():
            d={}
            try:
                import psutil
                d["cpu_pct"]=psutil.cpu_percent(interval=0.5)
                vm=psutil.virtual_memory()
                d["mem_used_mb"]=vm.used//(1024*1024)
                d["mem_total_mb"]=vm.total//(1024*1024)
                d["mem_pct"]=vm.percent
            except Exception: pass
            try:
                r=subprocess.run(
                    ["nvidia-smi","--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True,text=True,timeout=2)
                if r.returncode==0 and r.stdout.strip():
                    p=[x.strip() for x in r.stdout.strip().split(",")]
                    if len(p)>=5:
                        d["gpu_name"]=p[0]; d["gpu_util"]=float(p[1])
                        d["gpu_mem_used"]=int(p[2]); d["gpu_mem_total"]=int(p[3])
                        d["gpu_temp"]=int(p[4])
            except Exception: pass
            self.updated.emit(d); self._stop.wait(1.0)
    def stop(self): self._stop.set()

# ── VIDEO THREAD ──────────────────────────────────────────────────────────────
class VideoThread(QThread):
    frame_ready=Signal(np.ndarray)
    error=Signal(str)
    def __init__(self,cfg,perf):
        super().__init__(); self.cfg=cfg; self.perf=perf
        self._stop=threading.Event(); self._lock=threading.Lock()
        self._b=self._c=self._s=1.0
    def set_image(self,b,c,s):
        with self._lock: self._b=b; self._c=c; self._s=s
    def run(self):
        idx=self.cfg.get("video_index",0)
        cap=cv2.VideoCapture(idx,cv2.CAP_MSMF)
        if not cap.isOpened():
            self.error.emit(f"Could not open video device {idx}.\nCheck Settings → Device Settings."); return
        try:
            res=self.cfg.get("resolution","1920x1080").split("x")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,int(res[0]))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,int(res[1]))
        except (IndexError,ValueError) as e:
            print(f"[VideoThread] Invalid resolution in config ({e}), using device default")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
        cap.set(cv2.CAP_PROP_FPS,self.cfg.get("fps",60))
        sharpen=self.cfg.get("sharpen",False); deinterlace=self.cfg.get("deinterlace",False)
        while not self._stop.is_set():
            t0=time.perf_counter(); ret,frame=cap.read()
            if not ret: self.perf.rd(); continue
            self.perf.rc((time.perf_counter()-t0)*1000)
            with self._lock: b,c,s=self._b,self._c,self._s
            if b!=1.0 or c!=1.0: frame=cv2.convertScaleAbs(frame,alpha=c,beta=(b-1.0)*128)
            if s!=1.0:
                hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV).astype(np.float32)
                np.multiply(hsv[:,:,1], s, out=hsv[:,:,1])
                np.clip(hsv[:,:,1], 0, 255, out=hsv[:,:,1])
                frame=cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2BGR)
            frame=apply_filters(frame,sharpen,deinterlace)
            self.frame_ready.emit(frame)
        cap.release()
    def stop(self): self._stop.set(); self.wait(3000)

# ── AUDIO ENGINE ──────────────────────────────────────────────────────────────
class AudioEngine:
    def __init__(self,input_idx,output_idx=None,sample_rate=48000):
        self.input_idx=input_idx; self.output_idx=output_idx
        self.sample_rate=sample_rate
        self.volume=1.0; self.muted=False; self._stream=None; self._lock=threading.Lock()
        self._audio_buf=None
        # AV sync delay line
        self._delay_ms=0
        self._delay_buf=collections.deque()
        self._samples_to_skip=0

    def set_delay(self, ms: int):
        """Set the AV sync offset in milliseconds.
        Positive = delay audio (video is ahead); negative = skip audio ahead.
        Safe to call from the UI thread at any time.
        """
        self._delay_ms = int(ms)
        # Reset delay state; the callback reads these atomically enough
        # because Python int assignment is atomic at the GIL level.
        self._delay_buf.clear()
        sr = self.sample_rate
        samples = int(abs(self._delay_ms) / 1000.0 * sr)
        self._samples_to_skip = samples if self._delay_ms < 0 else 0

    def start(self, delay_ms: int = 0):
        # Initialise delay state from the parameter
        self._delay_ms = int(delay_ms)
        self._delay_buf.clear()
        sr = self.sample_rate
        samples = int(abs(self._delay_ms) / 1000.0 * sr)
        self._samples_to_skip = samples if self._delay_ms < 0 else 0

        engine = self

        def callback(indata, outdata, frames, time_info, status):
            # ── Volume / mute pre-process into a scratch buffer ───────────────
            if engine._audio_buf is None or engine._audio_buf.shape != outdata.shape:
                engine._audio_buf = np.empty_like(outdata)
            with engine._lock:
                muted  = engine.muted
                volume = engine.volume

            if muted:
                outdata[:] = 0
                return

            np.multiply(indata, volume, out=engine._audio_buf)
            np.clip(engine._audio_buf, -1.0, 1.0, out=engine._audio_buf)
            processed = engine._audio_buf  # shape (frames, channels)

            delay_ms = engine._delay_ms  # snapshot — primitive read, GIL-safe

            # ── Pass-through (no delay) ───────────────────────────────────────
            if delay_ms == 0:
                outdata[:] = processed
                return

            # ── Positive delay: buffer incoming, output silence until full ────
            if delay_ms > 0:
                target_samples = int(delay_ms / 1000.0 * sr)
                engine._delay_buf.append(processed.copy())
                buffered = sum(len(c) for c in engine._delay_buf)
                if buffered < target_samples:
                    outdata[:] = 0
                else:
                    # Drain enough frames to fill outdata
                    remaining = frames
                    out_pos = 0
                    while remaining > 0 and engine._delay_buf:
                        chunk = engine._delay_buf[0]
                        available = len(chunk)
                        take = min(available, remaining)
                        outdata[out_pos:out_pos + take] = chunk[:take]
                        out_pos += take
                        remaining -= take
                        if take == available:
                            engine._delay_buf.popleft()
                        else:
                            # Put the remainder back as the new head
                            engine._delay_buf[0] = chunk[take:]
                    if remaining > 0:
                        outdata[out_pos:] = 0
                return

            # ── Negative delay: skip ahead by discarding samples ──────────────
            # delay_ms < 0
            if engine._samples_to_skip > 0:
                skip = min(engine._samples_to_skip, frames)
                engine._samples_to_skip -= skip
                if skip < frames:
                    outdata[:frames - skip] = processed[skip:]
                    outdata[frames - skip:] = 0
                else:
                    outdata[:] = 0
            else:
                outdata[:] = processed

        for in_dev,out_dev in [(self.input_idx,self.output_idx),(self.input_idx,None),(None,None)]:
            try:
                di=sd.query_devices(in_dev if in_dev is not None else sd.default.device[0])
                ch=min(2,int(di["max_input_channels"]))
                self._stream=sd.Stream(samplerate=sr,channels=ch,dtype="float32",
                                       device=(in_dev,out_dev),callback=callback,blocksize=2048)
                self._stream.start()
                print(f"[Audio] Started — input:{in_dev} output:{out_dev} channels:{ch} rate:{sr}"); return
            except Exception as e: print(f"[Audio] Attempt failed (in:{in_dev} out:{out_dev}): {e}")
        print("[Audio] All attempts failed — running without audio")
    def stop(self):
        if self._stream:
            try: self._stream.stop(); self._stream.close()
            except Exception: pass
            self._stream=None
    def set_volume(self,v):
        with self._lock: self.volume=float(v)
    def toggle_mute(self):
        with self._lock:
            self.muted=not self.muted
            result=self.muted
        return result

# ── AUDIO RECORDER ───────────────────────────────────────────────────────────
class AudioRecorder:
    """
    Captures raw PCM float32 from a sounddevice InputStream and writes it to
    a temporary WAV file (int16 PCM) for later muxing by VideoRecorder.

    Usage:
        rec = AudioRecorder(cfg)
        rec.start("/tmp/audio_123.wav")
        ...
        rec.stop()   # flushes remaining audio and closes the file
    """

    def __init__(self, cfg):
        self._cfg = cfg
        self._stream = None
        self._q: queue.Queue = queue.Queue()
        self._thread = None
        self._wav_path = None
        self._wav_file = None
        self._channels = 1
        self._sample_rate = 48000
        self._stop_event = threading.Event()
        self._recording = False

    # ── internal writer thread ────────────────────────────────────────────────
    def _writer_loop(self):
        """Drain the queue and write int16 PCM chunks to the WAV file."""
        while not self._stop_event.is_set() or not self._q.empty():
            try:
                chunk = self._q.get(timeout=0.05)
                self._write_chunk(chunk)
            except queue.Empty:
                continue
        # Final flush — drain anything that arrived between stop_event.set() and here
        while not self._q.empty():
            try:
                chunk = self._q.get_nowait()
                self._write_chunk(chunk)
            except queue.Empty:
                break
        if self._wav_file:
            try:
                self._wav_file.close()
            except Exception:
                pass
            self._wav_file = None

    def _write_chunk(self, data: np.ndarray):
        """Convert float32 ndarray to int16 and append to WAV file."""
        if self._wav_file is None:
            return
        try:
            clipped = np.clip(data, -1.0, 1.0)
            pcm16 = (clipped * 32767.0).astype(np.int16)
            self._wav_file.writeframes(pcm16.tobytes())
        except Exception as e:
            print(f"[AudioRecorder] write error: {e}")

    # ── sounddevice callback ──────────────────────────────────────────────────
    def _sd_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[AudioRecorder] sounddevice status: {status}")
        if self._recording:
            self._q.put(indata.copy())

    # ── public API ───────────────────────────────────────────────────────────
    def start(self, wav_path: str):
        """Open the input stream and start writing PCM to wav_path."""
        self._wav_path = wav_path
        self._stop_event.clear()
        self._recording = False

        in_idx = self._cfg.get("audio_input_index", 3)
        sr = self._cfg.get("audio_sample_rate", 48000)
        self._sample_rate = sr

        # Determine channel count from device info
        try:
            di = sd.query_devices(in_idx)
            self._channels = min(2, int(di["max_input_channels"]))
        except Exception:
            self._channels = 1

        # Open WAV file before the stream starts so the writer thread is ready
        try:
            os.makedirs(os.path.dirname(wav_path) or ".", exist_ok=True)
            self._wav_file = wave.open(wav_path, "wb")
            self._wav_file.setnchannels(self._channels)
            self._wav_file.setsampwidth(2)           # 16-bit
            self._wav_file.setframerate(sr)
        except Exception as e:
            print(f"[AudioRecorder] Could not open WAV file {wav_path}: {e}")
            self._wav_file = None
            return

        # Start writer daemon thread
        self._thread = threading.Thread(target=self._writer_loop, daemon=True, name="AudioRecorderWriter")
        self._thread.start()

        # Open sounddevice input stream
        try:
            self._stream = sd.InputStream(
                device=in_idx,
                samplerate=sr,
                channels=self._channels,
                dtype="float32",
                blocksize=2048,
                callback=self._sd_callback,
            )
            self._stream.start()
            self._recording = True
            print(f"[AudioRecorder] Started — device:{in_idx} ch:{self._channels} rate:{sr} -> {wav_path}")
        except Exception as e:
            print(f"[AudioRecorder] Failed to open input stream: {e}")
            self._stop_event.set()
            self._recording = False

    def stop(self):
        """Stop the stream, flush remaining audio, and close the WAV file."""
        self._recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        # Signal writer thread to finish flushing
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        print(f"[AudioRecorder] Stopped — WAV: {self._wav_path}")

    @property
    def wav_path(self) -> str:
        return self._wav_path or ""


# ── VIDEO RECORDER ────────────────────────────────────────────────────────────
class VideoRecorder:
    """
    Records video frames to a file.

    If FFMPEG_PATH is set and include_audio=True (with a valid wav_path),
    frames are piped to an ffmpeg subprocess that muxes video + audio into a
    single output file.  Otherwise, falls back to cv2.VideoWriter (silent).
    """

    def __init__(self):
        # cv2 fallback
        self.writer = None
        # ffmpeg pipe mode
        self._ffmpeg_proc = None
        self._wav_path_to_cleanup = None
        # shared state
        self.recording = False
        self.path = None
        self._lock = threading.Lock()
        self._use_ffmpeg = False

    def start(self, path, fps, w, h, fmt="mp4",
              include_audio=False, wav_path=None,
              audio_codec="aac", audio_bitrate=320):
        with self._lock:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            self._use_ffmpeg = False
            self._ffmpeg_proc = None
            self._wav_path_to_cleanup = None
            self.writer = None

            # ── Try ffmpeg pipe mode ──────────────────────────────────────────
            if FFMPEG_PATH and include_audio and wav_path and os.path.isfile(wav_path):
                codec_map = {
                    "aac":  ("aac",  f"{audio_bitrate}k"),
                    "mp3":  ("libmp3lame", f"{audio_bitrate}k"),
                    "pcm":  ("pcm_s16le", None),
                }
                acodec, abitrate = codec_map.get(audio_codec, ("aac", "320k"))

                cmd = [
                    FFMPEG_PATH, "-y",
                    # video from stdin pipe
                    "-f", "rawvideo",
                    "-pix_fmt", "bgr24",
                    "-s", f"{w}x{h}",
                    "-r", str(fps),
                    "-i", "pipe:0",
                    # audio from temp WAV
                    "-i", wav_path,
                    # video codec
                    "-c:v", "libx264",
                    "-crf", "18",
                    "-preset", "fast",
                    # audio codec
                    "-c:a", acodec,
                ]
                if abitrate:
                    cmd += ["-b:a", abitrate]
                cmd += ["-shortest", path]

                try:
                    self._ffmpeg_proc = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self._use_ffmpeg = True
                    self._wav_path_to_cleanup = wav_path
                    self.recording = True
                    self.path = path
                    print(f"[Recorder] ffmpeg pipe mode — {w}x{h}@{fps} + audio ({acodec}) -> {path}")
                    return
                except Exception as e:
                    print(f"[Recorder] ffmpeg launch failed ({e}), falling back to cv2.VideoWriter")
                    self._ffmpeg_proc = None

            # ── cv2 fallback (silent) ─────────────────────────────────────────
            fourcc = cv2.VideoWriter_fourcc(*("mp4v" if fmt == "mp4" else "XVID"))
            self.writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
            if not self.writer.isOpened():
                print(f"[Recorder] VideoWriter failed to open: {path}")
                self.writer = None
                return
            self.recording = True
            self.path = path
            if include_audio and not FFMPEG_PATH:
                print("[Recorder] ffmpeg not found — recording without audio")

    def write(self, frame):
        with self._lock:
            if not self.recording:
                return
            if self._use_ffmpeg and self._ffmpeg_proc:
                try:
                    self._ffmpeg_proc.stdin.write(frame.tobytes())
                except Exception as e:
                    print(f"[Recorder] ffmpeg write error: {e}")
            elif self.writer:
                self.writer.write(frame)

    def stop(self):
        with self._lock:
            self.recording = False
            path = self.path
            self.path = None

            if self._use_ffmpeg and self._ffmpeg_proc:
                try:
                    self._ffmpeg_proc.stdin.close()
                    self._ffmpeg_proc.wait(timeout=30)
                except Exception as e:
                    print(f"[Recorder] ffmpeg finish error: {e}")
                    try: self._ffmpeg_proc.kill()
                    except Exception: pass
                self._ffmpeg_proc = None
                self._use_ffmpeg = False
                # Clean up temp WAV
                if self._wav_path_to_cleanup:
                    try:
                        os.remove(self._wav_path_to_cleanup)
                    except Exception:
                        pass
                    self._wav_path_to_cleanup = None
            elif self.writer:
                self.writer.release()
                self.writer = None

            return path

# ── CLIP BUFFER ───────────────────────────────────────────────────────────────
class ClipBuffer:
    def __init__(self,dur=30,fps=60):
        self._buf=collections.deque(maxlen=dur*fps); self._fps=fps; self._lock=threading.Lock()
    def push(self,f):
        with self._lock: self._buf.append(f.copy())
    def save(self,path,w,h):
        with self._lock: frames=list(self._buf); fps=self._fps
        if not frames: return None
        parent=os.path.dirname(path)
        if parent:
            os.makedirs(parent,exist_ok=True)
        wr=cv2.VideoWriter(path,cv2.VideoWriter_fourcc(*"mp4v"),fps,(w,h))
        if not wr.isOpened():
            print(f"[ClipBuffer] VideoWriter failed to open: {path}")
            return None
        for f in frames: wr.write(cv2.resize(f,(w,h)))
        wr.release(); return path
    def update(self,dur,fps):
        with self._lock:
            self._fps=fps
            self._buf=collections.deque(self._buf,maxlen=dur*fps)

class ClipSaveWorker(QThread):
    finished=Signal(str)
    def __init__(self,clip_buf,path,w,h):
        super().__init__(); self.clip_buf=clip_buf; self.path=path; self.w=w; self.h=h
    def run(self): self.finished.emit(self.clip_buf.save(self.path,self.w,self.h) or "")

# ── VIDEO WIDGET ──────────────────────────────────────────────────────────────
class VideoWidget(QLabel):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640,360)
        self.setStyleSheet("background:#000000;")
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self._px=None; self._lock=threading.Lock()
        self._overlay_on=False; self._ar_lock=True
        self._zoom=1.0; self._offset=[0.0,0.0]; self._drag=None
        self._perf={}; self._sys={}
        self._sfps=self._sdrop=self._sren=self._sgpu=0.0
        self._target_fps=60; self._mode="none"; self._rec_active=False
        self.setMouseTracking(True)

    def set_frame(self,frame,perf,gpu_ms,rec,target_fps,mode,sys_data=None):
        h,w=frame.shape[:2]
        if self._zoom>1.0:
            cw=int(w/self._zoom); ch=int(h/self._zoom)
            x0=max(0,min(w-cw,int(self._offset[0]*(w-cw))))
            y0=max(0,min(h-ch,int(self._offset[1]*(h-ch))))
            frame=frame[y0:y0+ch,x0:x0+cw]; h,w=frame.shape[:2]
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        img=QImage(rgb.data,w,h,w*3,QImage.Format_RGB888).copy()
        del rgb
        with self._lock:
            self._px=QPixmap.fromImage(img)
            self._perf=perf; self._sys=sys_data or {}
            self._rec_active=rec; self._target_fps=target_fps; self._mode=mode
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(),QColor("#000000"))
        with self._lock: px=self._px
        if px is None:
            # ── Empty state — centered placeholder ───────────────────────────
            cw=self.width(); ch=self.height()
            # Subtle grid background
            painter.setOpacity(0.04)
            pen=QPen(QColor(C["accent"])); pen.setWidth(1)
            painter.setPen(pen)
            step=40
            for x in range(0,cw,step): painter.drawLine(x,0,x,ch)
            for y in range(0,ch,step): painter.drawLine(0,y,cw,y)
            painter.setOpacity(1.0)
            # Center box
            bw,bh=440,200
            bx=(cw-bw)//2; by=(ch-bh)//2
            path=QPainterPath()
            path.addRoundedRect(QRectF(bx,by,bw,bh),14,14)
            painter.fillPath(path,QColor(C["panel2"]+"cc"))
            pen2=QPen(QColor(C["border2"])); pen2.setWidth(1)
            painter.setPen(pen2); painter.drawPath(path)
            # Icon
            painter.setFont(QFont("Segoe UI",32))
            painter.setPen(QColor(C["accent"]+"88"))
            painter.drawText(QRect(bx,by+20,bw,60),Qt.AlignCenter,"\u29c6")
            # Title
            painter.setFont(QFont("Segoe UI",15,QFont.Bold))
            painter.setPen(QColor(C["text"]))
            painter.drawText(QRect(bx,by+70,bw,36),Qt.AlignCenter,APP_NAME)
            # Sub
            painter.setFont(QFont("Segoe UI",10))
            painter.setPen(QColor(C["text2"]))
            painter.drawText(QRect(bx,by+108,bw,28),Qt.AlignCenter,"No device connected")
            painter.setFont(QFont("Segoe UI",9))
            painter.setPen(QColor(C["subtext"]))
            painter.drawText(QRect(bx,by+136,bw,24),Qt.AlignCenter,"Press F5 to start  \u2022  Tools \u2192 Device Settings to configure")
            painter.end(); return

        cw=self.width(); ch=self.height()
        sw=px.width(); sh=px.height()
        if self._ar_lock and sw>0 and sh>0:
            src_ar=sw/sh; dst_ar=cw/ch
            if src_ar>dst_ar: dw=cw; dh=int(cw/src_ar)
            else: dh=ch; dw=int(ch*src_ar)
            ox=(cw-dw)//2; oy=(ch-dh)//2
        else:
            dw,dh,ox,oy=cw,ch,0,0
        painter.drawPixmap(ox,oy,dw,dh,px)

        # ── Floating corner HUD overlay ───────────────────────────────────────
        if self._overlay_on and self._perf:
            s=self._perf; sy=self._sys; a=0.15
            self._sfps  =a*s.get("fps",0)     +(1-a)*self._sfps
            self._sdrop =a*s.get("drop_pct",0)+(1-a)*self._sdrop
            self._sren  =a*s.get("ren_avg",0) +(1-a)*self._sren
            self._sgpu  =a*s.get("gpu_avg",0) +(1-a)*self._sgpu
            fps=self._sfps; drop=self._sdrop; ren=self._sren; gpu=self._sgpu
            tfps=self._target_fps; mode=self._mode

            def pcol(v,w,b):
                if v is None: return QColor(C["subtext"])
                return QColor(C["good"]) if v<w else QColor(C["warn"]) if v<b else QColor(C["bad"])

            fc=QColor(C["good"]) if fps>=tfps*0.95 else QColor(C["warn"]) if fps>=tfps*0.75 else QColor(C["bad"])
            dc=QColor(C["good"]) if drop<1 else QColor(C["warn"]) if drop<5 else QColor(C["bad"])
            gpu_tag=" CUDA" if mode=="cuda" and CUDA_AVAILABLE else " CPU"
            rec_tag="  \u23fa" if self._rec_active else ""
            zm_tag=f"  {self._zoom:.1f}x" if self._zoom>1.0 else ""

            cpu=sy.get("cpu_pct"); ram=sy.get("mem_pct")
            gut=sy.get("gpu_util"); gvr=sy.get("gpu_mem_used")
            cpt=sy.get("cpu_temp"); gtp=sy.get("gpu_temp")

            sl=[
                (f"FPS  {fps:5.1f}/{tfps}{rec_tag}", fc),
                (f"DROP {drop:5.1f}%",               dc),
                (f"REND {ren:5.1f}ms{gpu_tag}{zm_tag}", fc),
                (f"GPU  {gpu:5.1f}ms",               fc),
            ]
            yl=[
                (f"CPU  {cpu:.0f}%" if cpu is not None else "CPU  N/A",  pcol(cpu,60,85)),
                (f"RAM  {ram:.0f}%" if ram is not None else "RAM  N/A",  pcol(ram,60,85)),
                (f"GPU% {gut:.0f}%" if gut is not None else "GPU% N/A",  pcol(gut,60,85)),
                (f"VRAM {gvr}MB"    if gvr is not None else "VRAM N/A",  QColor(C["text"])),
                (f"CTMP {cpt}C"     if cpt is not None else "CTMP N/A",  pcol(cpt,70,85)),
                (f"GTMP {gtp}C"     if gtp is not None else "GTMP N/A",  pcol(gtp,70,85)),
            ]

            # Monospace font for consistent column alignment
            font=QFont("Cascadia Code",9,QFont.Bold)
            if not font.exactMatch(): font=QFont("Consolas",9,QFont.Bold)
            painter.setFont(font); fm=painter.fontMetrics()
            lh=fm.height()+4; pad=10
            col_w=max(fm.horizontalAdvance(r[0]) for r in sl+yl)+14
            bw=col_w*2+pad*3; bh=max(len(sl),len(yl))*lh+pad*2+lh+6

            # Position: top-left corner with margin
            hx=ox+10; hy=oy+10

            # Background panel — rounded rect
            painter.setRenderHint(QPainter.Antialiasing)
            bg_path=QPainterPath()
            bg_path.addRoundedRect(QRectF(hx,hy,bw,bh),8,8)
            painter.setOpacity(0.82)
            painter.fillPath(bg_path,QColor("#080810"))
            painter.setOpacity(1.0)
            border_pen=QPen(QColor(C["border2"])); border_pen.setWidth(1)
            painter.setPen(border_pen); painter.drawPath(bg_path)

            # Section headers
            hf=QFont("Segoe UI",8,QFont.Bold); painter.setFont(hf)
            hfm=painter.fontMetrics()
            painter.setPen(QColor(C["accent"]))
            painter.drawText(hx+pad,         hy+pad+hfm.ascent(),"STREAM")
            painter.drawText(hx+pad+col_w,   hy+pad+hfm.ascent(),"SYSTEM")

            # Accent underline for headers
            ul_y=hy+pad+hfm.height()+2
            acc_pen=QPen(QColor(C["accent"]+"66")); acc_pen.setWidth(1)
            painter.setPen(acc_pen)
            painter.drawLine(hx+pad,ul_y,hx+pad+col_w-8,ul_y)
            painter.drawLine(hx+pad+col_w,ul_y,hx+pad+col_w*2-8,ul_y)

            # Data rows
            painter.setFont(font)
            base_y=hy+pad+lh+2
            for i,(line,color) in enumerate(sl):
                y=base_y+i*lh+fm.ascent()
                painter.setPen(QColor(0,0,0,180)); painter.drawText(hx+pad+1,y+1,line)
                painter.setPen(color);             painter.drawText(hx+pad,  y,  line)
            for i,(line,color) in enumerate(yl):
                y=base_y+i*lh+fm.ascent()
                painter.setPen(QColor(0,0,0,180)); painter.drawText(hx+pad+col_w+1,y+1,line)
                painter.setPen(color);             painter.drawText(hx+pad+col_w,  y,  line)

            # ── Diagnostic bar below HUD ──────────────────────────────────────
            issues=[]
            tms=1000/max(tfps,1)
            if fps>0 and fps<tfps*0.75: issues.append(f"\u26a0 Low FPS ({fps:.0f}) — lower res or close other apps")
            if drop>5:                  issues.append(f"\u26a0 {drop:.1f}% drops — USB bandwidth issue")
            if ren>tms*1.5:            issues.append(f"\u26a0 High render {ren:.0f}ms — try CUDA upscaling or 720p")
            if cpu and cpu>85:         issues.append(f"\u26a0 CPU at {cpu:.0f}% — close other apps")
            if ram and ram>85:         issues.append(f"\u26a0 RAM at {ram:.0f}% — reduce clip buffer or lower res")
            if gtp and gtp>85:         issues.append(f"\u26a0 GPU temp {gtp}C — check cooling")

            df=QFont("Segoe UI",8); painter.setFont(df); dfm=painter.fontMetrics()
            msg=issues[0] if issues else "\u2713 Performance healthy"
            msg_col=QColor(C["warn"]) if issues else QColor(C["good"])
            mw=dfm.horizontalAdvance(msg)+18; mh=dfm.height()+8
            diag_y=hy+bh+5
            diag_path=QPainterPath()
            diag_path.addRoundedRect(QRectF(hx,diag_y,mw,mh),6,6)
            painter.setOpacity(0.82)
            painter.fillPath(diag_path,QColor("#080810"))
            painter.setOpacity(1.0)
            painter.setPen(border_pen); painter.drawPath(diag_path)
            painter.setPen(QColor(0,0,0,180))
            painter.drawText(hx+10,diag_y+dfm.ascent()+4+1,msg)
            painter.setPen(msg_col)
            painter.drawText(hx+10,diag_y+dfm.ascent()+4,  msg)

        painter.end()

    def wheelEvent(self,event):
        d=1 if event.angleDelta().y()>0 else -1
        self._zoom=max(1.0,min(8.0,self._zoom*(1.1**d)))
        if self._zoom==1.0: self._offset=[0.0,0.0]
    def _zoom_in(self): self._zoom=max(1.0,min(8.0,self._zoom*1.1))
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton: self._drag=e.position()
    def mouseMoveEvent(self,e):
        if self._drag and e.buttons()&Qt.LeftButton:
            dx=(e.position().x()-self._drag.x())/self.width()
            dy=(e.position().y()-self._drag.y())/self.height()
            self._offset[0]=max(0.0,min(1.0,self._offset[0]-dx))
            self._offset[1]=max(0.0,min(1.0,self._offset[1]-dy))
            self._drag=e.position()
    def mouseReleaseEvent(self,e): self._drag=None
    def reset_zoom(self): self._zoom=1.0; self._offset=[0.0,0.0]
    def toggle_overlay(self): self._overlay_on=not self._overlay_on; return self._overlay_on

# ── STATUS PILL WIDGET ────────────────────────────────────────────────────────
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

# ── DIALOGS ───────────────────────────────────────────────────────────────────
class BaseDialog(QDialog):
    def __init__(self,parent,title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(460)
        # Drop shadow for depth
        shadow=QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32); shadow.setOffset(0,4)
        shadow.setColor(QColor(0,0,0,140))
        self.setGraphicsEffect(shadow)

    def _section(self,label):
        gb=QGroupBox(label); return gb

    def _divider(self):
        f=QFrame(); f.setFrameShape(QFrame.HLine)
        f.setStyleSheet(f"color:{C['border2']};max-height:1px;margin:2px 0 6px 0;background:{C['border2']};")
        return f

    def _buttons(self,ok_text="Save"):
        bf=QHBoxLayout(); bf.addStretch(); bf.setSpacing(10)
        cancel=QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        cancel.setToolTip("Discard changes and close")
        cancel.setMinimumWidth(90)
        ok=QPushButton(ok_text); ok.setObjectName("accent"); ok.clicked.connect(self.accept)
        ok.setToolTip("Apply and close")
        ok.setMinimumWidth(90)
        bf.addWidget(cancel); bf.addWidget(ok); return bf

class AudioDialog(BaseDialog):
    def __init__(self,parent,cfg,audio):
        super().__init__(parent,"Audio Settings")
        self.cfg=cfg
        self._audio_engine=audio
        self.setMinimumWidth(500)
        layout=QVBoxLayout(self); layout.setSpacing(16); layout.setContentsMargins(20,20,20,20)

        # Header
        hdr=QLabel("\U0001f50a  AUDIO SETTINGS")
        hdr.setStyleSheet(f"color:{C['accent']};font-size:13pt;font-weight:bold;letter-spacing:1.5px;background:transparent;")
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # Volume section
        grp=self._section("Volume & Monitoring"); gl=QFormLayout(grp); gl.setSpacing(14)
        gl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gl.setContentsMargins(12,16,12,12)

        # Volume row: slider + spinbox
        vol_row=QHBoxLayout(); vol_row.setSpacing(10)
        self.vol_slider=QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0,200)
        self.vol_slider.setValue(int(cfg.get("volume",1.0)*100))
        self.vol_slider.setToolTip("Adjust playback volume (0=silent, 100=unity, 200=boost)")
        self.vol_spin=QSpinBox(); self.vol_spin.setRange(0,200); self.vol_spin.setSuffix("%")
        self.vol_spin.setFixedWidth(76); self.vol_spin.setValue(int(cfg.get("volume",1.0)*100))
        self.vol_spin.setToolTip("Type a value directly")
        def _on_vol_slider(v):
            self.vol_spin.blockSignals(True); self.vol_spin.setValue(v); self.vol_spin.blockSignals(False)
            if audio: audio.set_volume(v/100)
            cfg["volume"]=v/100
        def _on_vol_spin(v):
            self.vol_slider.blockSignals(True); self.vol_slider.setValue(v); self.vol_slider.blockSignals(False)
            if audio: audio.set_volume(v/100)
            cfg["volume"]=v/100
        self.vol_slider.valueChanged.connect(_on_vol_slider)
        self.vol_spin.valueChanged.connect(_on_vol_spin)
        vol_row.addWidget(self.vol_slider,1); vol_row.addWidget(self.vol_spin)
        vol_widget=QWidget(); vol_widget.setLayout(vol_row)
        lbl_vol=QLabel("Volume")
        lbl_vol.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gl.addRow(lbl_vol, vol_widget)

        # VU meter label (visual indicator of current level)
        self._vu_label=QLabel()
        self._vu_label.setFixedHeight(14)
        self._vu_label.setStyleSheet(f"background:{C['panel3']};border-radius:4px;")
        self._vu_label.setToolTip("Approximate volume level indicator")
        gl.addRow(QLabel(""), self._vu_label)
        self._update_vu(int(cfg.get("volume",1.0)*100))
        self.vol_slider.valueChanged.connect(self._update_vu)

        # Mute toggle — prominent button
        self.mute_btn=QPushButton()
        muted=cfg.get("muted",False)
        self.mute_btn.setText("\U0001f507  MUTED  (click to unmute)" if muted else "\U0001f50a  Audio Active  (click to mute)")
        self.mute_btn.setObjectName("danger" if muted else "accent")
        self.mute_btn.setFixedHeight(38)
        self.mute_btn.setToolTip("Toggle mute without stopping the stream")
        self._muted=muted
        def _toggle_mute_btn():
            self._muted=not self._muted
            cfg["muted"]=self._muted
            if audio: audio.muted=self._muted
            if self._muted:
                self.mute_btn.setText("\U0001f507  MUTED  (click to unmute)")
                self.mute_btn.setObjectName("danger")
            else:
                self.mute_btn.setText("\U0001f50a  Audio Active  (click to mute)")
                self.mute_btn.setObjectName("accent")
            self.mute_btn.setStyle(self.mute_btn.style())
        self.mute_btn.clicked.connect(_toggle_mute_btn)
        lbl_mute=QLabel("Mute")
        lbl_mute.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gl.addRow(lbl_mute, self.mute_btn)

        layout.addWidget(grp)

        # ── Sample Rate ───────────────────────────────────────────────────────
        grp_sr=self._section("Sample Rate"); gsr=QFormLayout(grp_sr); gsr.setSpacing(12)
        gsr.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gsr.setContentsMargins(12,16,12,12)
        self.sr_combo=QComboBox()
        self.sr_combo.setToolTip("Audio sample rate — must match your capture card / interface")
        cur_sr=cfg.get("audio_sample_rate",48000)
        for sr in [44100,48000,96000]:
            self.sr_combo.addItem(f"{sr} Hz",sr)
            if sr==cur_sr: self.sr_combo.setCurrentIndex(self.sr_combo.count()-1)
        lbl_sr=QLabel("Sample rate:"); lbl_sr.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gsr.addRow(lbl_sr, self.sr_combo)
        sr_note=QLabel("Restart stream after changing sample rate.")
        sr_note.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gsr.addRow("",sr_note)
        layout.addWidget(grp_sr)

        # ── AV Sync Offset ────────────────────────────────────────────────────
        grp_sync=self._section("AV Sync Offset"); gsync=QFormLayout(grp_sync); gsync.setSpacing(12)
        gsync.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gsync.setContentsMargins(12,16,12,12)

        cur_delay=cfg.get("audio_delay_ms",0)
        sync_row=QHBoxLayout(); sync_row.setSpacing(10)
        self.sync_slider=QSlider(Qt.Horizontal)
        self.sync_slider.setRange(-500,500)
        self.sync_slider.setSingleStep(10)
        self.sync_slider.setPageStep(50)
        self.sync_slider.setValue(cur_delay)
        self.sync_slider.setToolTip("Shift audio timing relative to video (-500 to +500 ms, step 10 ms)")
        self.sync_spin=QSpinBox()
        self.sync_spin.setRange(-500,500)
        self.sync_spin.setSingleStep(10)
        self.sync_spin.setSuffix(" ms")
        self.sync_spin.setFixedWidth(88)
        self.sync_spin.setValue(cur_delay)
        self.sync_spin.setToolTip("Audio offset in milliseconds (negative = earlier, positive = later)")

        def _on_sync_slider(v):
            self.sync_spin.blockSignals(True); self.sync_spin.setValue(v); self.sync_spin.blockSignals(False)
            cfg["audio_delay_ms"]=v
            if audio: audio.set_delay(v)
        def _on_sync_spin(v):
            self.sync_slider.blockSignals(True); self.sync_slider.setValue(v); self.sync_slider.blockSignals(False)
            cfg["audio_delay_ms"]=v
            if audio: audio.set_delay(v)
        self.sync_slider.valueChanged.connect(_on_sync_slider)
        self.sync_spin.valueChanged.connect(_on_sync_spin)
        sync_row.addWidget(self.sync_slider,1); sync_row.addWidget(self.sync_spin)
        sync_widget=QWidget(); sync_widget.setLayout(sync_row)
        lbl_sync=QLabel("Sync offset")
        lbl_sync.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gsync.addRow(lbl_sync, sync_widget)

        sync_hint=QLabel("Negative = audio arrives earlier (before video).  Positive = audio arrives later (after video).")
        sync_hint.setWordWrap(True)
        sync_hint.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        gsync.addRow("",sync_hint)
        layout.addWidget(grp_sync)

        # Info note
        note=QLabel("Volume above 100% amplifies the signal (may clip).")
        note.setStyleSheet(f"color:{C['subtext']};font-size:9pt;background:transparent;")
        layout.addWidget(note)
        layout.addLayout(self._buttons("Close"))

    def _update_vu(self, val):
        """Draw a simple gradient bar as a visual volume level indicator."""
        pct=min(val,200)/200.0
        green_w=int(pct*160)
        if pct<=0.5:
            color=C["good"]
        elif pct<=0.85:
            color=C["warn"]
        else:
            color=C["bad"]
        self._vu_label.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"  stop:0 {color}cc, stop:{pct:.2f} {color}88, stop:{min(pct+0.01,1.0):.2f} {C['panel3']}, stop:1 {C['panel3']});"
            f"border-radius:4px;"
        )

    def accept(self):
        self.cfg["audio_sample_rate"]=self.sr_combo.currentData()
        self.cfg["audio_delay_ms"]=self.sync_spin.value()
        self.close()

class ImageDialog(BaseDialog):
    def __init__(self,parent,vthread,cfg=None):
        super().__init__(parent,"Image & Filters"); self.vthread=vthread; self.cfg=cfg
        self.setMinimumWidth(520)
        self.vals={
            "brightness": cfg.get("brightness",1.0) if cfg else 1.0,
            "contrast":   cfg.get("contrast",1.0)   if cfg else 1.0,
            "saturation": cfg.get("saturation",1.0)  if cfg else 1.0,
        }
        layout=QVBoxLayout(self); layout.setSpacing(16); layout.setContentsMargins(20,20,20,20)

        hdr=QLabel("\u25c8  IMAGE & FILTERS")
        hdr.setStyleSheet(f"color:{C['accent']};font-size:13pt;font-weight:bold;letter-spacing:1.5px;background:transparent;")
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        grp=self._section("Colour Adjustments"); gl=QFormLayout(grp); gl.setSpacing(14)
        gl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gl.setContentsMargins(12,16,12,12)
        self.sliders={}; self.spins={}

        slider_defs=[
            ("brightness","\u2600  Brightness", 20,200,"Boost or reduce overall luminance (100 = neutral)"),
            ("contrast",  "\u25d1  Contrast",   20,200,"Expand or compress the tonal range (100 = neutral)"),
            ("saturation","\u2b21  Saturation",  0,200,"Increase or reduce colour intensity (100 = neutral)"),
        ]
        for key,label,lo,hi,tip in slider_defs:
            row=QHBoxLayout(); row.setSpacing(10)
            init_val=self.vals.get(key,1.0)
            sl=QSlider(Qt.Horizontal); sl.setRange(lo,hi); sl.setValue(int(init_val*100)); sl.setToolTip(tip)
            spin=QDoubleSpinBox(); spin.setRange(lo/100.0,hi/100.0); spin.setDecimals(2)
            spin.setSingleStep(0.05); spin.setValue(init_val); spin.setFixedWidth(80)
            spin.setToolTip("Type a value directly (1.0 = neutral)")
            def _on_slider(v, k=key, sp=spin):
                sp.blockSignals(True); sp.setValue(v/100.0); sp.blockSignals(False)
                self.vals[k]=v/100.0; self._apply()
            def _on_spin(v, k=key, s=sl):
                s.blockSignals(True); s.setValue(int(v*100)); s.blockSignals(False)
                self.vals[k]=v; self._apply()
            sl.valueChanged.connect(_on_slider)
            spin.valueChanged.connect(_on_spin)
            row.addWidget(sl,1); row.addWidget(spin)
            container=QWidget(); container.setLayout(row)
            lbl=QLabel(label); lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
            gl.addRow(lbl, container)
            self.sliders[key]=sl; self.spins[key]=spin

        layout.addWidget(grp)

        # Reset button
        reset_row=QHBoxLayout(); reset_row.addStretch()
        reset=QPushButton("\u21ba  Reset All to Neutral")
        reset.setToolTip("Set brightness, contrast, and saturation back to 1.0 (no effect)")
        reset.clicked.connect(self._reset); reset_row.addWidget(reset)
        layout.addLayout(reset_row)
        layout.addLayout(self._buttons("Close"))

    def _apply(self):
        if self.vthread: self.vthread.set_image(self.vals["brightness"],self.vals["contrast"],self.vals["saturation"])
        if self.cfg:
            self.cfg["brightness"]=self.vals["brightness"]
            self.cfg["contrast"]=self.vals["contrast"]
            self.cfg["saturation"]=self.vals["saturation"]
            save_config(self.cfg)

    def _reset(self):
        for key in self.sliders:
            self.sliders[key].setValue(100)

    def accept(self): self.close()

class UpscaleDialog(BaseDialog):
    def __init__(self,parent,cfg):
        super().__init__(parent,"Upscaling Settings"); self.mode=cfg.get("upscale_mode","none")
        self.setMinimumWidth(500)
        layout=QVBoxLayout(self); layout.setSpacing(16); layout.setContentsMargins(20,20,20,20)

        hdr=QLabel("\U0001f50d  GPU UPSCALING")
        hdr.setStyleSheet(f"color:{C['accent']};font-size:13pt;font-weight:bold;letter-spacing:1.5px;background:transparent;")
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        grp=self._section("Upscale Mode"); gl=QVBoxLayout(grp); gl.setSpacing(10)
        gl.setContentsMargins(12,16,12,12)
        self.bg=QButtonGroup()

        card_defs=[
            ("none","\u25a0  Off  \u2014  No upscaling",
             "Pass frames through at captured resolution.\nLowest CPU/GPU overhead — best for 1080p60 direct capture.", True),
            ("cuda",f"\u26a1  CUDA Lanczos  \u2014  GPU resize  "
                    f"{'(\u2713 Available)' if CUDA_AVAILABLE else '(\u2717 Not available)'}",
             "Use NVIDIA CUDA to upscale via Lanczos4 interpolation.\nBest quality for 720p\u21921080p or 1080p\u21921440p.",
             CUDA_AVAILABLE),
        ]
        for val,label,desc,avail in card_defs:
            # Card container
            card=QFrame(); card.setObjectName("upscale_card")
            card.setStyleSheet(
                f"QFrame#upscale_card{{"
                f"  background:{C['card']};"
                f"  border:1px solid {''+C['accent'] if val==self.mode else C['border2']};"
                f"  border-radius:10px;"
                f"  padding:4px;"
                f"}}"
                f"QFrame#upscale_card:hover{{"
                f"  border-color:{C['accent2']};"
                f"}}"
            )
            cl=QVBoxLayout(card); cl.setSpacing(4); cl.setContentsMargins(12,10,12,10)
            rb=QRadioButton(label); rb.setChecked(val==self.mode); rb.setEnabled(avail)
            rb.setToolTip(desc)
            rb.setStyleSheet(f"font-weight:bold;font-size:10pt;color:{C['text'] if avail else C['subtext']};background:transparent;")
            desc_lbl=QLabel(desc.replace(".","\n.",1) if "." in desc else desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(f"color:{C['text2']};font-size:9pt;background:transparent;padding-left:26px;")
            def _on_rb(checked,v=val,c=card):
                if checked:
                    setattr(self,"mode",v)
                    # Update card borders
                    for ch in grp.findChildren(QFrame):
                        ch.setStyleSheet(ch.styleSheet())
            rb.toggled.connect(_on_rb)
            self.bg.addButton(rb); cl.addWidget(rb); cl.addWidget(desc_lbl)
            gl.addWidget(card)

        layout.addWidget(grp)
        layout.addLayout(self._buttons())

class RecordingDialog(BaseDialog):
    def __init__(self,parent,cfg):
        super().__init__(parent,"Recording Settings"); self.cfg=cfg
        self.setMinimumWidth(540)
        layout=QVBoxLayout(self); layout.setSpacing(16); layout.setContentsMargins(20,20,20,20)

        hdr=QLabel("\u23fa  RECORDING SETTINGS")
        hdr.setStyleSheet(f"color:{C['accent']};font-size:13pt;font-weight:bold;letter-spacing:1.5px;background:transparent;")
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # ── Output Paths ──────────────────────────────────────────────────────
        grp=self._section("Output Paths"); gfl=QFormLayout(grp); gfl.setSpacing(12)
        gfl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gfl.setContentsMargins(12,16,12,12)

        for attr,label,key,tip in [
            ("rec_path","Recordings","recording_path","Folder where recordings are saved"),
            ("scr_path","Screenshots","screenshot_path","Folder where screenshots are saved"),
            ("clip_path_edit","Clips","clip_path","Folder where instant clips (F9) are saved"),
        ]:
            row=QHBoxLayout(); row.setSpacing(6)
            le=QLineEdit(cfg.get(key,"")); le.setToolTip(tip)
            br=QPushButton("\U0001f4c2  Browse"); br.setFixedWidth(100)
            br.setToolTip(f"Choose {label.lower()} folder")
            def _browse(checked, le=le, lbl=label):
                d=QFileDialog.getExistingDirectory(self,f"Choose {lbl} Folder",le.text())
                if d: le.setText(d)
            br.clicked.connect(_browse)
            row.addWidget(le,1); row.addWidget(br)
            w=QWidget(); w.setLayout(row)
            lbl=QLabel(label+":"); lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
            gfl.addRow(lbl,w)
            setattr(self,attr,le)

        layout.addWidget(grp)

        # ── Screenshot Format ─────────────────────────────────────────────────
        grp_sfmt=self._section("Screenshot Format"); gsfmt=QVBoxLayout(grp_sfmt); gsfmt.setSpacing(10)
        gsfmt.setContentsMargins(12,16,12,12)
        sfmt_row=QHBoxLayout(); sfmt_row.setSpacing(10); self.sfmt_bg=QButtonGroup()
        cur_sfmt=cfg.get("screenshot_format","png")
        for bid,(fmt,label_f) in enumerate([("png","PNG"),("jpeg","JPEG"),("webp","WebP")]):
            rb=QRadioButton(label_f); rb.setChecked(fmt==cur_sfmt)
            rb.setStyleSheet(f"font-size:10pt;background:transparent;")
            self.sfmt_bg.addButton(rb,bid)
            sfmt_row.addWidget(rb)
        sfmt_row.addStretch()
        gsfmt.addLayout(sfmt_row)
        jpeg_row=QHBoxLayout(); jpeg_row.setSpacing(10)
        jpeg_qlbl=QLabel("JPEG quality:"); jpeg_qlbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        self.jpeg_quality_spin=QSpinBox(); self.jpeg_quality_spin.setRange(1,100)
        self.jpeg_quality_spin.setValue(cfg.get("screenshot_jpeg_quality",92))
        self.jpeg_quality_spin.setFixedWidth(80); self.jpeg_quality_spin.setSuffix("%")
        self.jpeg_quality_spin.setToolTip("JPEG compression quality (higher = larger file, better quality)")
        jpeg_row.addWidget(jpeg_qlbl); jpeg_row.addWidget(self.jpeg_quality_spin); jpeg_row.addStretch()
        self._jpeg_qual_w=QWidget(); self._jpeg_qual_w.setLayout(jpeg_row)
        self._jpeg_qual_w.setVisible(cur_sfmt=="jpeg")
        gsfmt.addWidget(self._jpeg_qual_w)
        self.sfmt_bg.idClicked.connect(lambda bid: self._jpeg_qual_w.setVisible(bid==1))
        layout.addWidget(grp_sfmt)

        # ── Format & Buffer ───────────────────────────────────────────────────
        grp2=self._section("Format & Clip Buffer"); gl2=QVBoxLayout(grp2); gl2.setSpacing(12)
        gl2.setContentsMargins(12,16,12,12)

        # Format cards
        fmt_lbl=QLabel("Container format:")
        fmt_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        gl2.addWidget(fmt_lbl)
        fmt_row=QHBoxLayout(); fmt_row.setSpacing(10); self.fmt_bg=QButtonGroup()
        for fmt,icon,title,desc,tip in [
            ("mp4","\U0001f3ac","MP4","H.264 / best compat","Standard MP4 — plays everywhere"),
            ("mkv","\U0001f4e6","MKV","H.264 / recoverable","Matroska — safe if interrupted"),
        ]:
            card=QFrame(); card.setStyleSheet(
                f"QFrame{{background:{C['panel3']};border:1px solid "
                f"{''+C['accent'] if fmt==cfg.get('recording_format','mp4') else C['border2']};"
                f"border-radius:8px;padding:4px;}}"
                f"QFrame:hover{{border-color:{C['accent2']};}}"
            )
            cl=QVBoxLayout(card); cl.setSpacing(3); cl.setContentsMargins(12,10,12,10)
            rb=QRadioButton(f"{icon} {title}"); rb.setChecked(fmt==cfg.get("recording_format","mp4"))
            rb.setStyleSheet(f"font-weight:bold;font-size:10pt;background:transparent;")
            rb.setToolTip(tip)
            rb.toggled.connect(lambda c,f=fmt:cfg.__setitem__("recording_format",f) if c else None)
            desc_l=QLabel(desc); desc_l.setStyleSheet(f"color:{C['subtext']};font-size:8pt;background:transparent;padding-left:4px;")
            self.fmt_bg.addButton(rb); cl.addWidget(rb); cl.addWidget(desc_l)
            fmt_row.addWidget(card)
        fmt_row.addStretch()
        gl2.addLayout(fmt_row)

        # Clip buffer
        clip_row=QHBoxLayout(); clip_row.setSpacing(10)
        clip_label=QLabel("Clip buffer duration:")
        clip_label.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        self.clip_spin=QSpinBox(); self.clip_spin.setRange(5,120); self.clip_spin.setSuffix(" seconds")
        self.clip_spin.setValue(cfg.get("clip_duration",30)); self.clip_spin.setFixedWidth(120)
        self.clip_spin.setToolTip("Seconds of footage kept in rolling buffer — press F9 to save as instant clip")
        clip_row.addWidget(clip_label); clip_row.addWidget(self.clip_spin); clip_row.addStretch()
        gl2.addLayout(clip_row)

        layout.addWidget(grp2)

        # ── Audio Track ───────────────────────────────────────────────────────
        grp_aud = self._section("Audio Track"); gaud = QVBoxLayout(grp_aud); gaud.setSpacing(10)
        gaud.setContentsMargins(12,16,12,12)

        # ffmpeg availability note
        if not FFMPEG_PATH:
            no_ff = QLabel(
                "\u26a0  ffmpeg not found — audio will not be included in recordings.\n"
                "Install ffmpeg and place it at  C:/ContentCapture_v2/bin/ffmpeg.exe  or add it to PATH."
            )
            no_ff.setWordWrap(True)
            no_ff.setStyleSheet(
                f"color:{C['warning']};font-size:9pt;background:transparent;"
                f"border:1px solid {C['warning']}44;border-radius:6px;padding:6px 10px;"
            )
            gaud.addWidget(no_ff)

        # Include audio checkbox
        self.aud_include_chk = QCheckBox("Include audio in recordings")
        self.aud_include_chk.setChecked(cfg.get("recording_include_audio", True) and bool(FFMPEG_PATH))
        if not FFMPEG_PATH:
            self.aud_include_chk.setEnabled(False)
            self.aud_include_chk.setToolTip("Install ffmpeg to enable audio recording")
        else:
            self.aud_include_chk.setToolTip("Mux the captured audio stream into the output file via ffmpeg")
        gaud.addWidget(self.aud_include_chk)

        # Codec + bitrate row (enabled only when checkbox is on)
        codec_row = QHBoxLayout(); codec_row.setSpacing(14)
        codec_lbl = QLabel("Codec:"); codec_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        codec_row.addWidget(codec_lbl)
        self._aud_codec_bg = QButtonGroup()
        cur_codec = cfg.get("recording_audio_codec","aac")
        self._aud_rb_aac  = QRadioButton("AAC")
        self._aud_rb_mp3  = QRadioButton("MP3")
        self._aud_rb_pcm  = QRadioButton("PCM (lossless, large)")
        for i,(rb,val) in enumerate([(self._aud_rb_aac,"aac"),(self._aud_rb_mp3,"mp3"),(self._aud_rb_pcm,"pcm")]):
            rb.setChecked(val == cur_codec)
            rb.setStyleSheet("font-size:10pt;background:transparent;")
            self._aud_codec_bg.addButton(rb, i)
            codec_row.addWidget(rb)
        codec_row.addStretch()
        gaud.addLayout(codec_row)

        # Bitrate row
        bitrate_row = QHBoxLayout(); bitrate_row.setSpacing(10)
        bitrate_lbl = QLabel("Bitrate:"); bitrate_lbl.setStyleSheet(f"color:{C['text2']};font-size:10pt;background:transparent;")
        self.aud_bitrate_spin = QSpinBox()
        self.aud_bitrate_spin.setRange(64, 320)
        self.aud_bitrate_spin.setSingleStep(64)
        self.aud_bitrate_spin.setSuffix(" kbps")
        self.aud_bitrate_spin.setFixedWidth(110)
        cur_br = cfg.get("recording_audio_bitrate", 320)
        # Snap to nearest valid value
        for snap in [64, 128, 192, 320]:
            if cur_br <= snap:
                cur_br = snap; break
        self.aud_bitrate_spin.setValue(cur_br)
        self.aud_bitrate_spin.setToolTip("Audio bitrate for AAC/MP3 (ignored for PCM)")
        bitrate_row.addWidget(bitrate_lbl); bitrate_row.addWidget(self.aud_bitrate_spin); bitrate_row.addStretch()
        self._bitrate_widget = QWidget(); self._bitrate_widget.setLayout(bitrate_row)
        gaud.addWidget(self._bitrate_widget)

        # Wire up enable/disable logic
        def _update_aud_controls():
            enabled = self.aud_include_chk.isChecked() and bool(FFMPEG_PATH)
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

    def accept(self):
        self.cfg["recording_path"]=self.rec_path.text()
        self.cfg["screenshot_path"]=self.scr_path.text()
        self.cfg["clip_path"]=self.clip_path_edit.text()
        self.cfg["clip_duration"]=self.clip_spin.value()
        fmt_map={0:"png",1:"jpeg",2:"webp"}
        self.cfg["screenshot_format"]=fmt_map.get(self.sfmt_bg.checkedId(),"png")
        self.cfg["screenshot_jpeg_quality"]=self.jpeg_quality_spin.value()
        # Audio track settings
        self.cfg["recording_include_audio"] = self.aud_include_chk.isChecked()
        codec_map = {0:"aac", 1:"mp3", 2:"pcm"}
        self.cfg["recording_audio_codec"] = codec_map.get(self._aud_codec_bg.checkedId(), "aac")
        self.cfg["recording_audio_bitrate"] = self.aud_bitrate_spin.value()
        super().accept()

class DeviceDialog(BaseDialog):
    def __init__(self,parent,cfg):
        super().__init__(parent,"Device Settings"); self.cfg=cfg
        self.setMinimumWidth(520)
        layout=QVBoxLayout(self); layout.setSpacing(16); layout.setContentsMargins(20,20,20,20)

        hdr=QLabel("\u2699  DEVICE SETTINGS")
        hdr.setStyleSheet(f"color:{C['accent']};font-size:13pt;font-weight:bold;letter-spacing:1.5px;background:transparent;")
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # ── Devices form ──────────────────────────────────────────────────────
        grp=self._section("Capture Devices"); gfl=QFormLayout(grp); gfl.setSpacing(14)
        gfl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        gfl.setContentsMargins(12,16,12,12)

        # Video device
        self.vid_combo=QComboBox()
        self.vid_combo.setToolTip("Select the capture card or camera to use as video source")
        vdevs=find_video_devices()
        for idx,name in vdevs:
            self.vid_combo.addItem(f"\U0001f4f9  {name}",idx)
            if idx==cfg.get("video_index",0): self.vid_combo.setCurrentIndex(self.vid_combo.count()-1)
        if self.vid_combo.count()==0: self.vid_combo.addItem("No video devices found",0)
        vid_row=QHBoxLayout(); vid_row.setSpacing(6)
        vid_row.addWidget(self.vid_combo,1)
        refresh_btn=QPushButton("\u21ba"); refresh_btn.setFixedWidth(36)
        refresh_btn.setToolTip("Rescan for video devices")
        def _refresh_vid():
            self.vid_combo.clear()
            for idx,name in find_video_devices():
                self.vid_combo.addItem(f"\U0001f4f9  {name}",idx)
            if self.vid_combo.count()==0: self.vid_combo.addItem("No video devices found",0)
        refresh_btn.clicked.connect(_refresh_vid)
        vid_row.addWidget(refresh_btn)
        vw=QWidget(); vw.setLayout(vid_row)
        lbl_vid=QLabel("Video device:"); lbl_vid.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_vid, vw)

        # Resolution + FPS linked dropdowns
        res_fps_row=QHBoxLayout(); res_fps_row.setSpacing(10)
        self.res_combo=QComboBox()
        self.res_combo.setToolTip("Target capture resolution (device must support it)")
        for label,val in {"1920x1080 (1080p)":"1920x1080","1280x720 (720p)":"1280x720","854x480 (480p)":"854x480","640x360 (360p)":"640x360"}.items():
            self.res_combo.addItem(label,val)
            if val==cfg.get("resolution","1920x1080"): self.res_combo.setCurrentIndex(self.res_combo.count()-1)
        self.fps_combo=QComboBox()
        self.fps_combo.setToolTip("Target frame rate (device must support it)")
        for f in [60,30,24,15]:
            self.fps_combo.addItem(f"{f} fps",f)
            if f==cfg.get("fps",60): self.fps_combo.setCurrentIndex(self.fps_combo.count()-1)
        res_fps_row.addWidget(self.res_combo,2); res_fps_row.addWidget(self.fps_combo,1)
        rfw=QWidget(); rfw.setLayout(res_fps_row)
        lbl_res=QLabel("Resolution / FPS:"); lbl_res.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_res, rfw)

        # Audio input device
        self.aud_combo=QComboBox()
        self.aud_combo.setToolTip("Select the audio input device connected to the capture card")
        all_audio_devs=[]
        try: all_audio_devs=list(enumerate(sd.query_devices()))
        except Exception: pass
        for idx,d in all_audio_devs:
            if d["max_input_channels"]>0:
                self.aud_combo.addItem(f"\U0001f50a  [{idx}] {d['name'][:50]}",idx)
                if idx==cfg.get("audio_input_index",3): self.aud_combo.setCurrentIndex(self.aud_combo.count()-1)
        if self.aud_combo.count()==0: self.aud_combo.addItem("No audio input devices found",0)
        lbl_aud=QLabel("Audio input:"); lbl_aud.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_aud, self.aud_combo)

        # Audio output device
        self.aud_out_combo=QComboBox()
        self.aud_out_combo.setToolTip("Select the audio output / playback device (system default if not set)")
        self.aud_out_combo.addItem("\U0001f508  System default",None)
        saved_out=cfg.get("audio_output_index",None)
        for idx,d in all_audio_devs:
            if d["max_output_channels"]>0:
                self.aud_out_combo.addItem(f"\U0001f508  [{idx}] {d['name'][:50]}",idx)
                if idx==saved_out: self.aud_out_combo.setCurrentIndex(self.aud_out_combo.count()-1)
        lbl_aud_out=QLabel("Audio output:"); lbl_aud_out.setStyleSheet(f"color:{C['text2']};font-size:10pt;")
        gfl.addRow(lbl_aud_out, self.aud_out_combo)

        layout.addWidget(grp)

        # ── Behaviour ─────────────────────────────────────────────────────────
        grp_beh=self._section("Behaviour"); gbeh=QVBoxLayout(grp_beh); gbeh.setSpacing(8)
        gbeh.setContentsMargins(12,16,12,12)
        self.autostart_chk=QCheckBox("Auto-start stream on launch")
        self.autostart_chk.setChecked(cfg.get("auto_start",True))
        self.autostart_chk.setToolTip("Automatically start capturing when the app opens")
        gbeh.addWidget(self.autostart_chk)
        layout.addWidget(grp_beh)

        # Warning note
        note_bar=QFrame()
        note_bar.setStyleSheet(
            f"background:{C['warning']}18;border:1px solid {C['warning']}44;"
            f"border-radius:7px;padding:2px;"
        )
        note_layout=QHBoxLayout(note_bar); note_layout.setContentsMargins(10,6,10,6)
        note_icon=QLabel("\u26a0"); note_icon.setStyleSheet(f"color:{C['warning']};font-size:12pt;background:transparent;")
        note_text=QLabel("Changes take effect on the next stream start  (F5 to restart).")
        note_text.setStyleSheet(f"color:{C['warning']};font-size:9pt;background:transparent;")
        note_layout.addWidget(note_icon); note_layout.addWidget(note_text,1)
        layout.addWidget(note_bar)

        layout.addLayout(self._buttons())

    def accept(self):
        self.cfg["video_index"]=self.vid_combo.currentData()
        self.cfg["audio_input_index"]=self.aud_combo.currentData()
        self.cfg["audio_output_index"]=self.aud_out_combo.currentData()
        self.cfg["auto_start"]=self.autostart_chk.isChecked()
        if self.res_combo.currentData(): self.cfg["resolution"]=self.res_combo.currentData()
        if self.fps_combo.currentData(): self.cfg["fps"]=self.fps_combo.currentData()
        super().accept()

# ── HOTKEY DIALOG ─────────────────────────────────────────────────────────────
# ── GLOBAL HOTKEY MANAGER ─────────────────────────────────────────────────────
class GlobalHotkeyManager(QObject):
    """Bridges the `keyboard` library's background-thread callbacks to Qt signals.

    All public methods are safe to call from the Qt main thread.
    Callbacks emitted by `keyboard` are forwarded via Signal so they always
    arrive on the main thread regardless of which thread the hook fires on.
    """
    triggered = Signal(str)   # emits the action_key string, e.g. "save_clip"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered = {}   # action_key -> hotkey string currently registered
        self._enabled = False
        try:
            import keyboard as _kb
            self._kb = _kb
        except ImportError:
            self._kb = None
            print("[GlobalHotkey] 'keyboard' package not installed — global hotkeys unavailable")

    def is_available(self) -> bool:
        """Return True only when the `keyboard` library could be imported."""
        return self._kb is not None

    def register(self, action_key: str, key_str: str):
        """Register (or replace) the global hotkey for *action_key*.

        Safe to call multiple times; the old binding for the same action is
        removed first.  No-ops if the manager is disabled or unavailable.
        """
        if not self._kb or not self._enabled:
            return
        # Remove any previous binding for this action
        old = self._registered.get(action_key)
        if old:
            try:
                self._kb.remove_hotkey(old)
            except Exception:
                pass
        if not key_str:
            return
        try:
            # The lambda captures action_key by value (a=action_key).
            # Signal.emit() is thread-safe for Qt signals, so calling it from
            # the keyboard hook thread is explicitly allowed.
            self._kb.add_hotkey(
                key_str,
                lambda a=action_key: self.triggered.emit(a),
                suppress=False,
            )
            self._registered[action_key] = key_str
        except Exception as e:
            print(f"[GlobalHotkey] Failed to register '{key_str}' for '{action_key}': {e}")

    def unregister_all(self):
        """Remove every registered global hotkey.  Safe to call when disabled."""
        if not self._kb:
            return
        for key_str in list(self._registered.values()):
            try:
                self._kb.remove_hotkey(key_str)
            except Exception:
                pass
        self._registered.clear()

    def set_enabled(self, enabled: bool):
        """Enable or disable global hotkeys.  Disabling also unregisters all hooks."""
        self._enabled = enabled
        if not enabled:
            self.unregister_all()


# ── HOTKEY DIALOG ─────────────────────────────────────────────────────────────
class HotkeyDialog(BaseDialog):
    # (action_key, display_name, default_key)
    ACTIONS = [
        ("toggle_stream",    "Toggle Stream",    "F5"),
        ("save_clip",        "Save Clip",        "F9"),
        ("toggle_recording", "Toggle Recording", "F10"),
        ("toggle_fullscreen","Toggle Fullscreen","F11"),
        ("screenshot",       "Screenshot",       "F12"),
        ("toggle_mute",      "Toggle Mute",      "M"),
        ("toggle_overlay",   "Toggle Overlay",   "P"),
        ("reset_image",      "Reset Image",      "R"),
        ("reset_zoom",       "Reset Zoom",       "Z"),
        ("volume_up",        "Volume Up",        "="),
        ("volume_down",      "Volume Down",      "-"),
        ("exit_app",         "Exit App",         "Ctrl+Q"),
    ]

    def __init__(self, parent, cfg):
        super().__init__(parent, "Hotkey Remapping")
        self.cfg = cfg
        self.setMinimumWidth(660)
        self.setMinimumHeight(560)

        # Grab GlobalHotkeyManager from parent window (may be None)
        self._global_hk = getattr(parent, "_global_hk", None)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr = QLabel("\u2328  HOTKEY REMAPPING")
        hdr.setStyleSheet(
            f"color:{C['accent']};font-size:13pt;font-weight:bold;"
            f"letter-spacing:1.5px;background:transparent;"
        )
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # ── Global Hotkeys group box ──────────────────────────────────────────
        global_box = QGroupBox("Global Hotkeys")
        global_box_layout = QVBoxLayout(global_box)
        global_box_layout.setContentsMargins(12, 10, 12, 10)
        global_box_layout.setSpacing(6)

        self._global_master_cb = QCheckBox(
            "Enable global hotkeys (work while app is not focused)"
        )
        self._global_master_cb.setChecked(cfg.get("global_hotkeys_enabled", False))
        global_box_layout.addWidget(self._global_master_cb)

        global_note = QLabel(
            "Check the \u201cGlobal\u201d column below to make individual actions fire even when "
            "another window (e.g. a game) is in the foreground."
        )
        global_note.setWordWrap(True)
        global_note.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;background:transparent;"
        )
        global_box_layout.addWidget(global_note)

        # If keyboard package is missing, disable the group and explain why
        if self._global_hk is not None and not self._global_hk.is_available():
            global_box.setEnabled(False)
            global_box.setToolTip(
                "Install the 'keyboard' package to enable global hotkeys  "
                "(pip install keyboard)"
            )

        layout.addWidget(global_box)

        note = QLabel(
            "Click a key field and press the desired combination to remap it. "
            "Click Reset to restore the factory default for that action."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{C['text2']};font-size:9pt;background:transparent;")
        layout.addWidget(note)

        # ── Hotkey table — 4 columns: Action | Key Binding | Global | Reset ──
        self._table = QTableWidget(len(self.ACTIONS), 4, self)
        self._table.setHorizontalHeaderLabels(["Action", "Key Binding", "Global", ""])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._table.setColumnWidth(2, 64)
        self._table.setColumnWidth(3, 80)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setStyleSheet(
            f"QTableWidget{{background:{C['panel2']};border:1px solid {C['border']};"
            f"border-radius:8px;gridline-color:{C['border']};}}"
            f"QTableWidget::item{{padding:4px 8px;}}"
            f"QHeaderView::section{{background:{C['panel3']};color:{C['accent']};"
            f"border:none;border-bottom:1px solid {C['border2']};"
            f"padding:6px 8px;font-weight:bold;font-size:9pt;}}"
        )

        hotkeys = cfg.get("hotkeys", {})
        global_actions = set(cfg.get("global_hotkey_actions", []))
        global_enabled = cfg.get("global_hotkeys_enabled", False)
        hk_available = self._global_hk is not None and self._global_hk.is_available()

        self._edits = {}
        self._global_cbs = {}   # action_key -> QCheckBox

        for row, (key, name, default) in enumerate(self.ACTIONS):
            current = hotkeys.get(key, default)

            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor(C["text"]))
            self._table.setItem(row, 0, name_item)

            edit = QKeySequenceEdit(QKeySequence(current), self)
            edit.setStyleSheet(
                f"QKeySequenceEdit{{background:{C['panel3']};color:{C['text']};"
                f"border:1px solid {C['border2']};border-radius:6px;"
                f"padding:4px 8px;font-size:10pt;}}"
                f"QKeySequenceEdit:focus{{border-color:{C['accent']};}}"
            )
            self._table.setCellWidget(row, 1, edit)
            self._edits[key] = edit

            # "Global" checkbox — col 2
            global_cb = QCheckBox()
            global_cb.setChecked(key in global_actions)
            global_cb.setEnabled(global_enabled and hk_available)
            global_cb.setToolTip(
                "Fire this action even when the app is not focused"
                if hk_available
                else "Install the 'keyboard' package to enable global hotkeys"
            )
            cb_container = QWidget()
            cb_inner = QHBoxLayout(cb_container)
            cb_inner.setContentsMargins(0, 0, 0, 0)
            cb_inner.setAlignment(Qt.AlignCenter)
            cb_inner.addWidget(global_cb)
            self._table.setCellWidget(row, 2, cb_container)
            self._global_cbs[key] = global_cb

            reset_btn = QPushButton("Reset")
            reset_btn.setFixedHeight(28)
            reset_btn.setStyleSheet(
                f"QPushButton{{background:{C['panel3']};color:{C['text2']};"
                f"border:1px solid {C['border2']};border-radius:5px;"
                f"padding:0 8px;font-size:9pt;}}"
                f"QPushButton:hover{{background:{C['hover2']};color:{C['accent']};"
                f"border-color:{C['accent']};}}"
            )
            reset_btn.clicked.connect(
                lambda checked, d=default, e=edit: e.setKeySequence(QKeySequence(d))
            )
            btn_container = QWidget()
            btn_inner = QHBoxLayout(btn_container)
            btn_inner.setContentsMargins(4, 2, 4, 2)
            btn_inner.addWidget(reset_btn)
            self._table.setCellWidget(row, 3, btn_container)
            self._table.setRowHeight(row, 38)

        layout.addWidget(self._table)

        # Wire master checkbox → enable/disable per-row global checkboxes
        self._global_master_cb.toggled.connect(self._on_global_master_toggled)

        reset_row = QHBoxLayout()
        reset_all = QPushButton("\u21ba  Reset All to Defaults")
        reset_all.setToolTip("Restore every action to its factory default key")
        reset_all.clicked.connect(self._reset_all)
        reset_row.addStretch()
        reset_row.addWidget(reset_all)
        layout.addLayout(reset_row)
        layout.addLayout(self._buttons("Save"))

    def _on_global_master_toggled(self, checked: bool):
        """Enable or disable per-action Global checkboxes based on master state."""
        hk_available = self._global_hk is not None and self._global_hk.is_available()
        for cb in self._global_cbs.values():
            cb.setEnabled(checked and hk_available)

    def _reset_all(self):
        for key, name, default in self.ACTIONS:
            self._edits[key].setKeySequence(QKeySequence(default))

    def accept(self):
        hotkeys = self.cfg.setdefault("hotkeys", {})
        for key, name, default in self.ACTIONS:
            seq = self._edits[key].keySequence()
            hotkeys[key] = seq.toString() if not seq.isEmpty() else default
        self.cfg["hotkeys"] = hotkeys

        # Persist global hotkey settings
        self.cfg["global_hotkeys_enabled"] = self._global_master_cb.isChecked()
        self.cfg["global_hotkey_actions"] = [
            key for key, cb in self._global_cbs.items() if cb.isChecked()
        ]

        save_config(self.cfg)
        parent = self.parent()
        if parent and hasattr(parent, "_bind_shortcuts"):
            parent._bind_shortcuts()
        # Re-register global hotkeys to reflect any changes
        if parent and hasattr(parent, "_apply_global_hotkeys"):
            parent._apply_global_hotkeys()
        super().accept()

# ── MAIN WINDOW ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    RESOLUTIONS={"1920x1080 (1080p)":"1920x1080","1280x720 (720p)":"1280x720","854x480 (480p)":"854x480","640x360 (360p)":"640x360"}
    FPS_OPTIONS=[60,30,24,15]

    def __init__(self):
        super().__init__()
        self.cfg=load_config(); self.perf=PerfTracker()
        self.recorder=VideoRecorder()
        self.clip_buf=ClipBuffer(self.cfg["clip_duration"],self.cfg["fps"])
        self.audio=None; self.vthread=None; self.running=False
        self._audio_recorder=None
        self._raw_frame=None; self._frame_lock=threading.Lock(); self._sys_data={}
        self.fs_mode=False
        # Global hotkey manager — bridges keyboard lib callbacks to the Qt thread
        self._global_hk = GlobalHotkeyManager(self)
        self._global_hk.triggered.connect(self._on_global_hotkey)
        self._build_ui(); self._build_menu(); self._bind_shortcuts()
        self.sys_stats=SystemStats()
        self.sys_stats.updated.connect(self._on_sys_stats)
        self.sys_stats.start()
        if self.cfg.get("geometry"):
            try:
                from PySide6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromHex(bytes(self.cfg["geometry"],"ascii")))
            except Exception: pass
        else: self.resize(1440,860)
        self.setWindowTitle(APP_NAME); self.setStyleSheet(STYLESHEET)
        if self.cfg.get("always_on_top"): self.setWindowFlags(self.windowFlags()|Qt.WindowStaysOnTopHint)
        if self.cfg.get("auto_start",True): QTimer.singleShot(1500,self.start_stream)
        self._apply_global_hotkeys()

    # ── UI CONSTRUCTION ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Central widget: video fills everything ────────────────────────────
        self.video=VideoWidget(); self.video._ar_lock=self.cfg.get("aspect_ratio_lock",True)
        self.video.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video.customContextMenuRequested.connect(self._show_ctx_menu)
        self.setCentralWidget(self.video)

        # ── QToolBar (primary controls) ───────────────────────────────────────
        self.toolbar=QToolBar("Main Controls",self)
        self.toolbar.setObjectName("main_toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(18,18))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setStyleSheet(
            f"QToolBar{{background:{C['toolbar']};border-bottom:1px solid {C['border2']};padding:3px 8px;spacing:2px;}}"
        )
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # Brand label in toolbar
        brand=QLabel(f"  \u2b21  {APP_NAME.upper()}  ")
        brand.setStyleSheet(
            f"color:{C['accent']};font-size:11pt;font-weight:bold;"
            f"letter-spacing:2px;border:none;padding:0 10px 0 4px;"
        )
        self.toolbar.addWidget(brand)

        # Status pill — LIVE / OFFLINE
        self.status_pill=StatusPill("OFFLINE", C["danger"])
        self.status_pill.setToolTip("Capture stream state")
        self.toolbar.addWidget(self.status_pill)

        # Recording pill (hidden until recording)
        self.rec_pill=StatusPill("", C["record"])
        self.rec_pill.hide()
        self.rec_pill.setToolTip("Currently recording to file")
        self.toolbar.addWidget(self.rec_pill)

        # Mute pill
        self.mute_pill=StatusPill("", C["danger"])
        self.mute_pill.hide()
        self.mute_pill.setToolTip("Audio muted")
        self.toolbar.addWidget(self.mute_pill)

        self.toolbar.addSeparator()

        # ── Capture group ─────────────────────────────────────────────────────
        self.start_action=self._tact("\u25b6  START", self.toggle_stream,
                                     "Start / stop the capture stream  [F5]", checkable=False)
        self.start_action.setObjectName("start_action")
        self.toolbar.addAction(self.start_action)
        self.toolbar.addSeparator()

        # ── Audio group ───────────────────────────────────────────────────────
        self.toolbar.addWidget(self._toolbar_label("AUDIO"))
        self._mute_action=self._tact("\U0001f50a  MUTE", self.toggle_mute,
                                     "Toggle audio mute  [M]")
        self.toolbar.addAction(self._mute_action)
        self.toolbar.addSeparator()

        # ── Recording group ───────────────────────────────────────────────────
        self.toolbar.addWidget(self._toolbar_label("CAPTURE"))
        self._rec_action=self._tact("\u23fa  REC", self.toggle_recording,
                                    "Start / stop recording to file  [F10]")
        self.toolbar.addAction(self._rec_action)
        self._clip_action=self._tact("\U0001f4be  CLIP", self.save_clip,
                                     f"Save last {self.cfg.get('clip_duration',30)}s as instant clip  [F9]")
        self.toolbar.addAction(self._clip_action)
        self._shot_action=self._tact("\U0001f4f7  SHOT", self.take_screenshot,
                                     "Capture a PNG screenshot  [F12]")
        self.toolbar.addAction(self._shot_action)
        self.toolbar.addSeparator()

        # ── View group ────────────────────────────────────────────────────────
        self.toolbar.addWidget(self._toolbar_label("VIEW"))
        self._overlay_action=self._tact("\U0001f4ca  OVERLAY", self._toggle_overlay,
                                        "Toggle performance HUD overlay  [P]", checkable=True)
        self.toolbar.addAction(self._overlay_action)
        self._fs_action=self._tact("\u29c6  FULL", self.toggle_fullscreen,
                                   "Enter fullscreen mode  [F11]")
        self.toolbar.addAction(self._fs_action)

        # Stretch spacer
        spacer=QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        # Right-side info labels in toolbar
        self.res_lbl=QLabel("\u2014")
        self.res_lbl.setStyleSheet(f"color:{C['text2']};font-size:9pt;border:none;padding:0 4px;")
        self.res_lbl.setToolTip("Active capture resolution")
        self.toolbar.addWidget(self.res_lbl)

        _sep_a=QFrame(); _sep_a.setFrameShape(QFrame.VLine)
        _sep_a.setStyleSheet(f"color:{C['border2']};margin:7px 4px;"); self.toolbar.addWidget(_sep_a)

        self.fps_lbl=QLabel("\u2014")
        self.fps_lbl.setStyleSheet(f"color:{C['text2']};font-size:9pt;border:none;padding:0 4px;")
        self.fps_lbl.setToolTip("Live frames-per-second")
        self.toolbar.addWidget(self.fps_lbl)

        _sep_b=QFrame(); _sep_b.setFrameShape(QFrame.VLine)
        _sep_b.setStyleSheet(f"color:{C['border2']};margin:7px 4px;"); self.toolbar.addWidget(_sep_b)

        self.vol_lbl=QLabel("VOL 100%")
        self.vol_lbl.setStyleSheet(f"color:{C['subtext']};font-size:9pt;border:none;padding:0 4px;")
        self.vol_lbl.setToolTip("Current audio volume level")
        self.toolbar.addWidget(self.vol_lbl)

        # Back-compat aliases
        self.rec_lbl  = self.rec_pill
        self.mute_lbl = self.mute_pill
        self.shot_lbl = QLabel(""); self.shot_lbl.hide()
        self.clip_lbl = QLabel(""); self.clip_lbl.hide()

        # ── Status Bar ────────────────────────────────────────────────────────
        self._build_statusbar()

        # ── Fullscreen floating HUD toolbar ───────────────────────────────────
        self.fs_bar=QWidget(self.video)
        self.fs_bar.setStyleSheet(
            f"QWidget{{background:rgba(13,13,30,215);border-radius:14px;"
            f"border:1px solid {C['border2']};}}"
        )
        self.fs_bar.hide()
        fs_layout=QHBoxLayout(self.fs_bar); fs_layout.setContentsMargins(14,8,14,8); fs_layout.setSpacing(3)

        # Left side: stream info labels
        self._fs_info_lbl=QLabel(""); self._fs_info_lbl.setStyleSheet(
            f"color:{C['text2']};font-size:9pt;background:transparent;border:none;padding:0 10px 0 0;")
        fs_layout.addWidget(self._fs_info_lbl)

        fs_vsep=QFrame(); fs_vsep.setFrameShape(QFrame.VLine)
        fs_vsep.setStyleSheet(f"color:{C['border2']};margin:4px 6px;"); fs_layout.addWidget(fs_vsep)

        # Right side: recording controls
        for text,cmd,oid,tip in [
            ("\u25a0 STOP",     self.stop_stream,      "danger",      "Stop stream"),
            ("\U0001f507 MUTE", self.toggle_mute,      "",            "Mute audio  [M]"),
            ("\u23fa REC",      self.toggle_recording, "danger",      "Record  [F10]"),
            ("\U0001f4f7 SHOT", self.take_screenshot,  "",            "Screenshot  [F12]"),
            ("\U0001f4ca HUD",  self._toggle_overlay,  "",            "Performance overlay  [P]"),
            ("\u29c6 EXIT FS",  self.toggle_fullscreen,"accent",      "Exit fullscreen  [F11/ESC]"),
        ]:
            btn=self._tbtn(text,cmd,tip=tip,small=True)
            if oid: btn.setObjectName(oid)
            fs_layout.addWidget(btn)
        self.fs_bar.adjustSize()

        # Opacity animation for smooth fade
        self._fs_opacity=QGraphicsOpacityEffect(self.fs_bar)
        self.fs_bar.setGraphicsEffect(self._fs_opacity)
        self._fs_anim=QPropertyAnimation(self._fs_opacity, b"opacity")
        self._fs_anim.setDuration(220)
        self._fs_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.video.setMouseTracking(True)
        self.video.mouseMoveEvent=self._video_mouse_move
        self._fs_timer=QTimer(); self._fs_timer.setSingleShot(True)
        self._fs_timer.timeout.connect(self._fs_bar_fade_out)
        self.flash=QLabel(self.video); self.flash.hide()

    def _build_statusbar(self):
        """Build the bottom QStatusBar with segmented status sections."""
        sb=QStatusBar(self); self.setStatusBar(sb)
        sb.setSizeGripEnabled(False)

        # Connection state
        self._sb_conn=QLabel("  \u2b58  Offline  ")
        self._sb_conn.setStyleSheet(f"color:{C['bad']};font-size:9pt;border-right:1px solid {C['border']};")
        self._sb_conn.setToolTip("Stream connection state")
        sb.addWidget(self._sb_conn)

        # Resolution
        self._sb_res=QLabel("  \u2014  ")
        self._sb_res.setStyleSheet(f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};")
        self._sb_res.setToolTip("Capture resolution")
        sb.addWidget(self._sb_res)

        # FPS
        self._sb_fps=QLabel("  \u2014  ")
        self._sb_fps.setStyleSheet(f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};")
        self._sb_fps.setToolTip("Live frame rate")
        sb.addWidget(self._sb_fps)

        # Drop %
        self._sb_drop=QLabel("  DROP: \u2014  ")
        self._sb_drop.setStyleSheet(f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};")
        self._sb_drop.setToolTip("Dropped frame percentage")
        sb.addWidget(self._sb_drop)

        # Audio level
        self._sb_audio=QLabel("  \U0001f50a 100%  ")
        self._sb_audio.setStyleSheet(f"color:{C['text2']};font-size:9pt;border-right:1px solid {C['border']};")
        self._sb_audio.setToolTip("Audio volume level")
        sb.addWidget(self._sb_audio)

        # Record duration (right-aligned via addPermanentWidget)
        self._sb_rec=QLabel("  ")
        self._sb_rec.setStyleSheet(f"color:{C['subtext']};font-size:9pt;")
        sb.addPermanentWidget(self._sb_rec)

        # Notify label (clips/screenshots saved)
        self.notify_lbl=QLabel("")
        self.notify_lbl.setStyleSheet(f"color:{C['text2']};font-size:9pt;")
        sb.addPermanentWidget(self.notify_lbl)

        # Timer to update record duration
        self._rec_start_time=None
        self._rec_timer=QTimer(); self._rec_timer.setInterval(1000)
        self._rec_timer.timeout.connect(self._update_rec_duration)

    def _update_rec_duration(self):
        if self.recorder.recording and self._rec_start_time:
            elapsed=int(time.time()-self._rec_start_time)
            m,s=divmod(elapsed,60); h,m=divmod(m,60)
            dur=f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            self._sb_rec.setText(f"  \u23fa REC {dur}  ")
            self._sb_rec.setStyleSheet(f"color:{C['record']};font-size:9pt;font-weight:bold;")
        else:
            self._sb_rec.setText("  ")
            self._sb_rec.setStyleSheet(f"color:{C['subtext']};font-size:9pt;")

    def _tbtn(self, text, cmd, tip="", small=False):
        """Create a styled push button for use in the fullscreen HUD."""
        btn=QPushButton(text); btn.clicked.connect(cmd)
        btn.setFixedHeight(30 if small else 34)
        btn.setMinimumWidth(50)
        if tip: btn.setToolTip(tip)
        sz="8" if small else "9"
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
        a=QAction(text,self)
        a.triggered.connect(cmd)
        if tip: a.setToolTip(tip); a.setStatusTip(tip)
        if checkable: a.setCheckable(True)
        return a

    def _toolbar_label(self, text):
        """Create a small section label for the toolbar."""
        lbl=QLabel(f"  {text}")
        lbl.setStyleSheet(
            f"color:{C['subtext']};font-size:7pt;font-weight:bold;"
            f"letter-spacing:1.2px;border:none;padding:0 2px;"
        )
        return lbl

    def _vline(self):
        """Thin vertical separator."""
        f=QFrame(); f.setFrameShape(QFrame.VLine)
        f.setFixedWidth(1)
        f.setStyleSheet(f"color:{C['border2']};margin:6px 8px;")
        return f

    def _build_menu(self):
        mb=self.menuBar()
        def menu(t): return mb.addMenu(t)
        def act(m,label,slot,shortcut=None):
            a=QAction(label,self); a.triggered.connect(slot)
            if shortcut: a.setShortcut(QKeySequence(shortcut))
            m.addAction(a); return a

        # ── File ─────────────────────────────────────────────────────────────
        fm=menu("&File")
        act(fm,"\U0001f4c1  Open Save Location",
            lambda:self._open_folder(self.cfg.get("recording_path","")))
        act(fm,"\U0001f4be  Export Clip  [F9]",self.save_clip,"F9")
        fm.addSeparator()
        exit_act=QAction("\u2715  Exit",self); exit_act.triggered.connect(self.close)
        exit_act.setShortcut(QKeySequence("Ctrl+Q")); fm.addAction(exit_act)

        # ── Capture ───────────────────────────────────────────────────────────
        cm=menu("&Capture")
        act(cm,"\u25b6  Start Stream  [F5]",self.start_stream,"F5")
        act(cm,"\u25a0  Stop Stream   [F5]",self.stop_stream)
        cm.addSeparator()
        act(cm,"\u23fa  Start Recording  [F10]",self.start_recording,"F10")
        act(cm,"\u23f9  Stop Recording   [F10]",self.stop_recording)
        cm.addSeparator()
        act(cm,"\U0001f4f7  Take Screenshot  [F12]",self.take_screenshot,"F12")
        act(cm,"\U0001f4be  Save Clip         [F9]",self.save_clip)

        # ── View ─────────────────────────────────────────────────────────────
        vm=menu("&View")
        act(vm,"\u29c6  Fullscreen  [F11]",self.toggle_fullscreen,"F11")
        vm.addSeparator()
        act(vm,"\U0001f4ca  Toggle Overlay  [P]",self._toggle_overlay,"P")
        vm.addSeparator()
        # Upscale toggle
        act(vm,"\U0001f50d  Toggle Upscale",self._open_upscale)
        vm.addSeparator()
        # Zoom
        act(vm,"\u2295  Zoom In",lambda:self.video._zoom_in())
        act(vm,"\u2296  Zoom Out",lambda:setattr(self.video,"_zoom",max(1.0,self.video._zoom/1.1)) or self.video.update())
        act(vm,"\u21ba  Reset Zoom  [Z]",self.video.reset_zoom,"Z")
        vm.addSeparator()
        self._ar_action=QAction("\u2713  Lock Aspect Ratio",self,checkable=True)
        self._ar_action.setChecked(self.cfg.get("aspect_ratio_lock",True))
        self._ar_action.triggered.connect(self._toggle_ar_lock); vm.addAction(self._ar_action)

        # Resolution submenu
        vm.addSeparator()
        rm=vm.addMenu("Resolution"); self._res_actions={}
        for label,val in self.RESOLUTIONS.items():
            a=QAction(label,self,checkable=True); a.setChecked(val==self.cfg.get("resolution","1920x1080"))
            a.triggered.connect(lambda c,v=val:self._set_resolution(v)); rm.addAction(a); self._res_actions[val]=a
        frm=vm.addMenu("Frame Rate"); self._fps_actions={}
        for f in self.FPS_OPTIONS:
            a=QAction(f"{f} fps",self,checkable=True); a.setChecked(f==self.cfg.get("fps",60))
            a.triggered.connect(lambda c,fps=f:self._set_fps(fps)); frm.addAction(a); self._fps_actions[f]=a

        # ── Tools ─────────────────────────────────────────────────────────────
        tm=menu("&Tools")
        act(tm,"\U0001f50a  Audio Settings...",self._open_audio)
        act(tm,"\u25c8  Image Settings...",self._open_image)
        act(tm,"\U0001f50d  Upscale Settings...",self._open_upscale)
        act(tm,"\u23fa  Recording Settings...",self._open_recording)
        act(tm,"\u2699  Device Settings...",self._open_devices)
        tm.addSeparator()
        act(tm,"\U0001f4c1  Open Recordings Folder",
            lambda:self._open_folder(self.cfg.get("recording_path","")))
        act(tm,"\U0001f4f7  Open Screenshots Folder",
            lambda:self._open_folder(self.cfg.get("screenshot_path","")))
        tm.addSeparator()
        act(tm,"\u21ba  Reset Image  [R]",self._reset_image,"R")
        act(tm,"\u21ba  Reset Perf Stats",self.perf.reset)
        tm.addSeparator()
        act(tm,"\U0001f50a  Mute / Unmute  [M]",self.toggle_mute,"M")
        act(tm,"\u25b2  Volume Up  [=]",lambda:self._nudge_vol(0.1),"=")
        act(tm,"\u25bc  Volume Down  [-]",lambda:self._nudge_vol(-0.1),"-")
        tm.addSeparator()
        act(tm,"\u2328  Hotkeys\u2026",self._open_hotkeys)
        tm.addSeparator()
        self._aot_action=QAction("Always on Top",self,checkable=True)
        self._aot_action.setChecked(self.cfg.get("always_on_top",False))
        self._aot_action.triggered.connect(self._toggle_aot); tm.addAction(self._aot_action)

        # ── Help ──────────────────────────────────────────────────────────────
        hm=menu("&Help")
        act(hm,"?  About",self._show_about)

    def _show_ctx_menu(self,pos):
        menu=QMenu(self)
        menu.setStyleSheet(STYLESHEET)

        # Stream section
        start_lbl="\u25a0 Stop Stream  [F5]" if self.running else "\u25b6 Start Stream  [F5]"
        menu.addAction(start_lbl, self.toggle_stream)
        menu.addSeparator()

        # Capture section
        menu.addAction("\U0001f4f7 Screenshot  [F12]", self.take_screenshot)
        copy_act=menu.addAction("\U0001f4cb Copy Frame", self._copy_frame)
        copy_act.setEnabled(self.running)
        menu.addAction("\U0001f4be Save Clip  [F9]", self.save_clip)
        menu.addSeparator()

        # Zoom submenu
        zm=menu.addMenu("\U0001f50d Zoom")
        zm.addAction("\u2295 Zoom In",  lambda:self.video._zoom_in() or self.video.update())
        zm.addAction("\u2296 Zoom Out", lambda:setattr(self.video,"_zoom",max(1.0,self.video._zoom/1.1)) or self.video.update())
        zm.addAction("\u21ba Reset Zoom  [Z]", self.video.reset_zoom)

        menu.addAction("\u29c6 Fullscreen  [F11]", self.toggle_fullscreen)
        menu.addSeparator()

        # Overlay toggle
        overlay_lbl="\U0001f4ca Hide Overlay  [P]" if self.video._overlay_on else "\U0001f4ca Show Overlay  [P]"
        menu.addAction(overlay_lbl, self._toggle_overlay)
        menu.exec(self.video.mapToGlobal(pos))

    def _copy_frame(self):
        """Copy the current video frame to the clipboard as an image."""
        with self._frame_lock: frame=self._raw_frame
        if frame is None: return
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        h,w=rgb.shape[:2]
        img=QImage(rgb.data,w,h,w*3,QImage.Format_RGB888).copy()
        QApplication.clipboard().setPixmap(QPixmap.fromImage(img))

    def _bind_shortcuts(self):
        """(Re-)register all keyboard shortcuts, reading from cfg["hotkeys"] with defaults."""
        hk = self.cfg.get("hotkeys", {})
        def k(action, default): return hk.get(action, default)

        # Map each action key to its slot and config key
        bindings = [
            (k("toggle_stream",    "F5"),  self.toggle_stream),
            (k("save_clip",        "F9"),  self.save_clip),
            (k("toggle_recording", "F10"), self.toggle_recording),
            (k("toggle_fullscreen","F11"), self.toggle_fullscreen),
            (k("screenshot",       "F12"), self.take_screenshot),
            (k("toggle_mute",      "M"),   self.toggle_mute),
            (k("toggle_overlay",   "P"),   self._toggle_overlay),
            (k("reset_image",      "R"),   self._reset_image),
            (k("reset_zoom",       "Z"),   self.video.reset_zoom),
            (k("volume_up",        "="),   lambda: self._nudge_vol(0.1)),
            (k("volume_down",      "-"),   lambda: self._nudge_vol(-0.1)),
            ("Escape", lambda: self.toggle_fullscreen() if self.fs_mode else None),
        ]

        # Delete old shortcuts so re-binding doesn't stack duplicates
        if hasattr(self, "_shortcuts"):
            for sc in self._shortcuts.values():
                try: sc.setEnabled(False); sc.deleteLater()
                except Exception: pass
        self._shortcuts = {}

        for key, slot in bindings:
            if not key:
                continue
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)
            self._shortcuts[key] = sc

        # Exit App shortcut — maps to self.close
        exit_key = k("exit_app", "Ctrl+Q")
        sc_exit = QShortcut(QKeySequence(exit_key), self)
        sc_exit.activated.connect(self.close)
        self._shortcuts[exit_key] = sc_exit

        # Re-apply global hotkeys whenever local shortcuts are rebuilt so the
        # two systems stay in sync (e.g. after the hotkey dialog saves).
        if hasattr(self, "_global_hk"):
            self._apply_global_hotkeys()

    # ── GLOBAL HOTKEY DISPATCH ────────────────────────────────────────────────
    def _on_global_hotkey(self, action_key: str):
        """Slot called (on the Qt main thread via Signal) when a global hotkey fires."""
        actions = {
            "toggle_stream":    self.toggle_stream,
            "save_clip":        self.save_clip,
            "toggle_recording": self.toggle_recording,
            "toggle_fullscreen":self.toggle_fullscreen,
            "screenshot":       self.take_screenshot,
            "toggle_mute":      self.toggle_mute,
            "toggle_overlay":   self._toggle_overlay,
            "reset_image":      self._reset_image,
            "reset_zoom":       self.video.reset_zoom,
            "volume_up":        lambda: self._nudge_vol(0.1),
            "volume_down":      lambda: self._nudge_vol(-0.1),
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
        self.fs_mode=not self.fs_mode
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
        hint=QLabel(
            "\u29c6  FULLSCREEN  \u2022  F11 or ESC to exit  \u2022  Move mouse to bottom edge for HUD",
            self.video
        )
        hint.setStyleSheet(
            f"background:rgba(10,10,30,215);color:{C['text2']};"
            f"border-radius:8px;padding:8px 18px;font-size:9pt;"
            f"border:1px solid {C['border2']};"
        )
        hint.adjustSize()
        hint.move(self.video.width()//2-hint.width()//2, self.video.height()-hint.height()-28)
        hint.show(); QTimer.singleShot(3800,hint.deleteLater)

    def _fs_bar_fade_in(self):
        self._fs_anim.stop()
        self._fs_anim.setStartValue(self._fs_opacity.opacity())
        self._fs_anim.setEndValue(1.0)
        # Disconnect any lingering done-handler before restarting
        try: self._fs_anim.finished.disconnect(self._on_fs_fade_done)
        except Exception: pass
        self._fs_anim.start()
        self.fs_bar.show(); self.fs_bar.raise_()

    def _fs_bar_fade_out(self):
        self._fs_anim.stop()
        self._fs_anim.setStartValue(self._fs_opacity.opacity())
        self._fs_anim.setEndValue(0.0)
        self._fs_anim.finished.connect(self._on_fs_fade_done)
        self._fs_anim.start()

    def _on_fs_fade_done(self):
        try: self._fs_anim.finished.disconnect(self._on_fs_fade_done)
        except Exception: pass
        if self._fs_opacity.opacity() < 0.05:
            self.fs_bar.hide()

    def _video_mouse_move(self,event):
        VideoWidget.mouseMoveEvent(self.video,event)
        if not self.fs_mode: return
        if event.position().y()>self.video.height()*0.80:
            # Update FS info label before showing
            snap=self.perf.snapshot()
            fps=snap.get("fps",0); drop=snap.get("drop_pct",0)
            res=self.cfg.get("resolution","")
            rec_tag="  \u23fa REC" if self.recorder.recording else ""
            self._fs_info_lbl.setText(
                f"\u25cf {'LIVE' if self.running else 'OFFLINE'}  |  {res}  |  {fps:.0f} fps  |  {drop:.1f}% drop{rec_tag}"
            )
            self.fs_bar.adjustSize()
            w=max(680,self.fs_bar.sizeHint().width()); h=self.fs_bar.sizeHint().height()
            self.fs_bar.setGeometry((self.video.width()-w)//2, self.video.height()-h-14, w, h)
            self._fs_bar_fade_in()
            self._fs_timer.start(3200)
        else:
            if not self._fs_timer.isActive():
                self._fs_timer.start(1600)

    # ── STREAM CONTROL ────────────────────────────────────────────────────────
    def toggle_stream(self):
        if self.running: self.stop_stream()
        else: self.start_stream()

    def start_stream(self):
        if self.running: return
        in_idx=self.cfg.get("audio_input_index",3)
        out_idx=self.cfg.get("audio_output_index",None)
        sr=self.cfg.get("audio_sample_rate",48000)
        self.audio=AudioEngine(in_idx,out_idx,sample_rate=sr)
        self.audio.set_volume(self.cfg.get("volume",1.0))
        if self.cfg.get("muted",False): self.audio.muted=True
        self.audio.start(delay_ms=self.cfg.get("audio_delay_ms",0))
        self.vthread=VideoThread(self.cfg,self.perf)
        self.vthread.frame_ready.connect(self._on_frame)
        self.vthread.error.connect(self._on_video_error)
        self.vthread.start()
        # Apply persisted image settings immediately
        self.vthread.set_image(
            self.cfg.get("brightness",1.0),
            self.cfg.get("contrast",1.0),
            self.cfg.get("saturation",1.0),
        )
        self.running=True; self.perf.reset()
        # Update status pill and toolbar action
        self.status_pill.set_state("\u25cf LIVE", C["live"])
        self.start_action.setText("\u25a0  STOP")
        res=self.cfg.get("resolution","1920x1080")
        self.res_lbl.setText(res.replace("x","\u00d7"))
        self._sb_conn.setText(f"  \u25cf  Live  ")
        self._sb_conn.setStyleSheet(f"color:{C['good']};font-size:9pt;border-right:1px solid {C['border']};font-weight:bold;")
        self._sb_res.setText(f"  {res.replace('x','\u00d7')}  ")
        if self.cfg.get("muted",False):
            self.mute_pill.set_state("\U0001f507 MUTED", C["danger"]); self.mute_pill.show()
        self._update_vol_label()

    def stop_stream(self):
        if not self.running: return
        self.running=False
        if self.recorder.recording: self.stop_recording()
        if self.vthread: self.vthread.stop(); self.vthread=None
        if self.audio: self.audio.stop(); self.audio=None
        # Update status pill and toolbar action
        self.status_pill.set_state("OFFLINE", C["danger"])
        self.start_action.setText("\u25b6  START")
        self.res_lbl.setText("\u2014"); self.fps_lbl.setText("\u2014")
        self.fps_lbl.setStyleSheet(f"color:{C['text2']};font-size:9pt;border:none;padding:0 4px;")
        self._sb_conn.setText("  \u2b58  Offline  ")
        self._sb_conn.setStyleSheet(f"color:{C['bad']};font-size:9pt;border-right:1px solid {C['border']};")
        self._sb_res.setText("  \u2014  ")
        self._sb_fps.setText("  \u2014  ")
        self._sb_drop.setText("  DROP: \u2014  ")
        with self.video._lock: self.video._px=None
        self.video.update()

    def _on_frame(self,frame):
        if not self.running: return
        with self._frame_lock: self._raw_frame=frame.copy()
        self.clip_buf.push(frame)
        if self.recorder.recording: self.recorder.write(frame)
        snap=self.perf.snapshot()
        self.video.set_frame(frame,snap,0.0,self.recorder.recording,
                             self.cfg.get("fps",60),self.cfg.get("upscale_mode","none"),self._sys_data)
        fps=snap.get("fps",0)
        if fps>0:
            drop=snap.get("drop_pct",0)
            if drop>5:      col=C["bad"]
            elif fps>=self.cfg.get("fps",60)*0.95: col=C["good"]
            else:            col=C["warn"]
            self.fps_lbl.setText(f"{fps:.0f} fps")
            self.fps_lbl.setStyleSheet(f"color:{col};font-size:9pt;border:none;padding:0 4px;")
            # Update status bar
            self._sb_fps.setText(f"  {fps:.0f} fps  ")
            self._sb_fps.setStyleSheet(f"color:{col};font-size:9pt;border-right:1px solid {C['border']};")
            drop_col=C["good"] if drop<1 else C["warn"] if drop<5 else C["bad"]
            self._sb_drop.setText(f"  DROP: {drop:.1f}%  ")
            self._sb_drop.setStyleSheet(f"color:{drop_col};font-size:9pt;border-right:1px solid {C['border']};")

    def _on_video_error(self,msg): self.stop_stream(); QMessageBox.critical(self,"No Signal",msg)
    def _on_sys_stats(self,data): self._sys_data=data

    # ── AUDIO ─────────────────────────────────────────────────────────────────
    def toggle_mute(self):
        if not self.audio: return
        m=self.audio.toggle_mute(); self.cfg["muted"]=m
        if m:
            self.mute_pill.set_state("\U0001f507 MUTED", C["danger"]); self.mute_pill.show()
            self._sb_audio.setText("  \U0001f507 MUTED  ")
            self._sb_audio.setStyleSheet(f"color:{C['bad']};font-size:9pt;border-right:1px solid {C['border']};font-weight:bold;")
        else:
            self.mute_pill.hide()
            self._update_vol_label()

    def _nudge_vol(self,d):
        v=max(0.0,min(2.0,self.cfg.get("volume",1.0)+d))
        self.cfg["volume"]=v
        if self.audio: self.audio.set_volume(v)
        self._update_vol_label()

    def _update_vol_label(self):
        v=self.cfg.get("volume",1.0); pct=int(v*100)
        if pct<50:   col=C["warn"]
        elif pct>150: col=C["accent"]
        else:         col=C["subtext"]
        self.vol_lbl.setText(f"VOL {pct}%")
        self.vol_lbl.setStyleSheet(f"color:{col};font-size:9pt;border:none;padding:0 4px;")
        self._sb_audio.setText(f"  \U0001f50a {pct}%  ")
        self._sb_audio.setStyleSheet(f"color:{col};font-size:9pt;border-right:1px solid {C['border']};")

    def _reset_image(self):
        if self.vthread: self.vthread.set_image(1.0,1.0,1.0)

    # ── RECORDING ─────────────────────────────────────────────────────────────
    def toggle_recording(self):
        if self.recorder.recording: self.stop_recording()
        else: self.start_recording()

    def start_recording(self):
        if not self.running: QMessageBox.warning(self,"Recording","Start stream first."); return
        with self._frame_lock: frame=self._raw_frame
        if frame is None: return
        h,w=frame.shape[:2]; ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fmt=self.cfg.get("recording_format","mp4")
        path=os.path.join(self.cfg["recording_path"],f"rec_{ts}.{fmt}")

        # ── Audio recording setup ─────────────────────────────────────────────
        include_audio=self.cfg.get("recording_include_audio",True)
        wav_path=None
        if include_audio and FFMPEG_PATH:
            wav_path=os.path.join(self.cfg["recording_path"],f"tmp_audio_{ts}.wav")
            self._audio_recorder=AudioRecorder(self.cfg)
            self._audio_recorder.start(wav_path)
        else:
            self._audio_recorder=None

        # ── Start video recorder ──────────────────────────────────────────────
        self.recorder.start(
            path,
            self.cfg.get("fps",60), w, h, fmt,
            include_audio=include_audio and bool(FFMPEG_PATH),
            wav_path=wav_path,
            audio_codec=self.cfg.get("recording_audio_codec","aac"),
            audio_bitrate=self.cfg.get("recording_audio_bitrate",320),
        )
        self.rec_pill.set_state("\u23fa REC", C["record"]); self.rec_pill.show()
        self._rec_start_time=time.time(); self._rec_timer.start()

    def stop_recording(self):
        # Stop audio first so it's fully flushed before ffmpeg muxes
        if self._audio_recorder is not None:
            self._audio_recorder.stop()
            self._audio_recorder=None
        path=self.recorder.stop(); self.rec_pill.hide()
        self._rec_timer.stop(); self._rec_start_time=None; self._update_rec_duration()
        if path: QTimer.singleShot(100,lambda:QMessageBox.information(self,"Saved",f"Recording saved:\n{path}"))

    def save_clip(self):
        if not self.running: QMessageBox.warning(self,"Clip","Start stream first."); return
        with self._frame_lock: frame=self._raw_frame
        if frame is None: return
        h,w=frame.shape[:2]; ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        clip_dir=self.cfg.get("clip_path",self.cfg.get("recording_path",""))
        path=os.path.join(clip_dir,f"clip_{ts}.mp4")
        os.makedirs(clip_dir,exist_ok=True)
        self._notify("\U0001f4be Saving clip\u2026", C["clip"])
        self._clip_worker=ClipSaveWorker(self.clip_buf,path,w,h)
        self._clip_worker.finished.connect(self._on_clip_saved)
        self._clip_worker.finished.connect(self._clip_worker.deleteLater)
        self._clip_worker.start()

    def _on_clip_saved(self,result):
        name=os.path.basename(result) if result else "Empty buffer"
        self._notify(f"\U0001f4be Saved: {name}", C["clip"])
        QTimer.singleShot(4000, lambda: self._notify("", C["subtext"]))

    def take_screenshot(self):
        with self._frame_lock: frame=self._raw_frame
        if frame is None: QMessageBox.warning(self,"Screenshot","No frame \u2014 start stream first."); return
        ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
        sfmt=self.cfg.get("screenshot_format","png")
        ext={"png":"png","jpeg":"jpg","webp":"webp"}.get(sfmt,"png")
        path=os.path.join(self.cfg["screenshot_path"],f"capture_{ts}.{ext}")
        os.makedirs(self.cfg["screenshot_path"],exist_ok=True)
        if sfmt=="jpeg":
            q=self.cfg.get("screenshot_jpeg_quality",92)
            ok=cv2.imwrite(path,frame,[cv2.IMWRITE_JPEG_QUALITY,q])
        elif sfmt=="webp":
            ok=cv2.imwrite(path,frame,[cv2.IMWRITE_WEBP_QUALITY,90])
        else:
            ok=cv2.imwrite(path,frame)
        if not ok:
            QMessageBox.warning(self,"Screenshot",f"Failed to write screenshot:\n{path}"); return
        name=os.path.basename(path)
        self._notify(f"\U0001f4f7 {name}", C["screenshot"])
        QTimer.singleShot(4000, lambda: self._notify("", C["subtext"]))
        # White flash effect
        self.flash.setStyleSheet("background:rgba(255,255,255,200);")
        self.flash.setGeometry(self.video.rect()); self.flash.show()
        QTimer.singleShot(80, lambda:self.flash.setStyleSheet("background:rgba(200,200,200,100);"))
        QTimer.singleShot(160, self.flash.hide)

    def _notify(self, text, color):
        """Update the status bar notification area."""
        self.notify_lbl.setText(f"  {text}  " if text else "")
        self.notify_lbl.setStyleSheet(f"color:{color};font-size:9pt;")

    # ── MISC ACTIONS ──────────────────────────────────────────────────────────
    def _toggle_overlay(self):
        on=self.video.toggle_overlay()
        self._overlay_action.setChecked(on)
    def _toggle_ar_lock(self): self.video._ar_lock=self._ar_action.isChecked(); self.cfg["aspect_ratio_lock"]=self.video._ar_lock
    def _set_resolution(self,val): self.cfg["resolution"]=val; [a.setChecked(v==val) for v,a in self._res_actions.items()]
    def _set_fps(self,fps): self.cfg["fps"]=fps; [a.setChecked(f==fps) for f,a in self._fps_actions.items()]
    def _toggle_aot(self):
        on=self._aot_action.isChecked(); self.cfg["always_on_top"]=on
        flags=self.windowFlags()
        if on: flags|=Qt.WindowStaysOnTopHint
        else: flags&=~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags); self.show()
    def _open_folder(self,path): os.makedirs(path,exist_ok=True); os.startfile(path)
    def _open_audio(self): AudioDialog(self,self.cfg,self.audio).exec()
    def _open_image(self): ImageDialog(self,self.vthread,self.cfg).exec()
    def _open_upscale(self):
        dlg=UpscaleDialog(self,self.cfg)
        if dlg.exec(): self.cfg["upscale_mode"]=dlg.mode
    def _open_recording(self):
        dlg=RecordingDialog(self,self.cfg)
        if dlg.exec(): self.clip_buf.update(self.cfg["clip_duration"],self.cfg["fps"])
    def _open_devices(self): DeviceDialog(self,self.cfg).exec()
    def _open_hotkeys(self): HotkeyDialog(self,self.cfg).exec()
    def _show_about(self):
        ram=get_available_ram_gb()
        QMessageBox.information(self,"About",
            f"{APP_NAME}  v{APP_VERSION}\n{APP_TAGLINE}\n\n"
            f"CUDA:  {'yes' if CUDA_AVAILABLE else 'no'}\n"
            f"RAM:   {ram:.1f}GB detected\n\n"
            f"Config: {CONFIG_FILE}")

    def closeEvent(self,event):
        # Unregister all keyboard library hooks first so the low-level hook is
        # released before any other teardown runs.
        self._global_hk.unregister_all()
        self.cfg["geometry"]=bytes(self.saveGeometry().toHex()).decode("ascii")
        save_config(self.cfg); self.stop_stream(); self.sys_stats.stop(); event.accept()

# ── ENTRY POINT ───────────────────────────────────────────────────────────────
def main():
    try: import psutil
    except ImportError: pass
    app=QApplication(sys.argv)
    app.setApplicationName(APP_NAME); app.setApplicationVersion(APP_VERSION); app.setStyle("Fusion")
    win=MainWindow(); win.show(); sys.exit(app.exec())

if __name__=="__main__":
    main()
