"""Config load/save and runtime defaults.

The configuration is a plain dict — there is no global mutable singleton.
Pass it explicitly to whoever needs it.
"""
import json
import os

from constants import CONFIG_FILE


def get_available_ram_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        return 16.0


def get_recommended_settings() -> dict:
    """Return a dict of overrides chosen based on detected RAM."""
    ram = get_available_ram_gb()
    print(f"[RAM] Detected {ram:.1f}GB total RAM")
    if ram < 12:
        print("[RAM] Low memory mode — 720p default, 10s clip buffer")
        return {"clip_duration": 10, "resolution": "1280x720", "preview_fps_cap": 24}
    elif ram < 20:
        print("[RAM] Standard memory mode — 1080p, 15s clip buffer")
        return {"clip_duration": 15, "resolution": "1920x1080", "preview_fps_cap": 30}
    else:
        print("[RAM] High memory mode — 1080p, 20s clip buffer")
        return {"clip_duration": 20, "resolution": "1920x1080", "preview_fps_cap": 30}


DEFAULT_CONFIG = {
    "video_index": 0,
    "audio_input_index": 3,
    "audio_output_index": None,
    "resolution": "1920x1080",
    "fps": 60,
    "volume": 1.0,
    "muted": False,
    "upscale_mode": "none",
    "sharpen": False,
    "deinterlace": False,
    "screenshot_path": os.path.join(os.environ.get("USERPROFILE", "~"), "Pictures", "ContentCapture"),
    "recording_path":  os.path.join(os.environ.get("USERPROFILE", "~"), "Videos",   "ContentCapture"),
    "clip_path":       os.path.join(os.environ.get("USERPROFILE", "~"), "Videos",   "ContentCapture", "Clips"),
    "clip_duration": 15,
    "recording_format": "mp4",
    "screenshot_format": "png",
    "screenshot_jpeg_quality": 92,
    "always_on_top": False,
    "auto_start": True,
    "geometry": None,
    "aspect_ratio_lock": True,
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "audio_sample_rate": 48000,
    "audio_delay_ms": 0,
    "hotkeys": {},
    "global_hotkeys_enabled": False,
    "global_hotkey_actions": [],
    # Audio recording settings
    "recording_include_audio": True,
    "recording_audio_codec": "aac",
    "recording_audio_bitrate": 320,
    # Microphone input (independent from capture-card audio)
    "mic_index": None,
    "mic_enabled": False,
    "mic_muted": False,
    "mic_volume": 1.0,
    # Performance / RAM settings
    "clip_buffer_enabled": False,
    "clip_buffer_jpeg_quality": 85,
    "overlay": False,
    "preview_fps_cap": 30,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    first_run = not os.path.exists(CONFIG_FILE)
    try:
        if not first_run:
            with open(CONFIG_FILE) as f:
                cfg.update(json.load(f))
    except Exception as e:
        print(f"[Config] load failed: {e}")
    if first_run:
        cfg.update(get_recommended_settings())
    return cfg


def save_config(cfg: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[Config] save failed: {e}")
