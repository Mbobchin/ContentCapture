"""Application-wide constants — names, paths, defaults.

This module has no side effects and imports nothing from the rest of the project.
Safe to import from anywhere.
"""
import os

APP_NAME    = "ContentCapture"
APP_VERSION = "2.4.0"
APP_TAGLINE = "Capture card viewer for Windows with GPU acceleration"

CONFIG_FILE = os.path.join(
    os.environ.get("APPDATA", ""),
    "ContentCapture",
    "config.json",
)

# Resolution presets exposed in the menu / device dialog (label -> value)
RESOLUTIONS = {
    "1920x1080 (1080p)": "1920x1080",
    "1280x720 (720p)":   "1280x720",
    "854x480 (480p)":    "854x480",
    "640x360 (360p)":    "640x360",
}

FPS_OPTIONS = [60, 30, 24, 15]

# Default hotkey table — used by both the hotkey dialog and the main window.
# (action_key, display_name, default_key)
HOTKEY_ACTIONS = [
    ("toggle_stream",     "Toggle Stream",     "F5"),
    ("save_clip",         "Save Clip",         "F9"),
    ("toggle_recording",  "Toggle Recording",  "F10"),
    ("toggle_fullscreen", "Toggle Fullscreen", "F11"),
    ("screenshot",        "Screenshot",        "F12"),
    ("toggle_mute",       "Toggle Mute",       "M"),
    ("toggle_overlay",    "Toggle Overlay",    "P"),
    ("reset_image",       "Reset Image",       "R"),
    ("reset_zoom",        "Reset Zoom",        "Z"),
    ("volume_up",         "Volume Up",         "="),
    ("volume_down",       "Volume Down",       "-"),
    ("exit_app",          "Exit App",          "Ctrl+Q"),
]
