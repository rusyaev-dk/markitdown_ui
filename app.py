"""Markitdown UI — drag & drop wrapper around microsoft/markitdown.

Lets the user drop/select a single file or a folder (processed recursively),
converts every supported document to Markdown, and shows live progress.
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

from markitdown import MarkItDown

# Extensions MarkItDown knows how to handle out of the box.
SUPPORTED_EXTS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv",
    ".html", ".htm", ".txt", ".md", ".json", ".xml", ".zip",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp",
    ".mp3", ".wav", ".m4a",
    ".epub", ".msg", ".rtf",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif"}

# Minimum extracted-text length below which a PDF is treated as "scanned"
# and re-processed with OCR when OCR mode is on.
PDF_OCR_FALLBACK_THRESHOLD = 40

_ocr_engine = None


def get_ocr_engine():
    """Lazily create the RapidOCR engine (loads ONNX models from disk, no network)."""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def ocr_array(img_array) -> str:
    engine = get_ocr_engine()
    result, _ = engine(img_array)
    if not result:
        return ""
    return "\n".join(line[1] for line in result)


def ocr_image_file(path: Path) -> str:
    from PIL import Image
    import numpy as np
    img = Image.open(path).convert("RGB")
    return ocr_array(np.array(img))


def ocr_pdf_file(path: Path, dpi: int = 200) -> str:
    import pypdfium2 as pdfium
    import numpy as np
    pdf = pdfium.PdfDocument(str(path))
    pages_text = []
    scale = dpi / 72
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil().convert("RGB")
        text = ocr_array(np.array(pil_image))
        if text.strip():
            pages_text.append(f"## Страница {i + 1}\n\n{text}")
    return "\n\n".join(pages_text)


def convert_document(md: MarkItDown, f: Path, ocr_enabled: bool) -> str:
    suffix = f.suffix.lower()
    if ocr_enabled and suffix in IMAGE_EXTS:
        text = ocr_image_file(f)
        return text if text.strip() else "*(OCR не распознал текст на изображении)*"

    if suffix == ".pdf":
        conv = md.convert(str(f))
        text = conv.text_content
        if ocr_enabled and len(text.strip()) < PDF_OCR_FALLBACK_THRESHOLD:
            ocr_text = ocr_pdf_file(f)
            if ocr_text.strip():
                return ocr_text
        return text

    conv = md.convert(str(f))
    return conv.text_content


@dataclass
class JobResult:
    src: Path
    ok: bool
    out_path: Path | None = None
    error: str = ""


@dataclass
class JobState:
    total: int = 0
    done: int = 0
    ok: int = 0
    failed: int = 0
    cancelled: bool = False
    results: list[JobResult] = field(default_factory=list)


def find_documents(paths: list[Path], recursive_dirs: bool, ext_filter: set[str] | None) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            it = p.rglob("*") if recursive_dirs else p.glob("*")
            for f in it:
                if f.is_file() and (ext_filter is None or f.suffix.lower() in ext_filter):
                    files.append(f)
        elif p.is_file():
            if ext_filter is None or p.suffix.lower() in ext_filter:
                files.append(p)
    return sorted(set(files))


class MarkItDownApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Markitdown UI")
        self.root.geometry("760x560")
        self.root.minsize(620, 460)

        self.selected_paths: list[Path] = []
        self.event_queue: "queue.Queue[tuple]" = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.cancel_flag = threading.Event()

        self.output_mode = tk.StringVar(value="same")  # same | custom
        self.output_dir = tk.StringVar(value="")
        self.recursive_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=True)
        self.only_known_ext = tk.BooleanVar(value=True)
        self.keep_structure = tk.BooleanVar(value=True)
        self.ocr_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._set_window_icon()
        self.root.after(100, self._poll_queue)

    def _set_window_icon(self):
        icon_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "icon.ico"
        try:
            self.root.iconbitmap(default=str(icon_path))
        except Exception:
            pass

    # ---------------------------------------------------------------- UI --
    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        drop_frame = tk.LabelFrame(self.root, text="1. Выберите документ(ы) или папку")
        drop_frame.pack(fill="x", **pad)

        self.drop_label = tk.Label(
            drop_frame,
            text=("Перетащите сюда файл(ы) или папку\n(или используйте кнопки ниже)"
                  if HAS_DND else
                  "Drag & drop недоступен (нет tkinterdnd2) — используйте кнопки ниже"),
            height=4, relief="ridge", bg="#f5f5f5", fg="#333",
        )
        self.drop_label.pack(fill="x", padx=8, pady=6)

        if HAS_DND:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)

        btn_row = tk.Frame(drop_frame)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(btn_row, text="Выбрать файлы...", command=self._pick_files).pack(side="left", padx=4)
        tk.Button(btn_row, text="Выбрать папку...", command=self._pick_folder).pack(side="left", padx=4)
        tk.Button(btn_row, text="Удалить выбранное", command=self._remove_selected).pack(side="left", padx=4)
        tk.Button(btn_row, text="Очистить список", command=self._clear_selection).pack(side="left", padx=4)

        list_row = tk.Frame(drop_frame)
        list_row.pack(fill="both", expand=False, padx=8, pady=(0, 4))
        self.selection_list = tk.Listbox(list_row, height=6, selectmode="extended", exportselection=False)
        self.selection_list.pack(side="left", fill="both", expand=True)
        sel_scroll = tk.Scrollbar(list_row, command=self.selection_list.yview)
        sel_scroll.pack(side="right", fill="y")
        self.selection_list.configure(yscrollcommand=sel_scroll.set)
        self.selection_list.bind("<Delete>", lambda e: self._remove_selected())
        self.selection_list.bind("<BackSpace>", lambda e: self._remove_selected())

        tk.Label(
            drop_frame,
            text="Выделяйте несколько строк с Ctrl / Shift и удаляйте кнопкой выше или клавишей Delete.",
            fg="#666", font=("", 8),
        ).pack(anchor="w", padx=8, pady=(0, 6))

        # --- settings ---
        opts_frame = tk.LabelFrame(self.root, text="2. Настройки")
        opts_frame.pack(fill="x", **pad)

        out_row = tk.Frame(opts_frame)
        out_row.pack(fill="x", padx=8, pady=4)
        tk.Radiobutton(out_row, text="Сохранять .md рядом с исходным файлом", variable=self.output_mode,
                       value="same").pack(anchor="w")
        custom_row = tk.Frame(opts_frame)
        custom_row.pack(fill="x", padx=8)
        tk.Radiobutton(custom_row, text="Сохранять в отдельную папку:", variable=self.output_mode,
                       value="custom").pack(side="left")
        self.output_entry = tk.Entry(custom_row, textvariable=self.output_dir, width=40)
        self.output_entry.pack(side="left", padx=6, fill="x", expand=True)
        tk.Button(custom_row, text="Обзор...", command=self._pick_output_dir).pack(side="left")

        chk_row = tk.Frame(opts_frame)
        chk_row.pack(fill="x", padx=8, pady=6)
        tk.Checkbutton(chk_row, text="Рекурсивно обходить вложенные папки", variable=self.recursive_var).grid(row=0, column=0, sticky="w")
        tk.Checkbutton(chk_row, text="Перезаписывать существующие .md", variable=self.overwrite_var).grid(row=1, column=0, sticky="w")
        tk.Checkbutton(chk_row, text="Обрабатывать только известные форматы", variable=self.only_known_ext).grid(row=0, column=1, sticky="w", padx=20)
        tk.Checkbutton(chk_row, text="Сохранять структуру папок (в custom-режиме)", variable=self.keep_structure).grid(row=1, column=1, sticky="w", padx=20)
        tk.Checkbutton(
            chk_row,
            text="Использовать OCR (для сканов PDF и изображений — медленнее)",
            variable=self.ocr_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # --- run controls ---
        run_frame = tk.Frame(self.root)
        run_frame.pack(fill="x", **pad)
        self.start_btn = tk.Button(run_frame, text="Начать конвертацию", bg="#2e7d32", fg="white",
                                    command=self._start_conversion)
        self.start_btn.pack(side="left", padx=4)
        self.cancel_btn = tk.Button(run_frame, text="Отмена", command=self._cancel_conversion, state="disabled")
        self.cancel_btn.pack(side="left", padx=4)

        # --- progress ---
        prog_frame = tk.LabelFrame(self.root, text="3. Прогресс")
        prog_frame.pack(fill="both", expand=True, **pad)

        self.progress_bar = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=8, pady=8)

        self.progress_label = tk.Label(prog_frame, text="Готов к работе. Обработано: 0 / 0")
        self.progress_label.pack(anchor="w", padx=8)

        self.log_text = tk.Text(prog_frame, height=14, state="disabled", wrap="none")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        log_scroll = tk.Scrollbar(self.log_text, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")

        # --- footer / authorship ---
        footer = tk.Frame(self.root)
        footer.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(footer, text="Markitdown UI  ·  автор:", fg="#777", font=("", 8)).pack(side="left")
        author_link = tk.Label(
            footer, text="github.com/rusyaev-dk", fg="#2563eb", cursor="hand2", font=("", 8, "underline"),
        )
        author_link.pack(side="left", padx=(4, 0))
        author_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/rusyaev-dk"))

    # ------------------------------------------------------------ actions --
    def _on_drop(self, event):
        raw = self.root.tk.splitlist(event.data)
        paths = [Path(p) for p in raw]
        self._add_paths(paths)

    def _pick_files(self):
        files = filedialog.askopenfilenames(title="Выберите файлы")
        if files:
            self._add_paths([Path(f) for f in files])

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку")
        if folder:
            self._add_paths([Path(folder)])

    def _pick_output_dir(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения .md")
        if folder:
            self.output_dir.set(folder)
            self.output_mode.set("custom")

    def _add_paths(self, paths: list[Path]):
        for p in paths:
            if p not in self.selected_paths:
                self.selected_paths.append(p)
                self.selection_list.insert("end", str(p))

    def _clear_selection(self):
        self.selected_paths.clear()
        self.selection_list.delete(0, "end")

    def _remove_selected(self):
        indices = self.selection_list.curselection()
        if not indices:
            return
        for i in reversed(indices):
            self.selection_list.delete(i)
            del self.selected_paths[i]

    def _log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ------------------------------------------------------------- worker --
    def _start_conversion(self):
        if not self.selected_paths:
            messagebox.showwarning("Нет файлов", "Сначала выберите файл(ы) или папку.")
            return
        if self.output_mode.get() == "custom" and not self.output_dir.get():
            messagebox.showwarning("Нет папки назначения", "Укажите папку для сохранения .md файлов.")
            return

        ext_filter = SUPPORTED_EXTS if self.only_known_ext.get() else None
        files = find_documents(self.selected_paths, self.recursive_var.get(), ext_filter)
        if not files:
            messagebox.showinfo("Нет документов", "Не найдено ни одного подходящего документа.")
            return

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        self.progress_bar["maximum"] = len(files)
        self.progress_bar["value"] = 0
        self.progress_label.config(text=f"Обработано: 0 / {len(files)}")

        self.cancel_flag.clear()
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")

        out_mode = self.output_mode.get()
        out_dir = Path(self.output_dir.get()) if out_mode == "custom" else None
        overwrite = self.overwrite_var.get()
        keep_structure = self.keep_structure.get()
        ocr_enabled = self.ocr_var.get()

        common_root = self._compute_common_root(files)

        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(files, out_mode, out_dir, overwrite, keep_structure, common_root, ocr_enabled),
            daemon=True,
        )
        self.worker_thread.start()

    def _compute_common_root(self, files: list[Path]) -> Path:
        try:
            return Path(os.path.commonpath([str(f.parent) for f in files]))
        except ValueError:
            return Path(files[0].anchor)

    def _cancel_conversion(self):
        self.cancel_flag.set()
        self.cancel_btn.config(state="disabled")

    def _reset_progress(self):
        if self.worker_thread is not None and self.worker_thread.is_alive():
            return
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = 100
        self.progress_label.config(text="Готов к работе. Обработано: 0 / 0")

    def _worker(self, files, out_mode, out_dir, overwrite, keep_structure, common_root, ocr_enabled):
        md = MarkItDown()
        state = JobState(total=len(files))

        if ocr_enabled:
            self.event_queue.put(("log", "Загрузка OCR-модели (при первом использовании — до пары секунд)..."))

        for f in files:
            if self.cancel_flag.is_set():
                state.cancelled = True
                break
            try:
                if out_mode == "same":
                    target = f.with_suffix(".md")
                else:
                    if keep_structure:
                        try:
                            rel = f.relative_to(common_root)
                        except ValueError:
                            rel = Path(f.name)
                        target = out_dir / rel.with_suffix(".md")
                    else:
                        target = out_dir / (f.stem + ".md")
                target.parent.mkdir(parents=True, exist_ok=True)

                if target.exists() and not overwrite:
                    result = JobResult(f, ok=False, error="пропущено (файл уже существует)")
                else:
                    text = convert_document(md, f, ocr_enabled)
                    target.write_text(text, encoding="utf-8")
                    result = JobResult(f, ok=True, out_path=target)
            except Exception as exc:  # noqa: BLE001
                result = JobResult(f, ok=False, error=f"{exc.__class__.__name__}: {exc}")
                self.event_queue.put(("trace", traceback.format_exc()))

            state.done += 1
            if result.ok:
                state.ok += 1
            else:
                state.failed += 1
            state.results.append(result)
            self.event_queue.put(("progress", state.done, state.total, result))

        self.event_queue.put(("finished", state))

    # -------------------------------------------------------------- queue --
    def _poll_queue(self):
        try:
            while True:
                item = self.event_queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, done, total, result = item
                    self.progress_bar["value"] = done
                    self.progress_label.config(text=f"Обработано: {done} / {total}")
                    if result.ok:
                        self._log(f"[OK] {result.src} -> {result.out_path}")
                    else:
                        self._log(f"[ОШИБКА] {result.src}: {result.error}")
                elif kind == "finished":
                    state: JobState = item[1]
                    self.start_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    status = "Отменено" if state.cancelled else "Готово"
                    self._log(f"--- {status}. Успешно: {state.ok}, Ошибок: {state.failed}, Всего: {state.total} ---")
                    self.progress_label.config(
                        text=f"{status}: {state.done} / {state.total} (успешно {state.ok}, ошибок {state.failed})"
                    )
                    self.root.after(2500, self._reset_progress)
                elif kind == "log":
                    self._log(item[1])
                elif kind == "trace":
                    pass  # detailed traceback already summarized in log
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    MarkItDownApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
