# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cross-platform desktop application for viewing random images from folders, built with Python and PySide6 (Qt). The application uses a modular structure with a clean separation between UI components, core functionality, and the main entry point. It provides features like random image viewing, history navigation, auto-advance timer, zoom controls, and various image manipulation options.

## Development Commands

### Running the Application
- **With uv (preferred):** `uv run main.py`
- **With Python:** `python main.py`

### Dependencies
- Install dependencies: `uv pip install pyside6` or `uv pip install -r pyproject.toml`
- Python 3.13+ is required (specified in pyproject.toml)

### Building Executable
- Install PyInstaller: `uv pip install pyinstaller`
- Build standalone executable with custom icon: `pyinstaller --noconfirm --onefile --windowed --icon=app_icon.png main.py`
- Build without icon (fallback): `pyinstaller --noconfirm --onefile --windowed main.py`
- Output binary will be in the `dist/` folder
- **Note**: The custom app icon (`app_icon.png`) replaces the default Python icon

## Architecture

### Modular Structure
The application is organized into a clean modular structure:

- **`main.py`**: Application entry point and initialization
- **`src/ui/`**: User interface components
  - `main_window.py`: Main application window with image display and controls
  - `widgets.py`: Custom widgets (ClickableLabel, MinimalProgressBar, ButtonOverlay)
  - `styles.py`: Dark theme stylesheet constants
- **`src/core/`**: Core functionality
  - `image_utils.py`: Image processing utilities and helper functions
- **`app_icon.png`**: Custom application icon for built executables

### Key Features Implementation
- **Image Display**: QLabel with pixmap scaling and transformation support
- **History System**: List-based navigation with thumbnail panel (QListWidget)
- **Timer System**: QTimer-based auto-advance with minimal progress bar and button overlay controls
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

Based on TODO.md, remaining planned improvements include:
- Collections feature for managing multiple image sources
- Enhanced zoom and panning capabilities
- Further UI refinements

When making changes, preserve the existing dark theme aesthetic and ensure cross-platform compatibility (Windows, macOS, Linux).