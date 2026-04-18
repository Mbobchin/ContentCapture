"""Video capture thread — opens an MSMF device and emits BGR frames."""
import threading
import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal


# Precomputed sharpen kernel — avoids reallocating a NumPy array every frame.
_SHARPEN_KERNEL = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)


def apply_filters(frame, sharpen, deinterlace):
    if deinterlace:
        frame = frame.copy()
        frame[1::2] = frame[::2]
    if sharpen:
        frame = cv2.filter2D(frame, -1, _SHARPEN_KERNEL)
    return frame


class VideoThread(QThread):
    frame_ready = Signal(np.ndarray)
    error       = Signal(str)

    def __init__(self, cfg, perf):
        super().__init__()
        self.cfg = cfg
        self.perf = perf
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._b = self._c = self._s = 1.0

    def set_image(self, b, c, s):
        with self._lock:
            self._b = b
            self._c = c
            self._s = s

    def run(self):
        idx = self.cfg.get("video_index", 0)
        cap = cv2.VideoCapture(idx, cv2.CAP_MSMF)
        if not cap.isOpened():
            self.error.emit(
                f"Could not open video device {idx}.\n"
                "Check Settings \u2192 Device Settings."
            )
            return
        try:
            res = self.cfg.get("resolution", "1920x1080").split("x")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  int(res[0]))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(res[1]))
        except (IndexError, ValueError) as e:
            print(f"[VideoThread] Invalid resolution in config ({e}), using device default")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_FPS, self.cfg.get("fps", 60))
        sharpen     = self.cfg.get("sharpen", False)
        deinterlace = self.cfg.get("deinterlace", False)
        while not self._stop.is_set():
            t0 = time.perf_counter()
            ret, frame = cap.read()
            if not ret:
                self.perf.rd()
                continue
            self.perf.rc((time.perf_counter() - t0) * 1000)
            with self._lock:
                b, c, s = self._b, self._c, self._s
            if b != 1.0 or c != 1.0:
                frame = cv2.convertScaleAbs(frame, alpha=c, beta=(b - 1.0) * 128)
            if s != 1.0:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
                np.multiply(hsv[:, :, 1], s, out=hsv[:, :, 1])
                np.clip(hsv[:, :, 1], 0, 255, out=hsv[:, :, 1])
                frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            frame = apply_filters(frame, sharpen, deinterlace)
            self.frame_ready.emit(frame)
        cap.release()

    def stop(self):
        self._stop.set()
        self.wait(3000)
