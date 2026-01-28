#!/usr/bin/env python3
"""
Robot QR Detection - Desktop Application
Detects and tracks a specific QR code marker ("ROBOT_R1") using the laptop webcam.

Usage:
    python main.py
    python main.py --camera-index 1
    python main.py --list-cameras

Requirements:
    pip install -r requirements.txt
    
Note: On macOS, you may need to grant camera permissions in System Preferences.
"""

import sys
import os
import argparse
import logging
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix zbar library path on macOS (needed for pyzbar)
if sys.platform == 'darwin':
    import ctypes
    from ctypes.util import find_library

    # Homebrew paths for Apple Silicon and Intel Macs
    for zbar_lib in ['/opt/homebrew/lib/libzbar.dylib', '/usr/local/lib/libzbar.dylib']:
        if os.path.exists(zbar_lib):
            # Monkey-patch pyzbar's library loading
            import pyzbar.zbar_library as zbar_library

            def _load_patched():
                libzbar = ctypes.cdll.LoadLibrary(zbar_lib)
                return libzbar, []

            zbar_library.load = _load_patched
            break

# Fix Qt plugin path for environments with conflicting Qt installations (e.g., Anaconda)
try:
    import PyQt6
    pyqt6_path = os.path.dirname(PyQt6.__file__)
    qt_plugins_path = os.path.join(pyqt6_path, 'Qt6', 'plugins')
    qt_lib_path = os.path.join(pyqt6_path, 'Qt6', 'lib')
    if os.path.exists(qt_plugins_path):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins_path
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugins_path, 'platforms')
    if os.path.exists(qt_lib_path):
        # Prepend to DYLD_LIBRARY_PATH for framework dependencies
        existing = os.environ.get('DYLD_LIBRARY_PATH', '')
        os.environ['DYLD_LIBRARY_PATH'] = qt_lib_path + (':' + existing if existing else '')
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


def _probe_cameras(max_index: int = 10) -> List[Tuple[int, str]]:
    """
    Try opening camera indices [0..max_index] and return a list of working indices.
    This is a best-effort probe (OpenCV indexes are backend/OS-dependent).
    """
    import cv2
    import platform

    working: List[Tuple[int, str]] = []
    for idx in range(max_index + 1):
        # On macOS, AVFoundation tends to behave better (and avoids some noisy backends).
        if platform.system() == "Darwin":
            cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
        else:
            cap = cv2.VideoCapture(idx)
        try:
            if not cap.isOpened():
                continue
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            h, w = frame.shape[:2]
            working.append((idx, f"{w}x{h}"))
        finally:
            try:
                cap.release()
            except Exception:
                pass
    return working


def main():
    parser = argparse.ArgumentParser(description="Robot QR Detection - Desktop Application")
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="OpenCV camera index to use (default: 0). Use --list-cameras to probe indices.",
    )
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="Probe camera indices and print those that can be opened, then exit.",
    )
    parser.add_argument(
        "--max-camera-index",
        type=int,
        default=10,
        help="Max camera index to probe when using --list-cameras (default: 10).",
    )
    args = parser.parse_args()

    if args.list_cameras:
        cams = _probe_cameras(max_index=args.max_camera_index)
        if not cams:
            print("No working cameras found via OpenCV.")
            print("If you're on macOS, check: System Settings → Privacy & Security → Camera.")
        else:
            print("Working camera indices (OpenCV):")
            for idx, size in cams:
                print(f"- index {idx}: {size}")
            print()
            print("Tip: If you want to try a different camera (e.g., Continuity Camera), run:")
            print("  python main.py --camera-index <index>")
        return

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Robot QR Detection")
    app.setOrganizationName("RobotQR")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    # Override camera index if requested
    try:
        window._camera._camera_index = int(args.camera_index)  # keep change minimal
    except Exception:
        pass
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

