<p align="center">
  <img src="app_icon.png" alt="Glimpse" width="128" height="128">
</p>

# Glimpse 👁️

**Random image viewer for collections**

A cross-platform desktop application for viewing random images from folders or collections. Useful for reference studies, browsing large image libraries, and rediscovering artwork.

## ✨ Features

### 🎲 **Collections & Random Viewing**
- Organize multiple folders into collections
- Quick shuffle mode for single folders
- History navigation with thumbnail panel

### ⏰ **Timer System** 
- Auto-advance with custom intervals (30 seconds to hours)
- Play/pause/stop controls
- Manual browsing mode

### 🖼️ **Image Viewing**
- Zoom and pan support
- Image transformations (flip, grayscale)
- Configurable backgrounds (black, gray, adaptive)

### 🎨 **Interface**
- Dark theme
- Keyboard shortcuts and right-click menu
- Minimal UI design

### 💾 **Collection Management**
- Multi-folder collections
- Persistent storage between sessions
- Cross-platform support (Windows, macOS, Linux)

---

## 🚀 Quick Start

### Installation

**Prerequisites:**
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager) - Install with: `pip install uv`

**Option 1: Run from Source**
```bash
# Clone the repository
git clone https://github.com/radioactiveorange/glimpse.git
cd glimpse

# Create and activate virtual environment with uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Run the application
uv run main.py
```

**Alternative with uv (no manual venv activation needed):**
```bash
# Clone the repository
git clone https://github.com/radioactiveorange/glimpse.git
cd glimpse

# Install dependencies (uv handles venv automatically)
uv pip install -e .

# Run the application
uv run main.py
```

**Option 2: Build Executable**
```bash
# Install build dependencies
uv pip install -e ".[build]"

# Build standalone executable
pyinstaller --noconfirm --onefile --windowed --icon=app_icon.ico --name=glimpse main.py

# Find your executable in the dist/ folder
```

---

### First Launch

1. Create a collection by clicking "New Collection" and selecting folders
2. Configure timer settings (or disable for manual browsing)
3. Click "Open Collection" to start viewing

Alternatively, use "Quick Shuffle Folder" to browse any folder immediately.

---

## 🎯 Use Cases

- Reference image studies
- Portfolio reviews
- Browsing large image libraries
- Visual research and inspiration

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `←` `→` | Navigate previous/next image |
| `Ctrl` `+` | Zoom in |
| `Ctrl` `-` | Zoom out |
| `Ctrl` `0` | Reset zoom to 100% |
| `Right-click` | Open context menu |

## 🖱️ Mouse Controls

- **Left-click + Drag**: Pan image when zoomed
- **Mouse Wheel**: Zoom in/out
- **Right-click**: Context menu with all options

---

## 🛠️ Advanced Features

### Collection Management
- Edit collections (rename, manage folders)
- Delete collections
- Auto-sorted by recent usage

### Image Processing  
- Supported formats: JPG, JPEG, PNG, BMP, GIF
- Recursive search in subfolders
- Grayscale mode and flip controls

### Customization
- Background modes: Black, Gray, Adaptive Color
- Timer intervals: 30s, 1min, 2min, 5min, or custom
- Configurable history panel

## 🏗️ Technical Details

- Framework: PySide6 (Qt for Python)
- Modular architecture
- JSON-based collection storage
- Cross-platform settings and data directories
- Image caching for smooth performance

## 🎨 Screenshots

### Welcome Screen & Collections
![Welcome Screen](screenshots/welcome-screen.png)

### Main Viewer
![Main Viewer](screenshots/main-viewer.png)

### Media Controls
![Media Controls](screenshots/media-controls.png)

### Context Menu
![Context Menu](screenshots/context-menu.png)

---

## 🤝 Contributing

This project was built collaboratively with Claude Code. Contributions, bug reports, and feature requests are welcome!

---

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

**Glimpse** - *Random glimpses of your visual world* ✨

*Built for artists, by artists (and AI) 🎨🤖*