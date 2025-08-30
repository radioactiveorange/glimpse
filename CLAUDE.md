# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Glimpse** is a cross-platform desktop application for viewing random images from collections, built with Python and PySide6 (Qt). The application features a sophisticated startup system for collection management, professional image viewing capabilities, and an artist-focused workflow. It uses a modular architecture with clean separation between UI components, core functionality, and data management.

## Development Commands

### Running the Application
- **With uv (preferred):** `uv run main.py`
- **With Python:** `python main.py`

### Dependencies
- Install dependencies: `uv pip install pyside6` or `uv pip install -r pyproject.toml`
- Python 3.13+ is required (specified in pyproject.toml)

### Building Executable
- Install PyInstaller: `uv pip install pyinstaller`
- Build using existing spec file: `pyinstaller glimpse.spec`
- Manual build with custom icon: `pyinstaller --noconfirm --onefile --windowed --icon=app_icon.ico --name=glimpse main.py`
- Build without icon (fallback): `pyinstaller --noconfirm --onefile --windowed main.py`
- Output binary will be in the `dist/` folder
- **Note**: Uses `app_icon.ico` for Windows builds, `app_icon.png` for other platforms

## Architecture

### Modular Structure
The application is organized into a clean modular structure:

- **`main.py`**: Application entry point with startup dialog integration
- **`src/ui/`**: User interface components
  - `main_window.py`: Main application window (GlimpseViewer class)
  - `startup_dialog.py`: Professional startup screen for collection management
  - `loading_dialog.py`: Async loading dialog with progress indication for large collections
  - `timer_dialog.py`: Timer configuration dialog for collections/folders
  - `widgets.py`: Custom widgets (ClickableLabel, MinimalProgressBar, ButtonOverlay)
  - `styles.py`: Dark theme stylesheet constants
- **`src/core/`**: Core functionality
  - `image_utils.py`: Image processing utilities and professional icon creation
  - `collections.py`: Collection management system with JSON storage
- **`app_icon.png`**: Custom application icon for built executables

### Key Features Implementation
- **Startup System**: Professional dialog with collection management and timer configuration
- **Collection Management**: JSON-based storage with CollectionManager class
- **Image Display**: Advanced QLabel with pixmap scaling, transformation, and panning support
- **History System**: List-based navigation with thumbnail panel (QListWidget)
- **Timer System**: QTimer-based auto-advance with media-style controls (play/pause/stop)
- **Professional UI**: Button overlays with consistent geometric icons
- **Loading System**: Asynchronous image loading with progress dialog for large collections (72K+ images)
- **Settings Persistence**: QSettings with cross-platform data directory support
- **Signal Architecture**: Clean signal/slot communication between startup and main window
  - Object-typed signals for complex data (tuples, custom objects)
  - Collection/folder signals emit tuples: `(data, timer_enabled, timer_interval)`
- **Window Management**: All dialogs and windows automatically center on screen with multi-monitor support

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

## Development Guidelines

### Code Patterns
- **Qt Signal Architecture**: Use object-typed signals for complex data (tuples, custom objects)
- **Error Handling**: Implement graceful fallbacks for cancelled dialogs and invalid data
- **Icon System**: All icons created via `create_professional_icon()` with consistent sizing (16x16)
- **Settings Management**: Use QSettings with proper cross-platform paths
- **Image Loading**: Always use QPixmap with error handling for unsupported formats
- **Memory Management**: Cache processed pixmaps (`_cached_pixmap`) for smooth UI operations
- **Async Loading**: Use LoadingDialog with QThread (ImageLoadingWorker) for large collections
- **Threading**: Worker threads should emit progress signals and handle cancellation gracefully
- **Dialog Centering**: All dialogs implement `center_on_screen()` and `showEvent()` override for consistent positioning

### Current Status (Phase 4 Complete)
All major features have been implemented:
- ✅ **Collections System**: Multi-folder collections with full CRUD operations
- ✅ **Startup Workflow**: Professional ShuffleBird-inspired interface
- ✅ **Timer Configuration**: Flexible timer settings for any viewing session
- ✅ **Professional UI**: Media-style controls with consistent icon design
- ✅ **Smart Panning**: Intelligent constraints based on image and zoom state
- ✅ **Performance Optimization**: Async loading prevents UI freezing during large collection creation
- ✅ **Window Management**: All windows and dialogs properly centered with multi-monitor support

### Maintenance Notes
- **Timer Consistency**: Play/pause/stop buttons synchronized with context menu
- **Panning Logic**: Intelligent constraints - allows repositioning when image is off-center, regardless of zoom
- **Collections Storage**: JSON files in platform-appropriate user data directories via QStandardPaths
- **Startup Flow**: Application uses startup dialog pattern - main window only shows after selection
- **Widget Hierarchy**: GlimpseViewer (main) ← StartupDialog → Collection/Folder selection
- **Loading Performance**: LoadingDialog prevents UI freezing for large collections (72K+ images tested)
- **Collection Creation**: Async image counting during collection creation prevents freezing
- **Thread Safety**: Worker threads properly stopped in dialog closeEvent to prevent crashes
- **Dialog Positioning**: All dialogs use `availableGeometry()` and `frameGeometry()` for accurate centering

When making changes, preserve the existing dark theme aesthetic and ensure cross-platform compatibility (Windows, macOS, Linux).