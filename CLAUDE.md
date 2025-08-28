# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cross-platform desktop application for viewing random images from folders, built with Python and PySide6 (Qt). The application is a single-file implementation (`main.py`) that provides features like random image viewing, history navigation, auto-advance timer, zoom controls, and various image manipulation options.

## Development Commands

### Running the Application
- **With uv (preferred):** `uv run main.py`
- **With Python:** `python main.py`

### Dependencies
- Install dependencies: `uv pip install pyside6` or `uv pip install -r pyproject.toml`
- Python 3.13+ is required (specified in pyproject.toml)

### Building Executable
- Install PyInstaller: `uv pip install pyinstaller`
- Build standalone executable: `pyinstaller --noconfirm --onefile --windowed main.py`
- Output binary will be in the `dist/` folder

## Architecture

### Single File Structure
The entire application is contained in `main.py` with these key components:

- **MainWindow class**: Main application window with image display, toolbar, and status bar
- **CircularCountdown class**: Custom widget for the animated timer overlay
- **Utility functions**: 
  - `get_images_in_folder()`: Recursively finds image files in directories
  - `emoji_icon()`: Creates Qt icons from emoji characters

### Key Features Implementation
- **Image Display**: QLabel with pixmap scaling and transformation support
- **History System**: List-based navigation with thumbnail panel (QListWidget)
- **Timer System**: QTimer-based auto-advance with smooth circular countdown overlay
- **Settings Persistence**: QSettings for remembering user preferences
- **Context Menu**: Right-click menu for all major actions
- **Keyboard Shortcuts**: Arrow keys for navigation, Ctrl+/- for zoom

### State Management
- Image transformations (flip, grayscale) applied via QTransform
- Background modes (black, gray, adaptive) handled through stylesheet updates
- Zoom levels managed through QLabel scaling
- History navigation with bidirectional index tracking

## Code Patterns

### Qt Widget Styling
The application uses a comprehensive dark theme stylesheet (`DARK_STYLESHEET`) that should be maintained when adding new UI elements.

### Image Processing
- Supported formats defined in `IMAGE_EXTENSIONS` constant
- Image loading uses QPixmap with error handling
- Transformations applied through QTransform matrix operations

### Event Handling
- Custom `keyPressEvent()` for keyboard shortcuts
- Context menu actions connected via Qt signals/slots
- Timer events handled through QTimer callbacks

## Future Development Notes

Based on TODO.md, planned improvements include:
- Collections feature for managing multiple image sources
- UI refactoring with button overlays and simplified timer display
- Code modularization to break up the monolithic main.py
- Enhanced zoom and panning capabilities

When making changes, preserve the existing dark theme aesthetic and ensure cross-platform compatibility (Windows, macOS, Linux).