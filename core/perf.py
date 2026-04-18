"""Per-frame performance tracker — capture / render / GPU times and FPS."""
import collections
import threading
import time


class PerfTracker:
    W = 60

    def __init__(self):
        self.ct = collections.deque(maxlen=self.W)
        self.rt = collections.deque(maxlen=self.W)
        self.gt = collections.deque(maxlen=self.W)
        self.fg = collections.deque(maxlen=self.W)
        self.dropped = self.total = 0
        self._last = None
        self._lock = threading.Lock()

    def rc(self, ms):
        with self._lock:
            self.ct.append(ms)
            self.total += 1
            if self._last:
                self.fg.append((time.perf_counter() - self._last) * 1000)
            self._last = time.perf_counter()

    def rd(self):
        with self._lock:
            self.dropped += 1
            self.total += 1

    def rr(self, ms):
        with self._lock:
            self.rt.append(ms)

    def rg(self, ms):
        with self._lock:
            self.gt.append(ms)

    def snapshot(self):
        with self._lock:
            def avg(d): return sum(d) / len(d) if d else 0
            def mx(d):  return max(d)         if d else 0
            g = list(self.fg)
            gap_avg = avg(g)
            return {
                "fps":      1000 / gap_avg if gap_avg > 0 else 0,
                "cap_avg":  avg(self.ct),
                "cap_max":  mx(self.ct),
                "ren_avg":  avg(self.rt),
                "ren_max":  mx(self.rt),
                "gpu_avg":  avg(self.gt),
                "gap_avg":  gap_avg,
                "gap_max":  mx(g),
                "dropped":  self.dropped,
                "total":    self.total,
                "drop_pct": (self.dropped / self.total * 100) if self.total else 0,
            }

    def reset(self):
        with self._lock:
            self.ct.clear()
            self.rt.clear()
            self.gt.clear()
            self.fg.clear()
            self.dropped = self.total = 0
            self._last = None
