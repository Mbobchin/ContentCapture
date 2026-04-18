"""Capture-card audio engine — input + monitoring output via sounddevice (WASAPI)."""
import collections
import threading

import numpy as np
import sounddevice as sd


class AudioEngine:
    def __init__(self, input_idx, output_idx=None, sample_rate=48000):
        self.input_idx = input_idx
        self.output_idx = output_idx
        self.sample_rate = sample_rate
        self.volume = 1.0
        self.muted = False
        self._stream = None
        self._in_stream = None
        self._out_stream = None
        self._lock = threading.Lock()
        self._audio_buf = None
        # AV sync delay line
        self._delay_ms = 0
        self._delay_buf = collections.deque()
        self._samples_to_skip = 0
        # Recording hook — set by MainWindow.start_recording() / stop_recording()
        self._recorder_ref = None

    def set_recorder(self, recorder_or_none):
        """Attach or detach a VideoRecorder so the audio callback can feed it.
        Safe to call from the UI thread at any time."""
        self._recorder_ref = recorder_or_none

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
            # ── Feed recorder first (always, regardless of mute/delay) ────────
            rec = engine._recorder_ref
            if rec is not None:
                try:
                    rec.write_audio(indata)
                except Exception:
                    pass

            # ── Volume / mute pre-process into a scratch buffer ───────────────
            if engine._audio_buf is None or engine._audio_buf.shape != outdata.shape:
                engine._audio_buf = np.empty_like(outdata)
            with engine._lock:
                muted = engine.muted
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
                            engine._delay_buf[0] = chunk[take:]
                    if remaining > 0:
                        outdata[out_pos:] = 0
                return

            # ── Negative delay: skip ahead by discarding samples ──────────────
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

        # Resolve input/output indices — never leave as None when a preference exists.
        # sounddevice may silently pick the system microphone if we pass None.
        resolved_in  = self.input_idx  if self.input_idx  is not None else sd.default.device[0]
        resolved_out = self.output_idx if self.output_idx is not None else sd.default.device[1]

        attempt_pairs = [
            (resolved_in,  self.output_idx if self.output_idx is not None else resolved_out),
            (resolved_in,  resolved_out),
            (resolved_in,  sd.default.device[1]),
            (sd.default.device[0], sd.default.device[1]),
        ]

        for in_dev, out_dev in attempt_pairs:
            try:
                in_info  = sd.query_devices(in_dev  if in_dev  is not None else sd.default.device[0])
                out_info = sd.query_devices(out_dev if out_dev is not None else sd.default.device[1])
                print(f"[Audio] Opening input: {in_info['name']!r}, output: {out_info['name']!r}")
                ch = min(2, int(in_info["max_input_channels"]))
                if ch == 0:
                    print(f"[Audio] Device {in_dev!r} has no input channels - skipping")
                    continue

                # Use separate InputStream + OutputStream instead of duplex.
                # sd.Stream fails when input and output are on different PortAudio host
                # APIs (e.g. WASAPI input + MME output) with error -9993.
                _out_stream_ref = [None]

                def _in_callback(indata, frames, time_info, status):
                    fake_out = np.zeros_like(indata)
                    callback(indata, fake_out, frames, time_info, status)
                    out_s = _out_stream_ref[0]
                    if out_s is not None and out_s.active:
                        try:
                            out_s.write(fake_out)
                        except Exception:
                            pass

                out_ch = min(2, int(out_info["max_output_channels"])) or ch
                self._out_stream = sd.OutputStream(
                    samplerate=sr, channels=out_ch, dtype="float32",
                    device=out_dev, blocksize=2048,
                )
                self._out_stream.start()
                _out_stream_ref[0] = self._out_stream

                self._in_stream = sd.InputStream(
                    samplerate=sr, channels=ch, dtype="float32",
                    device=in_dev, callback=_in_callback, blocksize=2048,
                )
                self._in_stream.start()
                # Keep _stream pointing to the input stream for backwards compatibility
                self._stream = self._in_stream

                print(f"[Audio] Started - input:{in_dev} output:{out_dev} channels:{ch} rate:{sr}")
                return
            except Exception as e:
                print(f"[Audio] Attempt failed (in:{in_dev} out:{out_dev}): {e}")
                # Clean up any partially opened streams before retrying
                try:
                    if self._out_stream is not None:
                        self._out_stream.stop()
                        self._out_stream.close()
                        self._out_stream = None
                except Exception:
                    pass
                if in_dev == self.input_idx and self.input_idx is not None:
                    print(
                        f"[Audio] NOTE: Configured input device index {self.input_idx} failed. "
                        f"Check Device Settings -> Audio input."
                    )
        print("[Audio] All attempts failed - running without audio")

    def stop(self):
        # Stop and close both the input and output streams separately.
        if self._in_stream is not None:
            try:
                self._in_stream.stop()
                self._in_stream.close()
            except Exception:
                pass
            self._in_stream = None
        if self._out_stream is not None:
            try:
                self._out_stream.stop()
                self._out_stream.close()
            except Exception:
                pass
            self._out_stream = None
        self._stream = None

    def set_volume(self, v):
        with self._lock:
            self.volume = float(v)

    def toggle_mute(self):
        with self._lock:
            self.muted = not self.muted
            return self.muted
