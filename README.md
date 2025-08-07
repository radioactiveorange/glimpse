# Random Image Viewer

A simple, modern, **cross-platform** desktop app to view random images from any folder (including subfolders). Great for artists, inspiration, or just browsing your photo collection!

---

## Features

- 📁 **Open Any Folder:** Load images from a folder and its subfolders.
- 🎲 **Random Image:** Instantly show a random image, avoiding repeats until all are seen.
- ⏮️ ⏭️ **History Navigation:** Go back and forward through viewed images.
- 🕒 **Auto-Advance Timer:** Automatically switch to a new random image at set intervals, with a circular countdown overlay.
- 🔍 **Zoom:** Zoom in/out/reset with mouse wheel, keyboard, or context menu.
- 🖱️ **Context Menu:** Right-click the image for all main actions (open folder, next/prev, zoom, timer, settings, etc.).
- 🌑 **Dark Theme:** Clean, minimal dark UI.
- 🖥️ **Cross-platform:** Works on Windows, macOS, and Linux.

---

## Installation

1. **Clone this repo:**
   ```sh
   git clone https://github.com/YOUR_USERNAME/random-image-viewer.git
   cd random-image-viewer
   ```

2. **Install [uv](https://github.com/astral-sh/uv) (if you don't have it):**
   ```sh
   pip install uv
   ```

3. **Install dependencies:**
   ```sh
   uv pip install -r pyproject.toml
   # or just
   uv pip install pyside6
   ```

---

## How to Run

- **With uv:**
  ```sh
  uv run main.py
  ```
- **Or with Python:**
  ```sh
  python main.py
  ```

---

## Usage

1. **Open a Folder:**
   - Right-click the image area and select "Open Folder".
2. **Show Random Image:**
   - Right-click and choose "Next Random Image", or press the **Right Arrow** key.
3. **Navigate History:**
   - Use **Left/Right Arrow** keys, or the context menu.
   - Enable the history panel from the context menu to click through viewed images.
4. **Auto-Advance:**
   - Enable from the context menu ("Enable Timer").
   - Adjust interval in the context menu.
   - A circular timer appears as an overlay.
5. **Zoom:**
   - Use mouse wheel over the image, keyboard shortcuts, or context menu.
6. **Other Actions:**
   - Flip image, toggle grayscale, change background, and more—all from the context menu.

---

## Keyboard Shortcuts & Context Menu Actions

- **Left Arrow:** Previous image
- **Right Arrow:** Next image (random if at end)
- **Ctrl + +:** Zoom in
- **Ctrl + -:** Zoom out
- **Ctrl + 0:** Reset zoom
- **Context Menu (right-click):**
  - Open Folder
  - Previous/Next Random Image
  - Zoom In/Out/Reset
  - Enable Timer & set interval
  - Show History Panel
  - Grayscale, Flip, Background color, etc.

---

## Screenshots

![Main Window](screenshots/main_window.png)
*Main window with random image loaded*

![History Panel](screenshots/history_panel.png)
*History panel enabled and showing viewed images*

![Pie Timer and Toolbar](screenshots/timer_toolbar.png)
*Pie timer overlay and auto-advance controls*

---

## Compiling to a Standalone Binary

You can compile this app to a standalone executable for Windows, Linux, or Mac using [PyInstaller](https://pyinstaller.org/).

1. **Install PyInstaller:**
   ```sh
   uv pip install pyinstaller
   ```
2. **Build the Executable:**
   ```sh
   pyinstaller --noconfirm --onefile --windowed main.py
   ```
   - The binary will be in the `dist/` folder.
   - For cross-compiling, build on the target OS or use a cross-compilation toolchain.

---

## Requirements

- Python 3.8+
- [PySide6](https://pypi.org/project/PySide6/)

---

## License

MIT License.

---

**Enjoy browsing your images!**