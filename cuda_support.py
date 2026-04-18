"""CUDA detection and GPU-accelerated frame helpers.

`check_cuda()` runs at import time so we cache the result, but it is cheap
(only queries the OpenCV / PyTorch APIs — does not touch the capture device).
"""
import time

import cv2
import numpy as np


def check_cuda() -> bool:
    try:
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            print("[CUDA] Available via OpenCV \u2713")
            return True
    except Exception:
        pass
    try:
        import torch
        if torch.cuda.is_available():
            print(f"[CUDA] Available via PyTorch \u2713 ({torch.cuda.get_device_name(0)})")
            torch.cuda.empty_cache()
            return True
    except Exception:
        pass
    print("[CUDA] Not available — CPU fallback")
    return False


CUDA_AVAILABLE = check_cuda()

# Cache PyTorch CUDA availability once at startup so we don't query it per frame.
try:
    import torch as _torch_mod
    _TORCH_CUDA = _torch_mod.cuda.is_available()
except Exception:
    _torch_mod = None
    _TORCH_CUDA = False


def cuda_resize(frame, tw, th):
    try:
        import torch
        import torch.nn.functional as F
        t = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0).float().mul_(1.0 / 255.0)
        if _TORCH_CUDA:
            t = t.cuda(non_blocking=True)
        out = F.interpolate(t, size=(th, tw), mode="bilinear", align_corners=False)
        out = out.squeeze(0).permute(1, 2, 0).mul_(255.0).clamp_(0, 255).byte().cpu().numpy()
        return out
    except Exception:
        return cv2.resize(frame, (tw, th), interpolation=cv2.INTER_LINEAR)


def upscale_frame(frame, mode, tw, th):
    t0 = time.perf_counter()
    if mode == "cuda" and CUDA_AVAILABLE:
        try:
            gpu = cv2.cuda_GpuMat()
            gpu.upload(frame)
            r = cv2.cuda.resize(gpu, (tw, th), interpolation=cv2.INTER_LANCZOS4)
            return r.download(), (time.perf_counter() - t0) * 1000
        except Exception:
            pass
        try:
            return cuda_resize(frame, tw, th), (time.perf_counter() - t0) * 1000
        except Exception:
            pass
    return cv2.resize(frame, (tw, th), interpolation=cv2.INTER_LINEAR), (time.perf_counter() - t0) * 1000
