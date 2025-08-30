#!/usr/bin/env python3
"""
Simple import test for CI environments.
Tests core functionality without requiring a GUI display.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_version():
    """Test version module."""
    from version import get_version
    version = get_version()
    print(f"Version: {version}")
    assert version.count('.') >= 2, 'Version should be semantic (x.y.z)'
    print("Version test passed")
    return version

def test_core_imports():
    """Test core module imports."""
    from version import get_version
    from core.image_utils import IMAGE_EXTENSIONS
    from core.collections import Collection, CollectionManager
    
    print("Core modules imported successfully")
    print(f"Glimpse v{get_version()} - Core functionality verified")
    print(f"Supported image formats: {len(IMAGE_EXTENSIONS)}")

def test_gui_imports():
    """Test GUI imports (requires display)."""
    try:
        from ui.main_window import GlimpseViewer
        from version import get_version
        print(f"GUI imports successful")
        print(f"Glimpse v{get_version()} - Full GUI test passed")
    except ImportError as e:
        print(f"GUI import failed: {e}")
        raise

if __name__ == "__main__":
    print("Running Glimpse import tests...")
    
    # Always test these
    version = test_version()
    test_core_imports()
    
    # Test GUI only if requested
    if "--gui" in sys.argv or os.environ.get("TEST_GUI", "").lower() == "true":
        print("Testing GUI imports...")
        test_gui_imports()
    else:
        print("Skipping GUI tests (use --gui flag to enable)")
    
    print(f"All tests passed for Glimpse v{version}!")