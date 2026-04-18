"""Microphone input engine — independent stream that mixes into recordings."""
import collections
import threading

import numpy as np
import sounddevice as sd


class MicEngine:
    """Manages a separate microphone input stream, independent of AudioEngine."""

    def __init__(self, cfg):
        self._cfg = cfg
        self._stream = None
        self._lock = threading.Lock()
        self.muted = cfg.get("mic_muted", False)
        self._volume = cfg.get("mic_volume", 1.0)
        self._buf = collections.deque(maxlen=8)   # small ring of recent chunks
        self._recorder_ref = None                  # set by MainWindow during recording

    @property
    def volume(self):
        with self._lock:
            return self._volume

    @volume.setter
    def volume(self, v):
        with self._lock:
            self._volume = max(0.0, min(4.0, float(v)))

    def set_recorder(self, recorder_or_none):
        """Attach or detach a VideoRecorder so mic data is written during recording."""
        self._recorder_ref = recorder_or_none

    def start(self):
        # Only start if BOTH a device is selected AND mic_enabled is True.
        # This prevents any audio from being captured on launch when mic is disabled.
        idx = self._cfg.get("mic_index", None)
        sr  = self._cfg.get("audio_sample_rate", 48000)
        if idx is None or not self._cfg.get("mic_enabled", False):
            return   # mic not configured or explicitly disabled — do nothing

        engine = self

        def _make_callback(stereo):
            def callback(indata, frames, time_info, status):
                # Check mute BEFORE writing to the recorder — when muted,
                # neither monitoring output nor the recording gets mic audio.
                if engine.muted:
                    return
                with engine._lock:
                    vol = engine._volume
                if stereo:
                    chunk = indata * vol
                else:
                    # mono → duplicate to stereo
                    chunk = np.column_stack([indata, indata]) * vol
                np.clip(chunk, -1.0, 1.0, out=chunk)
                engine._buf.append(chunk.copy())
                rec = engine._recorder_ref
                if rec is not None:
                    try:
                        rec.write_mic(chunk)
                    except Exception:
                        pass
            return callback

        # Try stereo first; some capture-card devices expose only mono
        for channels in (2, 1):
            try:
                cb = _make_callback(stereo=(channels == 2))
                self._stream = sd.InputStream(
                    device=idx,
                    channels=channels,
                    samplerate=sr,
                    dtype="float32",
                    blocksize=2048,
                    callback=cb,
                )
                self._stream.start()
                print(f"[Mic] Started — device index {idx}  channels:{channels}  rate:{sr}")
                return
            except Exception as e:
                print(f"[Mic] Failed with channels={channels}: {e}")
                self._stream = None

        print("[Mic] Could not open microphone device — mic disabled for this session")

    def stop(self):
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted

    def is_running(self):
        return self._stream is not None and self._stream.active
