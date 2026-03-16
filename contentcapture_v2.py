"""
ContentCapture v2.0.0
Native Windows — PySide6 + MSMF + WASAPI
No WSL, no usbipd, no PulseAudio.
"""
import sys, os, cv2, time, threading, collections, json, subprocess
import numpy as np
import sounddevice as sd
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QSlider, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QDialog, QRadioButton, QButtonGroup,
    QGroupBox, QGridLayout, QSizePolicy, QSpinBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QFont,
    QAction, QKeySequence, QShortcut
)

APP_NAME    = "ContentCapture"
APP_VERSION = "2.0.0"
APP_TAGLINE = "Capture card viewer for Windows with GPU acceleration"
CONFIG_FILE = os.path.join(os.environ.get("APPDATA",""), "ContentCapture", "config.json")

C = {
    "bg":"#0d0d0f","bg2":"#13131a","panel":"#16161e","panel2":"#1c1c28",
    "border":"#2a2a3d","accent":"#00d4f5","accent_dim":"#007a8c",
    "live":"#00e676","danger":"#ff4757","warning":"#ffa502",
    "text":"#e8e8f0","subtext":"#5a5a7a","hover":"#1e1e2e",
    "record":"#ff4757","clip":"#ff9f43","screenshot":"#e056fd",
    "good":"#00e676","warn":"#ffa502","bad":"#ff4757",
}

STYLESHEET = f"""
QMainWindow,QDialog,QWidget{{background:{C["bg"]};color:{C["text"]};font-family:'Segoe UI';font-size:10pt;}}
QMenuBar{{background:{C["panel"]};color:{C["text"]};border-bottom:1px solid {C["border"]};padding:2px;}}
QMenuBar::item:selected{{background:{C["hover"]};color:{C["accent"]};border-radius:4px;}}
QMenu{{background:{C["panel2"]};color:{C["text"]};border:1px solid {C["border"]};border-radius:6px;padding:4px;}}
QMenu::item{{padding:6px 24px;border-radius:4px;}}
QMenu::item:selected{{background:{C["hover"]};color:{C["accent"]};}}
QMenu::separator{{height:1px;background:{C["border"]};margin:4px 8px;}}
QPushButton{{background:{C["panel2"]};color:{C["text"]};border:1px solid {C["border"]};border-radius:8px;padding:6px 16px;font-size:9pt;}}
QPushButton:hover{{background:{C["hover"]};border-color:{C["accent"]};color:{C["accent"]};}}
QPushButton#accent{{background:{C["accent"]};color:#000;border:none;font-weight:bold;}}
QPushButton#accent:hover{{background:{C["accent_dim"]};color:{C["text"]};}}
QPushButton#danger{{background:{C["danger"]};color:{C["text"]};border:none;}}
QSlider::groove:horizontal{{height:4px;background:{C["border"]};border-radius:2px;}}
QSlider::handle:horizontal{{background:{C["accent"]};width:14px;height:14px;margin:-5px 0;border-radius:7px;}}
QSlider::sub-page:horizontal{{background:{C["accent"]};border-radius:2px;}}
QComboBox{{background:{C["panel2"]};color:{C["text"]};border:1px solid {C["border"]};border-radius:6px;padding:4px 8px;}}
QComboBox QAbstractItemView{{background:{C["panel2"]};color:{C["text"]};border:1px solid {C["border"]};selection-background-color:{C["hover"]};selection-color:{C["accent"]};}}
QCheckBox{{color:{C["text"]};spacing:8px;}}
QCheckBox::indicator{{width:16px;height:16px;border:1px solid {C["border"]};border-radius:4px;background:{C["panel2"]};}}
QCheckBox::indicator:checked{{background:{C["accent"]};border-color:{C["accent"]};}}
QRadioButton{{color:{C["text"]};spacing:8px;}}
QRadioButton::indicator{{width:14px;height:14px;border:1px solid {C["border"]};border-radius:7px;background:{C["panel2"]};}}
QRadioButton::indicator:checked{{background:{C["accent"]};border-color:{C["accent"]};}}
QGroupBox{{border:1px solid {C["border"]};border-radius:8px;margin-top:12px;padding-top:8px;color:{C["accent"]};font-weight:bold;}}
QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}
QLabel{{color:{C["text"]};}}
QLineEdit{{background:{C["panel2"]};border:1px solid {C["border"]};border-radius:6px;padding:4px 8px;color:{C["text"]};}}
QLineEdit:focus{{border-color:{C["accent"]};}}
QSpinBox{{background:{C["panel2"]};border:1px solid {C["border"]};border-radius:6px;padding:4px 8px;color:{C["text"]};}}
QListWidget{{background:{C["panel2"]};border:1px solid {C["border"]};border-radius:6px;color:{C["text"]};}}
QListWidget::item:selected{{background:{C["hover"]};color:{C["accent"]};}}
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

DEFAULT_CONFIG = {
    "video_index":0,"audio_input_index":3,"audio_output_index":9,
    "resolution":"1920x1080","fps":60,"volume":1.0,"muted":False,
    "upscale_mode":"none","sharpen":False,"deinterlace":False,
    "screenshot_path":os.path.join(os.environ.get("USERPROFILE","~"),"Pictures","ContentCapture"),
    "recording_path":os.path.join(os.environ.get("USERPROFILE","~"),"Videos","ContentCapture"),
    "clip_duration":30,"recording_format":"mp4",
    "always_on_top":False,"auto_start":True,"geometry":None,"aspect_ratio_lock":True,
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

def cuda_resize(frame, tw, th):
    try:
        import torch, torch.nn.functional as F
        t = torch.from_numpy(frame).permute(2,0,1).unsqueeze(0).float()/255.0
        if torch.cuda.is_available(): t = t.cuda()
        out = F.interpolate(t,size=(th,tw),mode="bilinear",align_corners=False)
        out = (out.squeeze(0).permute(1,2,0).cpu().numpy()*255).astype(np.uint8)
        torch.cuda.empty_cache(); return out
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

def apply_filters(frame,sharpen,deinterlace):
    if deinterlace: frame[1::2]=frame[::2]
    if sharpen:
        frame=cv2.filter2D(frame,-1,np.array([[0,-1,0],[-1,5,-1],[0,-1,0]],dtype=np.float32))
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
            return {"fps":1000/avg(g) if avg(g)>0 else 0,
                    "cap_avg":avg(self.ct),"cap_max":mx(self.ct),
                    "ren_avg":avg(self.rt),"ren_max":mx(self.rt),
                    "gpu_avg":avg(self.gt),"gap_avg":avg(g),"gap_max":mx(g),
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
        res=self.cfg.get("resolution","1920x1080").split("x")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,int(res[0]))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,int(res[1]))
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
                hsv[:,:,1]=np.clip(hsv[:,:,1]*s,0,255)
                frame=cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2BGR)
            frame=apply_filters(frame,sharpen,deinterlace)
            self.frame_ready.emit(frame)
        cap.release()
    def stop(self): self._stop.set(); self.wait(3000)

# ── AUDIO ENGINE ──────────────────────────────────────────────────────────────
class AudioEngine:
    def __init__(self,input_idx,output_idx=None):
        self.input_idx=input_idx; self.output_idx=output_idx
        self.volume=1.0; self.muted=False; self._stream=None; self._lock=threading.Lock()
    def start(self):
        def callback(indata,outdata,frames,time_info,status):
            with self._lock:
                if self.muted: outdata[:]=0
                else: np.copyto(outdata,np.clip(indata.astype(np.float32)*self.volume,-1.0,1.0))
        for in_dev,out_dev in [(self.input_idx,self.output_idx),(self.input_idx,None),(None,None)]:
            try:
                di=sd.query_devices(in_dev if in_dev is not None else sd.default.device[0])
                ch=min(2,int(di["max_input_channels"]))
                self._stream=sd.Stream(samplerate=48000,channels=ch,dtype="float32",
                                       device=(in_dev,out_dev),callback=callback,blocksize=2048)
                self._stream.start()
                print(f"[Audio] Started — input:{in_dev} output:{out_dev} channels:{ch}"); return
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
        with self._lock: self.muted=not self.muted; return self.muted

# ── VIDEO RECORDER ────────────────────────────────────────────────────────────
class VideoRecorder:
    def __init__(self):
        self.writer=None; self.recording=False; self.path=None; self._lock=threading.Lock()
    def start(self,path,fps,w,h,fmt="mp4"):
        with self._lock:
            os.makedirs(os.path.dirname(path),exist_ok=True)
            self.writer=cv2.VideoWriter(path,cv2.VideoWriter_fourcc(*("mp4v" if fmt=="mp4" else "XVID")),fps,(w,h))
            self.recording=True; self.path=path
    def write(self,frame):
        with self._lock:
            if self.recording and self.writer: self.writer.write(frame)
    def stop(self):
        with self._lock:
            if self.writer: self.writer.release(); self.writer=None
            self.recording=False; path=self.path; self.path=None; return path

# ── CLIP BUFFER ───────────────────────────────────────────────────────────────
class ClipBuffer:
    def __init__(self,dur=30,fps=60):
        self._buf=collections.deque(maxlen=dur*fps); self._fps=fps; self._lock=threading.Lock()
    def push(self,f):
        with self._lock: self._buf.append(f.copy())
    def save(self,path,w,h):
        with self._lock: frames=list(self._buf)
        if not frames: return None
        os.makedirs(os.path.dirname(path),exist_ok=True)
        wr=cv2.VideoWriter(path,cv2.VideoWriter_fourcc(*"mp4v"),self._fps,(w,h))
        for f in frames: wr.write(cv2.resize(f,(w,h)))
        wr.release(); return path
    def update(self,dur,fps):
        self._fps=fps
        with self._lock: self._buf=collections.deque(self._buf,maxlen=dur*fps)

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
        with self._lock:
            self._px=QPixmap.fromImage(img)
            self._perf=perf; self._sys=sys_data or {}
            self._rec_active=rec; self._target_fps=target_fps; self._mode=mode
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(),QColor("#000000"))
        with self._lock: px=self._px
        if px is None:
            painter.setPen(QColor(C["subtext"]))
            painter.setFont(QFont("Segoe UI",14))
            painter.drawText(self.rect(),Qt.AlignCenter,
                             f"{APP_NAME} v{APP_VERSION}\n\nPress F5 to start stream")
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

        # ── Detailed perf overlay ─────────────────────────────────────────────
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
            rec_tag="  ⏺" if self._rec_active else ""
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

            font=QFont("Cascadia Code",10,QFont.Bold)
            painter.setFont(font); fm=painter.fontMetrics()
            lh=fm.height()+3; pad=10
            col_w=max(fm.horizontalAdvance(r[0]) for r in sl+yl)+12
            bw=col_w*2+pad*3; bh=max(len(sl),len(yl))*lh+pad*2+lh+4

            painter.setOpacity(0.80)
            painter.fillRect(ox+6,oy+6,bw,bh,QColor("#0d0d0f"))
            painter.setOpacity(1.0)

            hf=QFont("Segoe UI",9,QFont.Bold); painter.setFont(hf)
            hfm=painter.fontMetrics(); painter.setPen(QColor(C["accent"]))
            painter.drawText(ox+6+pad,       oy+6+pad+hfm.ascent(),"STREAM")
            painter.drawText(ox+6+pad+col_w, oy+6+pad+hfm.ascent(),"SYSTEM")
            painter.setFont(font)

            for i,(line,color) in enumerate(sl):
                y=oy+6+pad+lh+i*lh+fm.ascent()
                painter.setPen(QColor("#000")); painter.drawText(ox+7+pad+1,    y+1,line)
                painter.setPen(color);          painter.drawText(ox+7+pad,      y,  line)
            for i,(line,color) in enumerate(yl):
                y=oy+6+pad+lh+i*lh+fm.ascent()
                painter.setPen(QColor("#000")); painter.drawText(ox+7+pad+col_w+1,y+1,line)
                painter.setPen(color);          painter.drawText(ox+7+pad+col_w,  y,  line)

            # ── Diagnostic message ────────────────────────────────────────────
            issues=[]
            tms=1000/max(tfps,1)
            if fps>0 and fps<tfps*0.75: issues.append(f"⚠ Low FPS ({fps:.0f}) — lower res or close other apps")
            if drop>5:                  issues.append(f"⚠ {drop:.1f}% drops — USB bandwidth issue")
            if ren>tms*1.5:            issues.append(f"⚠ High render {ren:.0f}ms — try CUDA upscaling or 720p")
            if cpu and cpu>85:         issues.append(f"⚠ CPU at {cpu:.0f}% — close other apps")
            if ram and ram>85:         issues.append(f"⚠ RAM at {ram:.0f}% — reduce clip buffer or lower res")
            if gtp and gtp>85:         issues.append(f"⚠ GPU temp {gtp}C — check cooling")

            df=QFont("Segoe UI",9); painter.setFont(df); dfm=painter.fontMetrics()
            diag_y=oy+6+bh+8+dfm.ascent()
            msg=issues[0] if issues else "✓ Performance healthy"
            msg_col=QColor(C["warn"]) if issues else QColor(C["good"])
            mw=dfm.horizontalAdvance(msg)+16
            painter.setOpacity(0.80)
            painter.fillRect(ox+6,oy+6+bh+4,mw,dfm.height()+8,QColor("#0d0d0f"))
            painter.setOpacity(1.0)
            painter.setPen(QColor("#000")); painter.drawText(ox+15,diag_y+1,msg)
            painter.setPen(msg_col);        painter.drawText(ox+14,diag_y,  msg)

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

# ── DIALOGS ───────────────────────────────────────────────────────────────────
class BaseDialog(QDialog):
    def __init__(self,parent,title):
        super().__init__(parent); self.setWindowTitle(title)
        self.setStyleSheet(STYLESHEET); self.setMinimumWidth(420)
    def _section(self,label): return QGroupBox(label)
    def _buttons(self,ok_text="Save"):
        bf=QHBoxLayout(); bf.addStretch()
        cancel=QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        ok=QPushButton(ok_text); ok.setObjectName("accent"); ok.clicked.connect(self.accept)
        bf.addWidget(cancel); bf.addWidget(ok); return bf

class AudioDialog(BaseDialog):
    def __init__(self,parent,cfg,audio):
        super().__init__(parent,"Audio Settings")
        layout=QVBoxLayout(self); layout.setSpacing(16)
        title=QLabel("AUDIO SETTINGS")
        title.setStyleSheet(f"color:{C['accent']};font-size:12pt;font-weight:bold;")
        layout.addWidget(title)
        grp=self._section("Volume"); gl=QVBoxLayout(grp)
        vrow=QHBoxLayout(); self.vol_slider=QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0,200); self.vol_slider.setValue(int(cfg.get("volume",1.0)*100))
        vlbl=QLabel(f"{int(cfg.get('volume',1.0)*100)}%"); vlbl.setFixedWidth(40)
        self.vol_slider.valueChanged.connect(lambda v:(vlbl.setText(f"{v}%"),audio.set_volume(v/100) if audio else None,cfg.__setitem__("volume",v/100)))
        vrow.addWidget(QLabel("Volume")); vrow.addWidget(self.vol_slider); vrow.addWidget(vlbl)
        gl.addLayout(vrow)
        mute_cb=QCheckBox("Mute Audio"); mute_cb.setChecked(cfg.get("muted",False))
        mute_cb.stateChanged.connect(lambda s:(cfg.__setitem__("muted",bool(s)),setattr(audio,"muted",bool(s)) if audio else None))
        gl.addWidget(mute_cb); layout.addWidget(grp); layout.addLayout(self._buttons("Close"))
    def accept(self): self.close()

class ImageDialog(BaseDialog):
    def __init__(self,parent,vthread):
        super().__init__(parent,"Image & Filters"); self.vthread=vthread
        self.vals={"brightness":1.0,"contrast":1.0,"saturation":1.0}
        layout=QVBoxLayout(self)
        title=QLabel("IMAGE & FILTERS")
        title.setStyleSheet(f"color:{C['accent']};font-size:12pt;font-weight:bold;")
        layout.addWidget(title); grp=self._section("Adjustments"); gl=QVBoxLayout(grp)
        self.sliders={}
        for key,label,lo,hi in [("brightness","Brightness",20,200),("contrast","Contrast",20,200),("saturation","Saturation",0,200)]:
            row=QHBoxLayout(); lbl=QLabel(label); lbl.setFixedWidth(90)
            sl=QSlider(Qt.Horizontal); sl.setRange(lo,hi); sl.setValue(100)
            val_lbl=QLabel("1.00"); val_lbl.setFixedWidth(36)
            sl.valueChanged.connect(lambda v,k=key,l=val_lbl:self._on_change(k,v,l))
            row.addWidget(lbl); row.addWidget(sl); row.addWidget(val_lbl)
            gl.addLayout(row); self.sliders[key]=sl
        layout.addWidget(grp)
        reset=QPushButton("Reset All"); reset.clicked.connect(self._reset)
        layout.addWidget(reset); layout.addLayout(self._buttons("Close"))
    def _on_change(self,key,val,lbl):
        v=val/100.0; self.vals[key]=v; lbl.setText(f"{v:.2f}")
        if self.vthread: self.vthread.set_image(self.vals["brightness"],self.vals["contrast"],self.vals["saturation"])
    def _reset(self):
        for sl in self.sliders.values(): sl.setValue(100)
    def accept(self): self.close()

class UpscaleDialog(BaseDialog):
    def __init__(self,parent,cfg):
        super().__init__(parent,"Upscaling Settings"); self.mode=cfg.get("upscale_mode","none")
        layout=QVBoxLayout(self)
        title=QLabel("GPU UPSCALING")
        title.setStyleSheet(f"color:{C['accent']};font-size:12pt;font-weight:bold;")
        layout.addWidget(title); grp=self._section("Mode"); gl=QVBoxLayout(grp); self.bg=QButtonGroup()
        for val,label,avail in [
            ("none","Off — no upscaling (fastest)",True),
            ("cuda",f"CUDA Lanczos — GPU resize {'✓' if CUDA_AVAILABLE else '(unavailable)'}",CUDA_AVAILABLE)]:
            rb=QRadioButton(label); rb.setChecked(val==self.mode); rb.setEnabled(avail)
            rb.toggled.connect(lambda c,v=val:setattr(self,"mode",v) if c else None)
            self.bg.addButton(rb); gl.addWidget(rb)
        layout.addWidget(grp); layout.addLayout(self._buttons())

class RecordingDialog(BaseDialog):
    def __init__(self,parent,cfg):
        super().__init__(parent,"Recording Settings"); self.cfg=cfg
        layout=QVBoxLayout(self)
        title=QLabel("RECORDING SETTINGS")
        title.setStyleSheet(f"color:{C['accent']};font-size:12pt;font-weight:bold;")
        layout.addWidget(title); grp=self._section("Paths"); gl=QVBoxLayout(grp)
        rec_row=QHBoxLayout(); self.rec_path=QLineEdit(cfg.get("recording_path",""))
        br=QPushButton("Browse"); br.setFixedWidth(70)
        br.clicked.connect(lambda:self.rec_path.setText(QFileDialog.getExistingDirectory(self,"Recordings") or self.rec_path.text()))
        rec_row.addWidget(QLabel("Recordings:")); rec_row.addWidget(self.rec_path); rec_row.addWidget(br)
        gl.addLayout(rec_row)
        scr_row=QHBoxLayout(); self.scr_path=QLineEdit(cfg.get("screenshot_path",""))
        bs=QPushButton("Browse"); bs.setFixedWidth(70)
        bs.clicked.connect(lambda:self.scr_path.setText(QFileDialog.getExistingDirectory(self,"Screenshots") or self.scr_path.text()))
        scr_row.addWidget(QLabel("Screenshots:")); scr_row.addWidget(self.scr_path); scr_row.addWidget(bs)
        gl.addLayout(scr_row); layout.addWidget(grp)
        grp2=self._section("Format & Duration"); gl2=QVBoxLayout(grp2)
        fmt_row=QHBoxLayout(); self.fmt_bg=QButtonGroup()
        for fmt,label in [("mp4","MP4 (H.264)"),("mkv","MKV (H.264)")]:
            rb=QRadioButton(label); rb.setChecked(fmt==cfg.get("recording_format","mp4"))
            rb.toggled.connect(lambda c,f=fmt:cfg.__setitem__("recording_format",f) if c else None)
            self.fmt_bg.addButton(rb); fmt_row.addWidget(rb)
        gl2.addLayout(fmt_row)
        clip_row=QHBoxLayout(); clip_row.addWidget(QLabel("Clip buffer:"))
        self.clip_spin=QSpinBox(); self.clip_spin.setRange(5,120); self.clip_spin.setSuffix(" sec")
        self.clip_spin.setValue(cfg.get("clip_duration",30))
        clip_row.addWidget(self.clip_spin); clip_row.addStretch()
        gl2.addLayout(clip_row); layout.addWidget(grp2); layout.addLayout(self._buttons())
    def accept(self):
        self.cfg["recording_path"]=self.rec_path.text()
        self.cfg["screenshot_path"]=self.scr_path.text()
        self.cfg["clip_duration"]=self.clip_spin.value(); super().accept()

class DeviceDialog(BaseDialog):
    def __init__(self,parent,cfg):
        super().__init__(parent,"Device Settings"); self.cfg=cfg
        layout=QVBoxLayout(self)
        title=QLabel("DEVICE SETTINGS")
        title.setStyleSheet(f"color:{C['accent']};font-size:12pt;font-weight:bold;")
        layout.addWidget(title); grp=self._section("Capture Devices"); gl=QVBoxLayout(grp)
        gl.addWidget(QLabel("Video Device:")); self.vid_combo=QComboBox()
        for idx,name in find_video_devices():
            self.vid_combo.addItem(name,idx)
            if idx==cfg.get("video_index",0): self.vid_combo.setCurrentIndex(self.vid_combo.count()-1)
        if self.vid_combo.count()==0: self.vid_combo.addItem("No devices found",0)
        gl.addWidget(self.vid_combo)
        gl.addWidget(QLabel("Audio Input Device:")); self.aud_combo=QComboBox()
        for idx,name in find_audio_devices():
            self.aud_combo.addItem(f"[{idx}] {name[:50]}",idx)
            if idx==cfg.get("audio_input_index",3): self.aud_combo.setCurrentIndex(self.aud_combo.count()-1)
        gl.addWidget(self.aud_combo)
        note=QLabel("Changes take effect on next stream start.")
        note.setStyleSheet(f"color:{C['subtext']};font-size:9pt;"); gl.addWidget(note)
        layout.addWidget(grp); layout.addLayout(self._buttons())
    def accept(self):
        self.cfg["video_index"]=self.vid_combo.currentData()
        self.cfg["audio_input_index"]=self.aud_combo.currentData(); super().accept()

# ── MAIN WINDOW ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    RESOLUTIONS={"1920×1080 (1080p)":"1920x1080","1280×720 (720p)":"1280x720","854×480 (480p)":"854x480","640×360 (360p)":"640x360"}
    FPS_OPTIONS=[60,30,24,15]

    def __init__(self):
        super().__init__()
        self.cfg=load_config(); self.perf=PerfTracker()
        self.recorder=VideoRecorder()
        self.clip_buf=ClipBuffer(self.cfg["clip_duration"],self.cfg["fps"])
        self.audio=None; self.vthread=None; self.running=False
        self._raw_frame=None; self._frame_lock=threading.Lock(); self._sys_data={}
        self.fs_mode=False
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

    def _build_ui(self):
        central=QWidget(); self.setCentralWidget(central)
        root=QVBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        self.topbar=QWidget(); self.topbar.setFixedHeight(42)
        self.topbar.setStyleSheet(f"background:{C['panel']};border-bottom:1px solid {C['border']};")
        tb=QHBoxLayout(self.topbar); tb.setContentsMargins(12,0,12,0)
        title=QLabel(f"  ⬡  {APP_NAME.upper()}")
        title.setStyleSheet(f"color:{C['accent']};font-size:12pt;font-weight:bold;border:none;")
        tb.addWidget(title); tb.addStretch()
        self.status_lbl=QLabel("● OFFLINE"); self.status_lbl.setStyleSheet(f"color:{C['danger']};font-weight:bold;border:none;")
        self.res_lbl=QLabel("—"); self.res_lbl.setStyleSheet(f"color:{C['subtext']};border:none;")
        self.fps_lbl=QLabel("—"); self.fps_lbl.setStyleSheet(f"color:{C['subtext']};border:none;")
        self.rec_lbl=QLabel(""); self.rec_lbl.setStyleSheet(f"color:{C['record']};font-weight:bold;border:none;")
        self.mute_lbl=QLabel(""); self.mute_lbl.setStyleSheet(f"color:{C['danger']};border:none;")
        self.vol_lbl=QLabel("VOL 100%"); self.vol_lbl.setStyleSheet(f"color:{C['subtext']};border:none;")
        self.shot_lbl=QLabel(""); self.shot_lbl.setStyleSheet(f"color:{C['screenshot']};border:none;")
        self.clip_lbl=QLabel(""); self.clip_lbl.setStyleSheet(f"color:{C['clip']};border:none;")
        for w in [self.status_lbl,self.res_lbl,self.fps_lbl,self.vol_lbl,
                  self.mute_lbl,self.rec_lbl,self.clip_lbl,self.shot_lbl]:
            tb.addWidget(w); tb.addSpacing(10)
        root.addWidget(self.topbar)
        self.video=VideoWidget(); self.video._ar_lock=self.cfg.get("aspect_ratio_lock",True)
        self.video.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video.customContextMenuRequested.connect(self._show_ctx_menu)
        root.addWidget(self.video,stretch=1)
        self.bottombar=QWidget(); self.bottombar.setFixedHeight(48)
        self.bottombar.setStyleSheet(f"background:{C['panel']};border-top:1px solid {C['border']};")
        bb=QHBoxLayout(self.bottombar); bb.setContentsMargins(8,4,8,4); bb.setSpacing(6)
        self.start_btn=self._tbtn("▶  START",self.toggle_stream,C["live"],"#000")
        self.start_btn.setFixedWidth(110); bb.addWidget(self.start_btn)
        for text,cmd,color,tc in [
            ("🔇  MUTE",   self.toggle_mute,       C["panel2"],    C["text"]),
            ("⏺  REC",    self.toggle_recording,  C["record"],    C["text"]),
            ("💾  CLIP",   self.save_clip,          C["clip"],      "#000"),
            ("📷  SHOT",   self.take_screenshot,   C["screenshot"],"#000"),
            ("🔍  UPSCALE",self._open_upscale,     C["accent_dim"],C["text"]),
            ("📊  OVERLAY",self._toggle_overlay,   C["warning"],   "#000"),
            ("⛶  FULL",   self.toggle_fullscreen, C["panel2"],    C["text"]),
        ]: bb.addWidget(self._tbtn(text,cmd,color,tc))
        bb.addStretch(); bb.addWidget(QLabel("Right-click for menu"))
        root.addWidget(self.bottombar)
        self.fs_bar=QWidget(self)
        self.fs_bar.setStyleSheet(f"background:{C['panel2']};border-radius:10px;border:1px solid {C['border']};")
        self.fs_bar.hide()
        fs_layout=QHBoxLayout(self.fs_bar); fs_layout.setContentsMargins(8,6,8,6); fs_layout.setSpacing(6)
        for text,cmd,color,tc in [
            ("■ STOP",    self.stop_stream,       C["danger"],    C["text"]),
            ("🔇 MUTE",   self.toggle_mute,       C["panel"],     C["text"]),
            ("⏺ REC",    self.toggle_recording,  C["record"],    C["text"]),
            ("📷 SHOT",   self.take_screenshot,   C["screenshot"],"#000"),
            ("📊 OVERLAY",self._toggle_overlay,   C["warning"],   "#000"),
            ("⛶ EXIT",   self.toggle_fullscreen, C["panel"],     C["text"]),
        ]: fs_layout.addWidget(self._tbtn(text,cmd,color,tc,small=True))
        self.fs_bar.adjustSize()
        self.video.setMouseTracking(True)
        self.video.mouseMoveEvent=self._video_mouse_move
        self._fs_timer=QTimer(); self._fs_timer.setSingleShot(True)
        self._fs_timer.timeout.connect(self.fs_bar.hide)
        self.flash=QLabel(self.video); self.flash.hide()

    def _tbtn(self,text,cmd,bg,fg,small=False):
        btn=QPushButton(text); btn.clicked.connect(cmd)
        btn.setFixedHeight(32 if not small else 28)
        btn.setStyleSheet(
            f"QPushButton{{background:{bg};color:{fg};border:none;border-radius:8px;"
            f"padding:0 12px;font-size:{'8' if small else '9'}pt;font-weight:bold;}}"
            f"QPushButton:hover{{background:{C['hover']};color:{C['accent']};}}")
        return btn

    def _build_menu(self):
        mb=self.menuBar()
        def menu(t): return mb.addMenu(t)
        def act(m,label,slot): a=QAction(label,self); a.triggered.connect(slot); m.addAction(a); return a

        sm=menu("Stream")
        act(sm,"▶  Start  [F5]",self.start_stream); act(sm,"■  Stop   [F5]",self.stop_stream); sm.addSeparator()
        rm=sm.addMenu("Resolution"); self._res_actions={}
        for label,val in self.RESOLUTIONS.items():
            a=QAction(label,self,checkable=True); a.setChecked(val==self.cfg.get("resolution","1920x1080"))
            a.triggered.connect(lambda c,v=val:self._set_resolution(v)); rm.addAction(a); self._res_actions[val]=a
        fm=sm.addMenu("Frame Rate"); self._fps_actions={}
        for f in self.FPS_OPTIONS:
            a=QAction(f"{f} fps",self,checkable=True); a.setChecked(f==self.cfg.get("fps",60))
            a.triggered.connect(lambda c,fps=f:self._set_fps(fps)); fm.addAction(a); self._fps_actions[f]=a
        sm.addSeparator(); act(sm,"⛶  Fullscreen [F11]",self.toggle_fullscreen); sm.addSeparator(); act(sm,"✕  Quit",self.close)

        am=menu("Audio"); act(am,"♪  Audio Settings...",self._open_audio); am.addSeparator()
        act(am,"🔇  Mute/Unmute [M]",self.toggle_mute)
        act(am,"▲  Vol Up  [=]",lambda:self._nudge_vol(0.1))
        act(am,"▼  Vol Down [-]",lambda:self._nudge_vol(-0.1))

        im=menu("Image"); act(im,"◈  Image & Filters...",self._open_image); im.addSeparator()
        act(im,"↺  Reset Image [R]",self._reset_image)

        vm=menu("Video")
        act(vm,"⏺  Start Recording [F10]",self.start_recording)
        act(vm,"⏹  Stop Recording  [F10]",self.stop_recording); vm.addSeparator()
        act(vm,"💾  Save Clip [F9]",self.save_clip); vm.addSeparator()
        act(vm,"⚙  Recording Settings...",self._open_recording)
        act(vm,"📁  Open Recordings Folder",lambda:self._open_folder(self.cfg["recording_path"]))

        scm=menu("Screenshot"); act(scm,"📷  Take Screenshot [F12]",self.take_screenshot); scm.addSeparator()
        act(scm,"📁  Open Screenshot Folder",lambda:self._open_folder(self.cfg["screenshot_path"]))

        om=menu("Overlay"); act(om,"📊  Toggle Perf Overlay [P]",self._toggle_overlay); om.addSeparator()
        act(om,"🔍  Upscaling Settings...",self._open_upscale); om.addSeparator()
        act(om,"⊕  Zoom In",lambda:self.video._zoom_in())
        act(om,"↺  Reset Zoom [Z]",self.video.reset_zoom); om.addSeparator()
        self._ar_action=QAction("✓  Lock Aspect Ratio",self,checkable=True)
        self._ar_action.setChecked(self.cfg.get("aspect_ratio_lock",True))
        self._ar_action.triggered.connect(self._toggle_ar_lock); om.addAction(self._ar_action)

        pm=menu("Performance"); act(pm,"📊  Toggle Perf Overlay [P]",self._toggle_overlay)
        pm.addSeparator(); act(pm,"↺  Reset Stats",self.perf.reset)

        stm=menu("Settings"); act(stm,"⚙  Device Settings...",self._open_devices); stm.addSeparator()
        self._aot_action=QAction("Always on Top",self,checkable=True)
        self._aot_action.setChecked(self.cfg.get("always_on_top",False))
        self._aot_action.triggered.connect(self._toggle_aot); stm.addAction(self._aot_action)
        stm.addSeparator(); act(stm,"?  About",self._show_about)

    def _show_ctx_menu(self,pos):
        menu=QMenu(self)
        for label,cmd in [("▶ Start/■ Stop [F5]",self.toggle_stream),("⏺ Record [F10]",self.toggle_recording),
                          ("💾 Save Clip [F9]",self.save_clip),("📷 Screenshot [F12]",self.take_screenshot),
                          ("🔇 Mute [M]",self.toggle_mute)]: menu.addAction(label,cmd)
        menu.addSeparator()
        for label,cmd in [("◈ Image & Filters",self._open_image),("🔍 Upscaling",self._open_upscale),
                          ("📊 Toggle Perf Overlay",self._toggle_overlay),("↺ Reset Zoom",self.video.reset_zoom)]:
            menu.addAction(label,cmd)
        menu.addSeparator(); menu.addAction("⛶ Fullscreen [F11]",self.toggle_fullscreen)
        menu.exec(self.video.mapToGlobal(pos))

    def _bind_shortcuts(self):
        for key,slot in [
            ("F5",self.toggle_stream),("F9",self.save_clip),("F10",self.toggle_recording),
            ("F11",self.toggle_fullscreen),("F12",self.take_screenshot),
            ("M",self.toggle_mute),("P",self._toggle_overlay),("R",self._reset_image),
            ("Z",self.video.reset_zoom),("=",lambda:self._nudge_vol(0.1)),
            ("-",lambda:self._nudge_vol(-0.1)),
            ("Escape",lambda:self.toggle_fullscreen() if self.fs_mode else None)]:
            QShortcut(QKeySequence(key),self).activated.connect(slot)

    def toggle_fullscreen(self):
        self.fs_mode=not self.fs_mode
        if self.fs_mode:
            self.topbar.hide(); self.bottombar.hide(); self.showFullScreen(); self._show_fs_hint()
        else:
            self.topbar.show(); self.bottombar.show(); self.showNormal(); self.fs_bar.hide()

    def _show_fs_hint(self):
        hint=QLabel("Press F11 or ESC to exit fullscreen  •  Move mouse to bottom for toolbar",self.video)
        hint.setStyleSheet(f"background:rgba(13,13,15,180);color:{C['subtext']};border-radius:6px;padding:6px 12px;font-size:10pt;")
        hint.adjustSize()
        hint.move(self.video.width()//2-hint.width()//2,self.video.height()-hint.height()-20)
        hint.show(); QTimer.singleShot(3000,hint.deleteLater)

    def _video_mouse_move(self,event):
        VideoWidget.mouseMoveEvent(self.video,event)
        if not self.fs_mode: return
        if event.position().y()>self.video.height()*0.82:
            w=560; h=self.fs_bar.sizeHint().height()
            self.fs_bar.setGeometry((self.video.width()-w)//2,self.video.height()-h-10,w,h)
            self.fs_bar.show(); self.fs_bar.raise_(); self._fs_timer.start(3000)

    def toggle_stream(self):
        if self.running: self.stop_stream()
        else: self.start_stream()

    def start_stream(self):
        if self.running: return
        in_idx=self.cfg.get("audio_input_index",3); out_idx=self.cfg.get("audio_output_index",9)
        self.audio=AudioEngine(in_idx,out_idx)
        self.audio.set_volume(self.cfg.get("volume",1.0))
        if self.cfg.get("muted",False): self.audio.muted=True
        self.audio.start()
        self.vthread=VideoThread(self.cfg,self.perf)
        self.vthread.frame_ready.connect(self._on_frame)
        self.vthread.error.connect(self._on_video_error)
        self.vthread.start()
        self.running=True; self.perf.reset()
        self.status_lbl.setText("● LIVE"); self.status_lbl.setStyleSheet(f"color:{C['live']};font-weight:bold;border:none;")
        self.start_btn.setText("■  STOP")
        self.start_btn.setStyleSheet(f"QPushButton{{background:{C['danger']};color:{C['text']};border:none;border-radius:8px;padding:0 12px;font-size:9pt;font-weight:bold;}}QPushButton:hover{{background:{C['hover']};color:{C['accent']};}}")
        self.res_lbl.setText(self.cfg.get("resolution","1920x1080").replace("x","×"))

    def stop_stream(self):
        if not self.running: return
        self.running=False
        if self.recorder.recording: self.stop_recording()
        if self.vthread: self.vthread.stop(); self.vthread=None
        if self.audio: self.audio.stop(); self.audio=None
        self.status_lbl.setText("● OFFLINE"); self.status_lbl.setStyleSheet(f"color:{C['danger']};font-weight:bold;border:none;")
        self.start_btn.setText("▶  START")
        self.start_btn.setStyleSheet(f"QPushButton{{background:{C['live']};color:#000;border:none;border-radius:8px;padding:0 12px;font-size:9pt;font-weight:bold;}}QPushButton:hover{{background:{C['hover']};color:{C['accent']};}}")
        self.res_lbl.setText("—"); self.fps_lbl.setText("—")
        self.video._px=None; self.video.update()

    def _on_frame(self,frame):
        with self._frame_lock: self._raw_frame=frame.copy()
        self.clip_buf.push(frame)
        if self.recorder.recording: self.recorder.write(frame)
        snap=self.perf.snapshot()
        self.video.set_frame(frame,snap,0.0,self.recorder.recording,
                             self.cfg.get("fps",60),self.cfg.get("upscale_mode","none"),self._sys_data)
        fps=snap.get("fps",0)
        if fps>0:
            col=C["good"] if fps>=self.cfg.get("fps",60)*0.95 else C["warn"]
            self.fps_lbl.setText(f"{fps:.0f} fps")
            self.fps_lbl.setStyleSheet(f"color:{col};border:none;")

    def _on_video_error(self,msg): self.stop_stream(); QMessageBox.critical(self,"No Signal",msg)
    def _on_sys_stats(self,data): self._sys_data=data

    def toggle_mute(self):
        if not self.audio: return
        m=self.audio.toggle_mute(); self.cfg["muted"]=m
        self.mute_lbl.setText("🔇 MUTED" if m else "")

    def _nudge_vol(self,d):
        v=max(0.0,min(2.0,self.cfg.get("volume",1.0)+d)); self.cfg["volume"]=v
        if self.audio: self.audio.set_volume(v)
        self.vol_lbl.setText(f"VOL {int(v*100)}%")

    def _reset_image(self):
        if self.vthread: self.vthread.set_image(1.0,1.0,1.0)

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
        self.recorder.start(path,self.cfg.get("fps",60),w,h,fmt)
        self.rec_lbl.setText("⏺ REC")

    def stop_recording(self):
        path=self.recorder.stop(); self.rec_lbl.setText("")
        if path: QTimer.singleShot(100,lambda:QMessageBox.information(self,"Saved",f"Recording saved:\n{path}"))

    def save_clip(self):
        if not self.running: QMessageBox.warning(self,"Clip","Start stream first."); return
        with self._frame_lock: frame=self._raw_frame
        if frame is None: return
        h,w=frame.shape[:2]; ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path=os.path.join(self.cfg["recording_path"],f"clip_{ts}.mp4")
        os.makedirs(self.cfg["recording_path"],exist_ok=True)
        self.clip_lbl.setText("💾 Saving...")
        self._clip_worker=ClipSaveWorker(self.clip_buf,path,w,h)
        self._clip_worker.finished.connect(self._on_clip_saved)
        self._clip_worker.start()

    def _on_clip_saved(self,result):
        name=os.path.basename(result) if result else "Empty buffer"
        self.clip_lbl.setText(f"💾 {name}")
        QTimer.singleShot(3000,lambda:self.clip_lbl.setText(""))

    def take_screenshot(self):
        with self._frame_lock: frame=self._raw_frame
        if frame is None: QMessageBox.warning(self,"Screenshot","No frame — start stream first."); return
        ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
        path=os.path.join(self.cfg["screenshot_path"],f"capture_{ts}.png")
        os.makedirs(self.cfg["screenshot_path"],exist_ok=True); cv2.imwrite(path,frame)
        name=os.path.basename(path); self.shot_lbl.setText(f"📷 {name}")
        QTimer.singleShot(3000,lambda:self.shot_lbl.setText(""))
        self.flash.setStyleSheet("background:white;"); self.flash.setGeometry(self.video.rect()); self.flash.show()
        QTimer.singleShot(80,lambda:self.flash.setStyleSheet("background:#aaa;"))
        QTimer.singleShot(160,self.flash.hide)

    def _toggle_overlay(self): self.video.toggle_overlay()
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
    def _open_image(self): ImageDialog(self,self.vthread).exec()
    def _open_upscale(self):
        dlg=UpscaleDialog(self,self.cfg)
        if dlg.exec(): self.cfg["upscale_mode"]=dlg.mode
    def _open_recording(self):
        dlg=RecordingDialog(self,self.cfg)
        if dlg.exec(): self.clip_buf.update(self.cfg["clip_duration"],self.cfg["fps"])
    def _open_devices(self): DeviceDialog(self,self.cfg).exec()
    def _show_about(self):
        ram=get_available_ram_gb()
        QMessageBox.information(self,"About",
            f"{APP_NAME}  v{APP_VERSION}\n{APP_TAGLINE}\n\n"
            f"CUDA:  {'✓' if CUDA_AVAILABLE else '✗'}\n"
            f"RAM:   {ram:.1f}GB detected\n\n"
            f"Config: {CONFIG_FILE}")

    def closeEvent(self,event):
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
