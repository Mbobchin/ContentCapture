"""Video / audio device discovery.

Both caches live here.  Callers must NEVER touch `_CACHED_*` directly — use
the public functions instead.  `find_video_devices()` opens hardware, so it
must only be called on explicit user request (e.g. opening Device Settings),
never at import time.
"""
import cv2
import sounddevice as sd

# Module-level device caches — populated once on first lookup or via refresh.
_CACHED_VIDEO_DEVICES = None
_CACHED_AUDIO_DEVICES = None  # list of (index, sd_device_dict) for ALL audio devices


def find_video_devices():
    """Return list of (index, name_str) for available video capture devices.
    Results are cached after the first scan; call refresh_device_cache() to rescan."""
    global _CACHED_VIDEO_DEVICES
    if _CACHED_VIDEO_DEVICES is not None:
        return _CACHED_VIDEO_DEVICES
    devs = []
    for i in range(8):
        cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            devs.append((i, f"Device {i} ({w}x{h})"))
            cap.release()
    _CACHED_VIDEO_DEVICES = devs
    return devs


def find_audio_devices():
    """Return list of (index, name_str) for audio INPUT devices.
    Results are cached; call refresh_device_cache() to rescan."""
    if _CACHED_AUDIO_DEVICES is None:
        populate_audio_cache()
    return [(i, d["name"]) for i, d in _CACHED_AUDIO_DEVICES if d["max_input_channels"] > 0]


def populate_audio_cache():
    """Scan sounddevice and fill _CACHED_AUDIO_DEVICES with (index, device_dict) pairs."""
    global _CACHED_AUDIO_DEVICES
    devs = []
    try:
        for i, d in enumerate(sd.query_devices()):
            devs.append((i, d))
    except Exception as e:
        print(f"[Devices] audio cache populate failed: {e}")
    _CACHED_AUDIO_DEVICES = devs


def get_audio_device_cache():
    """Return the (index, device_dict) list, populating it if needed.
    Used by dialogs that need both input and output device info."""
    if _CACHED_AUDIO_DEVICES is None:
        populate_audio_cache()
    return _CACHED_AUDIO_DEVICES or []


def refresh_device_cache():
    """Clear both device caches so the next lookup rescans."""
    global _CACHED_VIDEO_DEVICES, _CACHED_AUDIO_DEVICES
    _CACHED_VIDEO_DEVICES = None
    _CACHED_AUDIO_DEVICES = None
