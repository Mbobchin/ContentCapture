"""Live video preview widget — paints frames + optional perf overlay HUD."""
import threading
import time

import cv2
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QFont, QPen, QPainterPath,
)
from PySide6.QtWidgets import QLabel, QSizePolicy

from constants import APP_NAME
from cuda_support import CUDA_AVAILABLE
from theme import C


class VideoWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background:#000000;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._px = None
        self._lock = threading.Lock()
        self._overlay_on = False
        self._ar_lock = True
        self._zoom = 1.0
        self._offset = [0.0, 0.0]
        self._drag = None
        self._perf = {}
        self._sys = {}
        self._sfps = self._sdrop = self._sren = self._sgpu = 0.0
        self._target_fps = 60
        self._mode = "none"
        self._rec_active = False
        self.setMouseTracking(True)
        # Frame-skip governor — only repaint at most preview_fps_cap times/sec
        self._last_render = 0.0
        self._render_interval = 1.0 / 30.0   # default 30fps preview

    def set_render_fps(self, fps: int):
        """Set the maximum preview repaint rate (frames per second)."""
        self._render_interval = 1.0 / max(1, int(fps))

    def set_frame(self, frame, perf, gpu_ms, rec, target_fps, mode, sys_data=None):
        # Skip repaint if we rendered too recently
        now = time.perf_counter()
        if now - self._last_render < self._render_interval:
            with self._lock:
                self._perf = perf
                self._sys = sys_data or {}
                self._rec_active = rec
                self._target_fps = target_fps
                self._mode = mode
            return
        self._last_render = now

        h, w = frame.shape[:2]
        if self._zoom > 1.0:
            cw = int(w / self._zoom)
            ch = int(h / self._zoom)
            x0 = max(0, min(w - cw, int(self._offset[0] * (w - cw))))
            y0 = max(0, min(h - ch, int(self._offset[1] * (h - ch))))
            frame = frame[y0:y0 + ch, x0:x0 + cw]
            h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()
        del rgb
        with self._lock:
            self._px = QPixmap.fromImage(img)
            self._perf = perf
            self._sys = sys_data or {}
            self._rec_active = rec
            self._target_fps = target_fps
            self._mode = mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#000000"))
        with self._lock:
            px = self._px
        if px is None:
            # ── Empty state — centered placeholder ───────────────────────────
            cw = self.width()
            ch = self.height()
            painter.setOpacity(0.04)
            pen = QPen(QColor(C["accent"]))
            pen.setWidth(1)
            painter.setPen(pen)
            step = 40
            for x in range(0, cw, step):
                painter.drawLine(x, 0, x, ch)
            for y in range(0, ch, step):
                painter.drawLine(0, y, cw, y)
            painter.setOpacity(1.0)
            bw, bh = 440, 200
            bx = (cw - bw) // 2
            by = (ch - bh) // 2
            path = QPainterPath()
            path.addRoundedRect(QRectF(bx, by, bw, bh), 14, 14)
            painter.fillPath(path, QColor(C["panel2"] + "cc"))
            pen2 = QPen(QColor(C["border2"]))
            pen2.setWidth(1)
            painter.setPen(pen2)
            painter.drawPath(path)
            painter.setFont(QFont("Segoe UI", 32))
            painter.setPen(QColor(C["accent"] + "88"))
            painter.drawText(QRect(bx, by + 20, bw, 60), Qt.AlignCenter, "\u29c6")
            painter.setFont(QFont("Segoe UI", 15, QFont.Bold))
            painter.setPen(QColor(C["text"]))
            painter.drawText(QRect(bx, by + 70, bw, 36), Qt.AlignCenter, APP_NAME)
            painter.setFont(QFont("Segoe UI", 10))
            painter.setPen(QColor(C["text2"]))
            painter.drawText(QRect(bx, by + 108, bw, 28), Qt.AlignCenter, "No device connected")
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(C["subtext"]))
            painter.drawText(
                QRect(bx, by + 136, bw, 24),
                Qt.AlignCenter,
                "Press F5 to start  \u2022  Tools \u2192 Device Settings to configure",
            )
            painter.end()
            return

        cw = self.width()
        ch = self.height()
        sw = px.width()
        sh = px.height()
        if self._ar_lock and sw > 0 and sh > 0:
            src_ar = sw / sh
            dst_ar = cw / ch
            if src_ar > dst_ar:
                dw = cw
                dh = int(cw / src_ar)
            else:
                dh = ch
                dw = int(ch * src_ar)
            ox = (cw - dw) // 2
            oy = (ch - dh) // 2
        else:
            dw, dh, ox, oy = cw, ch, 0, 0
        painter.drawPixmap(ox, oy, dw, dh, px)

        # ── Floating corner HUD overlay ───────────────────────────────────────
        if self._overlay_on and self._perf:
            s = self._perf
            sy = self._sys
            a = 0.15
            self._sfps  = a * s.get("fps", 0)      + (1 - a) * self._sfps
            self._sdrop = a * s.get("drop_pct", 0) + (1 - a) * self._sdrop
            self._sren  = a * s.get("ren_avg", 0)  + (1 - a) * self._sren
            self._sgpu  = a * s.get("gpu_avg", 0)  + (1 - a) * self._sgpu
            fps = self._sfps
            drop = self._sdrop
            ren = self._sren
            gpu = self._sgpu
            tfps = self._target_fps
            mode = self._mode

            def pcol(v, w, b):
                if v is None:
                    return QColor(C["subtext"])
                return QColor(C["good"]) if v < w else QColor(C["warn"]) if v < b else QColor(C["bad"])

            fc = QColor(C["good"]) if fps >= tfps * 0.95 else QColor(C["warn"]) if fps >= tfps * 0.75 else QColor(C["bad"])
            dc = QColor(C["good"]) if drop < 1 else QColor(C["warn"]) if drop < 5 else QColor(C["bad"])
            gpu_tag = " CUDA" if mode == "cuda" and CUDA_AVAILABLE else " CPU"
            rec_tag = "  \u23fa" if self._rec_active else ""
            zm_tag = f"  {self._zoom:.1f}x" if self._zoom > 1.0 else ""

            cpu = sy.get("cpu_pct")
            ram = sy.get("mem_pct")
            gut = sy.get("gpu_util")
            gvr = sy.get("gpu_mem_used")
            cpt = sy.get("cpu_temp")
            gtp = sy.get("gpu_temp")

            sl = [
                (f"FPS  {fps:5.1f}/{tfps}{rec_tag}",       fc),
                (f"DROP {drop:5.1f}%",                     dc),
                (f"REND {ren:5.1f}ms{gpu_tag}{zm_tag}",    fc),
                (f"GPU  {gpu:5.1f}ms",                     fc),
            ]
            yl = [
                (f"CPU  {cpu:.0f}%" if cpu is not None else "CPU  N/A",  pcol(cpu, 60, 85)),
                (f"RAM  {ram:.0f}%" if ram is not None else "RAM  N/A",  pcol(ram, 60, 85)),
                (f"GPU% {gut:.0f}%" if gut is not None else "GPU% N/A",  pcol(gut, 60, 85)),
                (f"VRAM {gvr}MB"    if gvr is not None else "VRAM N/A",  QColor(C["text"])),
                (f"CTMP {cpt}C"     if cpt is not None else "CTMP N/A",  pcol(cpt, 70, 85)),
                (f"GTMP {gtp}C"     if gtp is not None else "GTMP N/A",  pcol(gtp, 70, 85)),
            ]

            font = QFont("Cascadia Code", 9, QFont.Bold)
            if not font.exactMatch():
                font = QFont("Consolas", 9, QFont.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            lh = fm.height() + 4
            pad = 10
            col_w = max(fm.horizontalAdvance(r[0]) for r in sl + yl) + 14
            bw = col_w * 2 + pad * 3
            bh = max(len(sl), len(yl)) * lh + pad * 2 + lh + 6

            hx = ox + 10
            hy = oy + 10

            painter.setRenderHint(QPainter.Antialiasing)
            bg_path = QPainterPath()
            bg_path.addRoundedRect(QRectF(hx, hy, bw, bh), 8, 8)
            painter.setOpacity(0.82)
            painter.fillPath(bg_path, QColor("#080810"))
            painter.setOpacity(1.0)
            border_pen = QPen(QColor(C["border2"]))
            border_pen.setWidth(1)
            painter.setPen(border_pen)
            painter.drawPath(bg_path)

            hf = QFont("Segoe UI", 8, QFont.Bold)
            painter.setFont(hf)
            hfm = painter.fontMetrics()
            painter.setPen(QColor(C["accent"]))
            painter.drawText(hx + pad,           hy + pad + hfm.ascent(), "STREAM")
            painter.drawText(hx + pad + col_w,   hy + pad + hfm.ascent(), "SYSTEM")

            ul_y = hy + pad + hfm.height() + 2
            acc_pen = QPen(QColor(C["accent"] + "66"))
            acc_pen.setWidth(1)
            painter.setPen(acc_pen)
            painter.drawLine(hx + pad,           ul_y, hx + pad + col_w - 8,     ul_y)
            painter.drawLine(hx + pad + col_w,   ul_y, hx + pad + col_w * 2 - 8, ul_y)

            painter.setFont(font)
            base_y = hy + pad + lh + 2
            for i, (line, color) in enumerate(sl):
                y = base_y + i * lh + fm.ascent()
                painter.setPen(QColor(0, 0, 0, 180))
                painter.drawText(hx + pad + 1, y + 1, line)
                painter.setPen(color)
                painter.drawText(hx + pad,     y,     line)
            for i, (line, color) in enumerate(yl):
                y = base_y + i * lh + fm.ascent()
                painter.setPen(QColor(0, 0, 0, 180))
                painter.drawText(hx + pad + col_w + 1, y + 1, line)
                painter.setPen(color)
                painter.drawText(hx + pad + col_w,     y,     line)

            issues = []
            tms = 1000 / max(tfps, 1)
            if fps > 0 and fps < tfps * 0.75:
                issues.append(f"\u26a0 Low FPS ({fps:.0f}) — lower res or close other apps")
            if drop > 5:
                issues.append(f"\u26a0 {drop:.1f}% drops — USB bandwidth issue")
            if ren > tms * 1.5:
                issues.append(f"\u26a0 High render {ren:.0f}ms — try CUDA upscaling or 720p")
            if cpu and cpu > 85:
                issues.append(f"\u26a0 CPU at {cpu:.0f}% — close other apps")
            if ram and ram > 85:
                issues.append(f"\u26a0 RAM at {ram:.0f}% — reduce clip buffer or lower res")
            if gtp and gtp > 85:
                issues.append(f"\u26a0 GPU temp {gtp}C — check cooling")

            df = QFont("Segoe UI", 8)
            painter.setFont(df)
            dfm = painter.fontMetrics()
            msg = issues[0] if issues else "\u2713 Performance healthy"
            msg_col = QColor(C["warn"]) if issues else QColor(C["good"])
            mw = dfm.horizontalAdvance(msg) + 18
            mh = dfm.height() + 8
            diag_y = hy + bh + 5
            diag_path = QPainterPath()
            diag_path.addRoundedRect(QRectF(hx, diag_y, mw, mh), 6, 6)
            painter.setOpacity(0.82)
            painter.fillPath(diag_path, QColor("#080810"))
            painter.setOpacity(1.0)
            painter.setPen(border_pen)
            painter.drawPath(diag_path)
            painter.setPen(QColor(0, 0, 0, 180))
            painter.drawText(hx + 10, diag_y + dfm.ascent() + 4 + 1, msg)
            painter.setPen(msg_col)
            painter.drawText(hx + 10, diag_y + dfm.ascent() + 4,     msg)

        painter.end()

    def wheelEvent(self, event):
        d = 1 if event.angleDelta().y() > 0 else -1
        self._zoom = max(1.0, min(8.0, self._zoom * (1.1 ** d)))
        if self._zoom == 1.0:
            self._offset = [0.0, 0.0]

    def _zoom_in(self):
        self._zoom = max(1.0, min(8.0, self._zoom * 1.1))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.position()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.LeftButton:
            dx = (e.position().x() - self._drag.x()) / self.width()
            dy = (e.position().y() - self._drag.y()) / self.height()
            self._offset[0] = max(0.0, min(1.0, self._offset[0] - dx))
            self._offset[1] = max(0.0, min(1.0, self._offset[1] - dy))
            self._drag = e.position()

    def mouseReleaseEvent(self, e):
        self._drag = None

    def reset_zoom(self):
        self._zoom = 1.0
        self._offset = [0.0, 0.0]

    def toggle_overlay(self):
        self._overlay_on = not self._overlay_on
        return self._overlay_on
