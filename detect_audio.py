"""Run during setup to auto-detect capture card audio and save to config."""
import json, os, sys
sys.path.insert(0, r"C:\ContentCapture_v2\venv\Lib\site-packages")

try:
    import sounddevice as sd

    capture_keywords = ("capture","guermok","usb video","hdmi","digital audio interface","usb audio")
    devs = sd.query_devices()
    capture_idx = None
    output_idx  = None

    # Find capture card input
    for i, d in enumerate(devs):
        name = d["name"].lower()
        if d["max_input_channels"] > 0 and any(k in name for k in capture_keywords):
            capture_idx = i
            print(f"[Setup] Capture audio detected: [{i}] {d['name']}")
            break

    if capture_idx is None:
        capture_idx = sd.default.device[0]
        print(f"[Setup] Using default input: [{capture_idx}]")

    # Find default output
    try:
        output_idx = sd.default.device[1]
        print(f"[Setup] Output: [{output_idx}] {devs[output_idx]['name']}")
    except Exception:
        output_idx = None

    # Save to config
    cfg_path = os.path.join(os.environ["APPDATA"], "ContentCapture", "config.json")
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    try:
        with open(cfg_path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    cfg["audio_input_index"]  = capture_idx
    cfg["audio_output_index"] = output_idx
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[Setup] Audio config saved")

except Exception as e:
    print(f"[Setup] Audio detection skipped: {e}")
