@echo off
setlocal EnableDelayedExpansion
title ContentCapture v2.0.0 — Setup
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║         ContentCapture v2.0.0 — Setup               ║
echo  ║   Capture card viewer for Windows with GPU accel.   ║
echo  ║   Native Windows — no WSL required                  ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  This will install everything needed to run ContentCapture v2.
echo  Estimated time: 3-5 minutes.
echo.
pause

:: ── Check Admin ──────────────────────────────────────────────────────────────
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  [ERROR] Please right-click and choose "Run as Administrator"
    pause & exit /b 1
)

:: ── Step 1: Python ───────────────────────────────────────────────────────────
echo.
echo  [1/5] Checking Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo        Installing Python 3.12...
    winget install --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo        Python installed. Please close and rerun this setup.
    pause & exit /b 0
) else (
    echo        Python OK
)

:: ── Step 2: Create venv ───────────────────────────────────────────────────────
echo.
echo  [2/5] Setting up virtual environment...
if not exist "C:\ContentCapture_v2\venv\" (
    python -m venv C:\ContentCapture_v2\venv
    echo        Virtual environment created OK
) else (
    echo        Virtual environment already exists OK
)

:: Allow scripts to run
powershell -Command "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force" >nul 2>&1

:: ── Step 3: Install dependencies ─────────────────────────────────────────────
echo.
echo  [3/5] Installing dependencies (this may take a few minutes)...
C:\ContentCapture_v2\venv\Scripts\pip.exe install ^
    PySide6 opencv-python numpy sounddevice pillow psutil ^
    --quiet
echo        Core packages installed OK

echo        Installing PyTorch with CUDA support...
C:\ContentCapture_v2\venv\Scripts\pip.exe install torch torchvision ^
    --index-url https://download.pytorch.org/whl/nightly/cu128 ^
    --quiet
echo        PyTorch installed OK

C:\ContentCapture_v2\venv\Scripts\pip.exe install "numpy<2.0" --force-reinstall --quiet
echo        NumPy pinned OK

:: ── Step 4: Copy app files ────────────────────────────────────────────────────
echo.
echo  [4/5] Installing app files...
copy /Y "%~dp0contentcapture_v2.py" "C:\ContentCapture_v2\contentcapture_v2.py" >nul
copy /Y "%~dp0ContentCapture.ico"   "C:\ContentCapture_v2\ContentCapture.ico"   >nul 2>&1
echo        App files copied OK

:: Auto-detect audio devices and save config
echo        Detecting audio devices...
C:\ContentCapture_v2\venv\Scripts\python.exe "%~dp0detect_audio.py"
echo        Audio configured OK

:: ── Step 5: Desktop shortcut ─────────────────────────────────────────────────
echo.
echo  [5/5] Creating desktop shortcut...
for /f "delims=" %%i in ('powershell -Command "[Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)"') do set "DESKTOP=%%i"
powershell -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%DESKTOP%\ContentCapture.lnk'); $s.TargetPath='C:\ContentCapture_v2\ContentCapture.bat'; $s.WorkingDirectory='C:\ContentCapture_v2'; $s.IconLocation='C:\ContentCapture_v2\ContentCapture.ico'; $s.Description='ContentCapture v2 — Capture Card Viewer'; $s.Save()"
echo        Shortcut created at: %DESKTOP%\ContentCapture.lnk

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║              SETUP COMPLETE!                        ║
echo  ║                                                      ║
echo  ║  Double-click ContentCapture on your desktop.       ║
echo  ║  Plug in your capture card before launching.        ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause
