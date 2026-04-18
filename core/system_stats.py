"""Background thread that polls psutil + nvidia-smi for the overlay HUD."""
import subprocess
import threading

from PySide6.QtCore import QThread, Signal


class SystemStats(QThread):
    """Polls psutil + nvidia-smi only when the overlay is visible.

    Use pause()/resume() to stop/start polling.  Starts paused by default
    because the overlay is off by default.
    """
    updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self._stop = threading.Event()
        self._active = threading.Event()   # only poll when set
        # _active is NOT set here — resume() must be called explicitly

    def pause(self):
        """Stop polling.  The run loop sleeps until resume() is called."""
        self._active.clear()

    def resume(self):
        """Start (or restart) polling immediately."""
        self._active.set()

    def run(self):
        while not self._stop.is_set():
            # Block here (no CPU burn) if overlay is hidden
            if not self._active.wait(timeout=1.0):
                continue          # timed out — loop back and re-check _stop
            d = {}
            try:
                import psutil
                d["cpu_pct"] = psutil.cpu_percent(interval=0.5)
                vm = psutil.virtual_memory()
                d["mem_used_mb"]  = vm.used  // (1024 * 1024)
                d["mem_total_mb"] = vm.total // (1024 * 1024)
                d["mem_pct"]      = vm.percent
            except Exception:
                pass
            try:
                r = subprocess.run(
                    ["nvidia-smi",
                     "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if r.returncode == 0 and r.stdout.strip():
                    p = [x.strip() for x in r.stdout.strip().split(",")]
                    if len(p) >= 5:
                        d["gpu_name"]      = p[0]
                        d["gpu_util"]      = float(p[1])
                        d["gpu_mem_used"]  = int(p[2])
                        d["gpu_mem_total"] = int(p[3])
                        d["gpu_temp"]      = int(p[4])
            except Exception:
                pass
            self.updated.emit(d)
            self._stop.wait(1.0)

    def stop(self):
        self._active.set()   # unblock the wait so the thread can exit cleanly
        self._stop.set()
