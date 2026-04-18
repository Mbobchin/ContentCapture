"""PyAV-based video recorder — muxes H.264 video and AAC/MP3/PCM audio."""
import os
import threading

import av
import cv2
import numpy as np


class VideoRecorder:
    """Records video frames and audio samples directly to a container file
    (MP4/MKV) using PyAV's bundled FFmpeg libraries.  No external binary needed.
    """

    def __init__(self):
        self.recording = False
        self._container = None
        self._v_stream = None
        self._a_stream = None
        self._lock = threading.Lock()
        self._pts_v = 0
        self._pts_a = 0
        self._sample_rate = 48000
        self._channels = 2
        self._audio_buf = np.empty((0,), dtype=np.float32)
        # Microphone mix buffer — populated by write_mic(), drained in write_audio()
        self._mic_mix_buf = np.empty((0,), dtype=np.float32)
        self.path = None

    def start(self, path, w, h, fps, include_audio=True,
              audio_input_index=None, sample_rate=48000,
              audio_codec="aac", audio_bitrate=320,
              video_quality=18):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._sample_rate = sample_rate
        self._channels = 2
        self._pts_v = 0
        self._pts_a = 0
        self._audio_buf = np.empty((0,), dtype=np.float32)
        self._mic_mix_buf = np.empty((0,), dtype=np.float32)

        try:
            self._container = av.open(path, mode='w')
        except Exception as e:
            print(f"[Recorder] Failed to open container: {e}")
            return

        # Video stream — H.264
        self._v_stream = self._container.add_stream('libx264', rate=fps)
        self._v_stream.width = w
        self._v_stream.height = h
        self._v_stream.pix_fmt = 'yuv420p'
        self._v_stream.options = {'crf': str(video_quality), 'preset': 'fast'}

        # Audio stream (only if requested)
        if include_audio:
            codec_name = {'aac': 'aac', 'mp3': 'libmp3lame', 'pcm': 'pcm_s16le'}.get(audio_codec, 'aac')
            self._a_stream = self._container.add_stream(codec_name, rate=sample_rate)
            self._a_stream.channels = self._channels
            self._a_stream.layout = 'stereo'
            if audio_codec != 'pcm':
                self._a_stream.bit_rate = audio_bitrate * 1000
        else:
            self._a_stream = None

        self.recording = True
        self.path = path
        print(f"[Recorder] PyAV — {w}x{h}@{fps} include_audio={include_audio} -> {path}")

    def write_video(self, frame_bgr):
        """Write a BGR numpy frame."""
        if not self.recording or self._container is None:
            return
        try:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            av_frame = av.VideoFrame.from_ndarray(frame_rgb, format='rgb24')
            av_frame.pts = self._pts_v
            av_frame.time_base = self._v_stream.time_base
            self._pts_v += 1
            with self._lock:
                for pkt in self._v_stream.encode(av_frame):
                    self._container.mux(pkt)
        except Exception as e:
            print(f"[Recorder] Video write error: {e}")

    def write_audio(self, indata_float32):
        """Write a chunk of float32 stereo audio (shape: [N, channels]).
        If mic data is pending in _mic_mix_buf it is additively mixed in."""
        if not self.recording or self._a_stream is None or self._container is None:
            return
        try:
            chunk = indata_float32.astype(np.float32)
            self._audio_buf = np.concatenate([self._audio_buf, chunk.flatten()])
            frame_size = self._a_stream.codec_context.frame_size or 1024
            samples_needed = frame_size * self._channels
            while len(self._audio_buf) >= samples_needed:
                block = self._audio_buf[:samples_needed]
                self._audio_buf = self._audio_buf[samples_needed:]
                block_2d = block.reshape(-1, self._channels)

                # ── Mix mic audio if available ────────────────────────────────
                if len(self._mic_mix_buf) >= samples_needed:
                    mic_block = self._mic_mix_buf[:samples_needed]
                    self._mic_mix_buf = self._mic_mix_buf[samples_needed:]
                    mic_2d = mic_block.reshape(-1, self._channels)
                    block_2d = block_2d + mic_2d
                    np.clip(block_2d, -1.0, 1.0, out=block_2d)
                elif len(self._mic_mix_buf) > 0:
                    have = (len(self._mic_mix_buf) // self._channels) * self._channels
                    if have > 0:
                        mic_partial = self._mic_mix_buf[:have].reshape(-1, self._channels)
                        self._mic_mix_buf = self._mic_mix_buf[have:]
                        rows = mic_partial.shape[0]
                        block_2d[:rows] = block_2d[:rows] + mic_partial
                        np.clip(block_2d, -1.0, 1.0, out=block_2d)

                av_frame = av.AudioFrame.from_ndarray(
                    block_2d.T.copy(), format='fltp', layout='stereo'
                )
                av_frame.sample_rate = self._sample_rate
                av_frame.pts = self._pts_a
                self._pts_a += frame_size
                with self._lock:
                    for pkt in self._a_stream.encode(av_frame):
                        self._container.mux(pkt)
        except Exception as e:
            print(f"[Recorder] Audio write error: {e}")

    def write_mic(self, chunk_float32):
        """Append a float32 stereo mic chunk to the mic mix buffer.
        Called from the MicEngine callback thread — no lock needed because
        numpy concatenation is GIL-held and _mic_mix_buf is only appended
        here and consumed in write_audio (same Python thread model)."""
        if not self.recording or self._a_stream is None:
            return
        try:
            data = chunk_float32.astype(np.float32).flatten()
            self._mic_mix_buf = np.concatenate([self._mic_mix_buf, data])
            # Guard against unbounded growth if capture audio never arrives
            max_samples = self._sample_rate * self._channels * 5  # 5-second cap
            if len(self._mic_mix_buf) > max_samples:
                self._mic_mix_buf = self._mic_mix_buf[-max_samples:]
        except Exception as e:
            print(f"[Recorder] Mic write error: {e}")

    def stop(self):
        if not self.recording:
            return None
        self.recording = False
        path = self.path
        try:
            with self._lock:
                if self._v_stream:
                    for pkt in self._v_stream.encode():
                        self._container.mux(pkt)
                if self._a_stream:
                    for pkt in self._a_stream.encode():
                        self._container.mux(pkt)
                if self._container:
                    self._container.close()
        except Exception as e:
            print(f"[Recorder] Stop error: {e}")
        finally:
            self._container = None
            self._v_stream = None
            self._a_stream = None
            self.path = None
        return path
