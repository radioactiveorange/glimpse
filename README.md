# Glimpse 👁️

**Get random glimpses of your image collections**

Glimpse is a cross-platform desktop application for artists, designers, and creatives who want to randomly view images from their collections. Perfect for reference studies, inspiration sessions, and rediscovering forgotten artwork.

## ✨ Features

### 🎲 **Smart Random Viewing**
- **Collections**: Organize multiple folders into themed collections (e.g., "Character References", "Environment Studies")
- **Quick Shuffle**: Instantly start viewing images from any folder
- **History Navigation**: Browse back and forth through previously viewed images with thumbnail panel

### ⏰ **Flexible Timer System** 
- **Auto-Advance**: Set custom intervals from 30 seconds to hours
- **Pause/Resume**: Full control with intuitive media-style buttons
- **Manual Mode**: Browse at your own pace without any timer

### 🖼️ **Professional Image Viewing**
- **Smart Zoom**: Smooth zooming with mouse wheel (Ctrl +/-)
- **Pan Support**: Drag images when zoomed in, with intelligent constraints
- **Image Transformations**: Flip horizontally/vertically, toggle grayscale
- **Adaptive Backgrounds**: Choose black, gray, or adaptive color backgrounds

### 🎨 **Artist-Focused Design**
- **Minimal UI**: Clean interface that doesn't distract from your images
- **Dark Theme**: Easy on the eyes for long viewing sessions
- **Keyboard Shortcuts**: Arrow keys for navigation, Ctrl+0 to reset zoom
- **Context Menu**: Right-click access to all features

### 💾 **Smart Collection Management**
- **Multi-folder Collections**: Include images from multiple directories
- **Persistent Storage**: Collections remembered between sessions
- **Usage Tracking**: Recently used collections shown first
- **Cross-platform**: Works on Windows, macOS, and Linux

---

## 🚀 Quick Start

### Installation

**Option 1: Run from Source**
```bash
# Clone the repository
git clone https://github.com/your-username/glimpse.git
cd glimpse

# Install dependencies with uv (recommended)
uv pip install pyside6

# Run the application
uv run main.py
```

**Option 2: Build Executable**
```bash
# Install PyInstaller
uv pip install pyinstaller

# Build standalone executable
pyinstaller --noconfirm --onefile --windowed --icon=app_icon.png main.py

# Find your executable in the dist/ folder
```

---

### First Launch

1. **Create a Collection**: Click "New Collection", give it a name, and select folders containing your images
2. **Configure Timer**: Choose your preferred auto-advance interval (or disable for manual browsing)
3. **Start Viewing**: Click "Open Collection" and enjoy your random image glimpses!

**Or use Quick Shuffle**: Select "Quick Shuffle Folder" for immediate access to any folder.

---

## 🎯 Perfect For

- **Digital Artists**: Reference image studies and inspiration
- **Photographers**: Portfolio reviews and rediscovering old work  
- **Designers**: Mood boards and creative inspiration sessions
- **Collectors**: Enjoying large image libraries without overwhelm
- **Students**: Art history studies and visual research

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
- **Edit Collections**: Rename collections and manage folder lists
- **Delete Collections**: Remove collections you no longer need
- **Smart Organization**: Collections auto-sorted by recent usage

### Image Processing  
- **Format Support**: JPG, JPEG, PNG, BMP, GIF
- **Recursive Search**: Automatically finds images in subfolders
- **Grayscale Mode**: Toggle black & white viewing
- **Flip Controls**: Horizontal and vertical image flipping

### Customization
- **Background Modes**: 
  - Black (default)
  - Gray (neutral)
  - Adaptive Color (matches image)
- **Timer Intervals**: 30s, 1min, 2min, 5min, or custom
- **UI Preferences**: Toggle history panel, adjust settings

## 🏗️ Technical Details

- **Framework**: PySide6 (Qt for Python)
- **Architecture**: Modular design with separate UI, core logic, and utilities
- **Data Storage**: JSON-based collections with cross-platform paths
- **Settings**: Platform-appropriate user data directories
- **Performance**: Optimized image caching and smooth animations

## 🎨 Screenshots

*Screenshots coming soon - the app is fully functional and ready to use!*

---

## 🤝 Contributing

This project was built collaboratively with Claude Code. Contributions, bug reports, and feature requests are welcome!

---

## 📝 License

This project is open source. License details to be added.

---

**Glimpse** - *Random glimpses of your visual world* ✨

*Built for artists, by artists (and AI) 🎨🤖*