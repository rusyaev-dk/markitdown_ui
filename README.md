# Markitdown UI

<p align="center">
  <img src="assets/icon_preview.png" width="140" alt="Markitdown UI icon">
</p>

<p align="center">
  Простая drag-and-drop GUI-оболочка для
  <a href="https://github.com/microsoft/markitdown">microsoft/markitdown</a> —
  конвертируйте документы (PDF, DOCX, PPTX, XLSX, изображения и др.) в Markdown
  одним файлом, целой папкой или рекурсивно вложенными папками.
</p>

---

## Возможности

- **Перетаскивание файлов и папок** (drag & drop) прямо в окно, либо выбор через диалоговые окна.
- **Рекурсивная обработка папок** — вложенные подпапки обходятся автоматически.
- **Множественный выбор** элементов списка (Ctrl / Shift) и быстрое удаление лишних (кнопка или `Delete`).
- **Индикатор прогресса** — сколько документов обработано / осталось, лог по каждому файлу (успех/ошибка), автосброс прогресса после завершения или отмены.
- **OCR-режим** для сканированных PDF и изображений — работает офлайн через [RapidOCR](https://github.com/RapidAI/RapidOCR) (ONNX Runtime), без установки Tesseract или сторонних сервисов.
- **Гибкие настройки сохранения**: рядом с исходником или в отдельную папку (с сохранением структуры каталогов), перезапись существующих `.md`, фильтр по известным форматам.
- Работает как **автономный `.exe`** — Python и зависимости пользователю не нужны.

## Поддерживаемые форматы

PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX, CSV, HTML, TXT, MD, JSON, XML, ZIP, изображения (PNG/JPG/GIF/BMP), аудио (MP3/WAV/M4A — транскрипция), EPUB, MSG, RTF — все форматы, которые понимает `markitdown`.

## Установка и запуск из исходников

Требуется **Python 3.12** (более новые версии могут быть несовместимы с частью зависимостей).

```bash
git clone https://github.com/rusyaev-dk/markitdown-ui.git
cd markitdown-ui
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Сборка standalone `.exe`

```bash
pip install -r requirements-dev.txt
bash build_exe.sh
```

Готовый файл появится в `dist/Markitdown UI.exe` — однофайловый, без консоли, со встроенной иконкой. Все зависимости (включая модели OCR) упаковываются внутрь, поэтому пользователю не нужно ничего устанавливать.

> Если `bash` недоступен, можно запустить ту же команду `pyinstaller` из содержимого `build_exe.sh` напрямую в PowerShell.

## Использование

1. Перетащите файл(ы) или папку в область в верхней части окна — либо воспользуйтесь кнопками «Выбрать файлы...» / «Выбрать папку...».
2. Настройте параметры: куда сохранять `.md`, обходить ли вложенные папки, перезаписывать ли существующие файлы, включить ли OCR.
3. Нажмите **«Начать конвертацию»** и следите за прогрессом. Конвертацию можно прервать кнопкой «Отмена».
4. Результаты (`.md` файлы) появятся рядом с исходниками или в указанной папке — в зависимости от выбранного режима.

## Иконка

Иконка сгенерирована программно (`generate_icon.py`, Pillow) и встроена как в окно приложения, так и в сам `.exe`.

## Технологии

- [microsoft/markitdown](https://github.com/microsoft/markitdown) — движок конвертации в Markdown.
- [RapidOCR (onnxruntime)](https://github.com/RapidAI/RapidOCR) — офлайн-OCR.
- Tkinter + [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) — интерфейс и drag & drop.
- [PyInstaller](https://pyinstaller.org/) — сборка автономного `.exe`.

## Автор

[github.com/rusyaev-dk](https://github.com/rusyaev-dk)

## Лицензия

MIT (см. [LICENSE](LICENSE)).
