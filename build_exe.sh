#!/usr/bin/env bash
# Builds dist/"Markitdown UI.exe" — a single-file, no-console Windows executable.
set -e
./venv/Scripts/python.exe -m PyInstaller \
  --noconfirm \
  --onefile \
  --windowed \
  --name "Markitdown UI" \
  --icon icon.ico \
  --add-data "icon.ico;." \
  --collect-all markitdown \
  --collect-all magika \
  --collect-all rapidocr_onnxruntime \
  --collect-all cv2 \
  --collect-data tkinterdnd2 \
  --hidden-import tkinterdnd2 \
  app.py
