"""Rolling JPEG-compressed frame buffer for instant clip saving."""
import collections
import os
import threading

import cv2
from PySide6.QtCore import QThread, Signal


class ClipBuffer:
    """Rolling frame buffer for instant clip saving.

    Frames are JPEG-compressed on push so each stored frame is ~100-300KB
    instead of ~6MB raw.  At 85 quality this is visually lossless and gives
    a 20-60x RAM reduction.  Falls back to raw copy if encode fails.
    """
    def __init__(self, dur=15, fps=60, jpeg_quality=85):
        self._buf = collections.deque(maxlen=max(1, dur * fps))
        self._fps = fps
        self._jpeg_quality = max(1, min(100, int(jpeg_quality)))
        self._lock = threading.Lock()

    def push(self, f):
        """Encode frame to JPEG bytes and store.  Exception-safe."""
        try:
            ok, buf = cv2.imencode(
                '.jpg', f,
                [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality],
            )
            if ok:
                with self._lock:
                    self._buf.append(buf)
                return
        except Exception as e:
            print(f"[ClipBuffer] JPEG encode failed ({e}), storing raw frame")
        # Fallback: store raw copy (still works, just uses more RAM)
        with self._lock:
            self._buf.append(f.copy())

    def save(self, path, w, h):
        with self._lock:
            items = list(self._buf)
            fps = self._fps
        if not items:
            return None
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        wr = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        if not wr.isOpened():
            print(f"[ClipBuffer] VideoWriter failed to open: {path}")
            return None
        for item in items:
            # item is either a JPEG-compressed numpy bytes array or a raw BGR frame
            if item.ndim == 1:
                try:
                    frame = cv2.imdecode(item, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue
                except Exception as e:
                    print(f"[ClipBuffer] JPEG decode failed: {e}")
                    continue
            else:
                frame = item
            wr.write(cv2.resize(frame, (w, h)))
        wr.release()
        return path

    def update(self, dur, fps, jpeg_quality=None):
        with self._lock:
            self._fps = fps
            if jpeg_quality is not None:
                self._jpeg_quality = max(1, min(100, int(jpeg_quality)))
            self._buf = collections.deque(self._buf, maxlen=max(1, dur * fps))

    def estimated_ram_mb(self, fps, dur, w=1920, h=1080):
        """Rough RAM estimate for UI display.  Quality factor ~= quality/100 * 0.05."""
        raw_mb = w * h * 3 / (1024 * 1024)
        quality_factor = self._jpeg_quality / 100.0 * 0.05
        return int(fps * dur * raw_mb * quality_factor)


class ClipSaveWorker(QThread):
    finished = Signal(str)

    def __init__(self, clip_buf, path, w, h):
        super().__init__()
        self.clip_buf = clip_buf
        self.path = path
        self.w = w
        self.h = h

    def run(self):
        self.finished.emit(self.clip_buf.save(self.path, self.w, self.h) or "")
