# -*- mode: python ; coding: utf-8 -*-
# ContentCapture PyInstaller spec — portable build (no PyTorch/CUDA)

import sys
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

# Collect PySide6 and PyAV fully
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')
av_datas, av_binaries, av_hiddenimports = collect_all('av')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside6_binaries + av_binaries,
    datas=pyside6_datas + av_datas,
    hiddenimports=[
        # PySide6
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'PySide6.QtMultimedia', 'PySide6.QtNetwork',
        # OpenCV
        'cv2',
        # Audio
        'sounddevice', 'soundfile', 'cffi', '_cffi_backend',
        # Optional global hotkey backend
        'keyboard',
        # PyAV
        *av_hiddenimports,
        # PySide6
        *pyside6_hiddenimports,
        # System
        'psutil', 'psutil._pswindows',
        'numpy', 'numpy.core', 'numpy.core._multiarray_umath',
        # ContentCapture package modules — explicitly listed so PyInstaller's
        # static analyzer always picks them up even if dynamic imports change.
        'constants', 'config', 'theme', 'cuda_support', 'devices', 'hotkeys',
        'core', 'core.perf', 'core.video_thread', 'core.audio_engine',
        'core.mic_engine', 'core.recorder', 'core.clip_buffer',
        'core.system_stats',
        'ui', 'ui.main_window',
        'ui.widgets', 'ui.widgets.video_widget', 'ui.widgets.status_pill',
        'ui.dialogs', 'ui.dialogs.base', 'ui.dialogs.about_dialog',
        'ui.dialogs.audio_dialog', 'ui.dialogs.image_dialog',
        'ui.dialogs.upscale_dialog', 'ui.dialogs.recording_dialog',
        'ui.dialogs.device_dialog', 'ui.dialogs.hotkey_dialog',
        # Stdlib used by app
        'json', 'threading', 'collections', 'datetime',
        'subprocess', 'os', 'sys', 'time',
    ],
    excludes=[
        # Exclude PyTorch entirely — app falls back to CPU gracefully
        'torch', 'torchvision', 'torchaudio',
        'torch.cuda', 'torch.nn',
        # Exclude other unused heavy packages
        'matplotlib', 'scipy', 'pandas', 'PIL', 'tkinter',
        'IPython', 'jupyter', 'notebook',
        'wx', 'gtk',
        'test', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ContentCapture',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ContentCapture.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ContentCapture',
)
