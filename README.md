# Markitdown UI

<p align="center">
  <img src="assets/icon_preview.png" width="140" alt="Markitdown UI icon">
</p>

<p align="center">
  A simple drag-and-drop GUI wrapper around
  <a href="https://github.com/microsoft/markitdown">microsoft/markitdown</a> —
  convert documents (PDF, DOCX, PPTX, XLSX, images, and more) to Markdown,
  one file at a time, a whole folder, or nested folders recursively.
</p>

---

## Features

- **Drag & drop** files and folders straight into the window, or pick them via file dialogs.
- **Recursive folder processing** — nested subfolders are walked automatically.
- **Multi-select** in the file list (Ctrl / Shift) with quick removal (button or `Delete` key).
- **Progress indicator** — how many documents are done / remaining, a per-file log (success/error), and auto-reset of progress after completion or cancellation.
- **OCR mode** for scanned PDFs and images — runs fully offline via [RapidOCR](https://github.com/RapidAI/RapidOCR) (ONNX Runtime), no need to install Tesseract or use any external service.
- **Flexible output options**: save next to the source file or into a separate folder (preserving directory structure), overwrite existing `.md` files, filter by known formats only.
- Ships as a **standalone `.exe`** — end users don't need Python or any dependencies installed.

## Supported formats

PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX, CSV, HTML, TXT, MD, JSON, XML, ZIP, images (PNG/JPG/GIF/BMP), audio (MP3/WAV/M4A — transcription), EPUB, MSG, RTF — every format `markitdown` understands.

## Install & run from source

Requires **Python 3.12** (newer versions may be incompatible with some dependencies).

```bash
git clone https://github.com/rusyaev-dk/markitdown-ui.git
cd markitdown-ui
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Building a standalone `.exe`

```bash
pip install -r requirements-dev.txt
bash build_exe.sh
```

The resulting file will be at `dist/Markitdown UI.exe` — a single-file, console-free executable with the icon embedded. All dependencies (including the OCR models) are bundled inside, so the end user doesn't need to install anything.

> If `bash` isn't available, run the equivalent `pyinstaller` command from `build_exe.sh` directly in PowerShell.

## Usage

1. Drag & drop file(s) or a folder onto the area at the top of the window — or use the "Select files..." / "Select folder..." buttons.
2. Configure the options: where to save the `.md` files, whether to recurse into subfolders, whether to overwrite existing files, and whether to enable OCR.
3. Click **"Start conversion"** and watch the progress. Conversion can be interrupted with the "Cancel" button.
4. The resulting `.md` files will appear next to the source files or in the chosen output folder, depending on the selected mode.

## Icon

The icon is generated programmatically (`generate_icon.py`, Pillow) and embedded both in the application window and in the `.exe` itself.

## Tech stack

- [microsoft/markitdown](https://github.com/microsoft/markitdown) — the Markdown conversion engine.
- [RapidOCR (onnxruntime)](https://github.com/RapidAI/RapidOCR) — offline OCR.
- Tkinter + [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) — UI and drag & drop.
- [PyInstaller](https://pyinstaller.org/) — standalone `.exe` packaging.

## Author

[github.com/rusyaev-dk](https://github.com/rusyaev-dk)

## License

MIT (see [LICENSE](LICENSE)).
