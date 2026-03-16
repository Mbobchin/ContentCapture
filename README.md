# ContentCapture v2.0.0

**Capture card viewer for Windows with GPU acceleration**

> Native Windows app — no WSL, no usbipd, no PulseAudio required.
> Just plug in your capture card and double-click.

---

## Requirements

- Windows 10/11
- Any USB capture card
- NVIDIA GPU recommended (CUDA acceleration)
- Python 3.12 (installer handles this)

---

## Installation

1. Right-click `ContentCaptureSetup_v2.bat` → **Run as Administrator**
2. Follow the on-screen steps (~3-5 minutes)
3. Double-click **ContentCapture** on your desktop

That's it. No WSL, no Linux, no terminal needed for daily use.

---

## Features

| Feature | Details |
|---|---|
| Live capture | 1080p60 via Windows MSMF |
| GPU rendering | CUDA Lanczos (NVIDIA) |
| Recording | MP4 / MKV |
| Clip buffer | Save last 10-120 seconds |
| Screenshots | PNG with timestamp |
| Perf overlay | FPS, render, CPU, GPU, RAM, temps |
| Zoom & pan | Scroll wheel + drag |
| Aspect ratio | Auto letterbox/pillarbox |
| Fullscreen | Clean with slide-up toolbar |
| Image controls | Brightness, contrast, saturation |
| Filters | Sharpen, deinterlace |

---

## Default Keybinds

| Key | Action |
|---|---|
| `F5` | Start / Stop stream |
| `F10` | Start / Stop recording |
| `F9` | Save clip |
| `F12` | Screenshot |
| `P` | Toggle performance overlay |
| `M` | Mute / Unmute |
| `=` / `-` | Volume up / down |
| `R` | Reset image |
| `Z` | Reset zoom |
| `Scroll` | Zoom in / out |
| `F11` / `Esc` | Fullscreen |

---

## Troubleshooting

**Black screen / No signal**
Capture card not detected. Check Settings → Device Settings and select the correct video device.

**No audio**
Go to Settings → Audio Settings. If audio is wrong device, use Settings → Device Settings to change input.

**App won't open**
Run `ContentCaptureSetup_v2.bat` again as Administrator.

**Desktop shortcut missing**
Run `CreateShortcut.ps1` in PowerShell.

---

## Changes from v1

| v1 (WSL) | v2 (Native Windows) |
|---|---|
| Requires WSL2 + Ubuntu | No WSL needed |
| usbipd USB passthrough | Direct Windows access |
| PulseAudio for audio | Native WASAPI audio |
| GStreamer pipeline | Windows MSMF |
| Complex setup | Simple installer |
| WSLg window quirks | Native Windows UI |

---

## Built with
Python 3.12 · PySide6 (Qt6) · OpenCV · sounddevice · PyTorch CUDA
