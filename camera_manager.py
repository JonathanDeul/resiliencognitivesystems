"""
Camera capture and QR code detection manager.
Handles webcam input, runs detection in a background thread,
and emits signals when detection state changes.
"""

import cv2
import numpy as np
import platform
import queue
import threading
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QMutexLocker
from typing import Optional
from dataclasses import dataclass

from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol

from smoothing import BoundingBox, DetectedQR, BoundingBoxSmoother
from roboflow_client import RoboflowClient, RoboflowDetection
from local_yolo_client import LocalYoloClient
from config import (
    ROBOFLOW_FRAME_INTERVAL,
    ROBOFLOW_PERSISTENCE_FRAMES,
    USE_LOCAL_YOLO,
)

# QR detection settings
QR_DETECTION_SCALE = 0.5  # Scale down for faster detection


# Target QR code payload to detect
TARGET_PAYLOAD = "ROBOT_R1"


def check_camera_permission() -> str:
    """
    Check camera permission status on macOS.
    Returns: 'authorized', 'denied', 'not_determined', or 'unknown'
    """
    if platform.system() != 'Darwin':
        return 'authorized'  # Non-macOS systems don't need this

    try:
        # Use PyObjC to check AVFoundation authorization status
        import objc
        AVFoundation = objc.loadBundle(
            'AVFoundation',
            bundle_path='/System/Library/Frameworks/AVFoundation.framework',
            module_globals=globals()
        )

        # AVAuthorizationStatus enum values
        # 0 = notDetermined, 1 = restricted, 2 = denied, 3 = authorized
        status = AVCaptureDevice.authorizationStatusForMediaType_('vide')  # 'vide' = video

        if status == 3:
            return 'authorized'
        elif status == 2:
            return 'denied'
        elif status == 0:
            return 'not_determined'
        else:
            return 'denied'
    except Exception as e:
        print(f"Could not check camera permission: {e}")
        return 'unknown'


def request_camera_permission(callback=None):
    """
    Request camera permission on macOS.
    Must be called from the main thread.

    Args:
        callback: Optional function to call with result (True/False)
    """
    if platform.system() != 'Darwin':
        if callback:
            callback(True)
        return

    try:
        import objc
        AVFoundation = objc.loadBundle(
            'AVFoundation',
            bundle_path='/System/Library/Frameworks/AVFoundation.framework',
            module_globals=globals()
        )

        def completion_handler(granted):
            if callback:
                callback(granted)

        # Request access - this will show the system permission dialog
        AVCaptureDevice.requestAccessForMediaType_completionHandler_('vide', completion_handler)
    except Exception as e:
        print(f"Could not request camera permission via AVFoundation: {e}")
        # Fallback: try to open camera directly
        cap = cv2.VideoCapture(0)
        granted = cap.isOpened()
        if granted:
            cap.release()
        if callback:
            callback(granted)


@dataclass
class ClassificationBBox:
    """Bounding box from Roboflow classification."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class FrameData:
    """Container for a processed frame and its detection result."""
    frame: np.ndarray
    detection: Optional[DetectedQR]
    robot_detected: bool  # QR code detected
    qr_enabled: bool  # Whether QR detection is enabled
    classification_detected: bool  # Roboflow classification detected
    classification_bbox: Optional[ClassificationBBox]  # Bounding box from Roboflow
    can_continue_moving: bool  # Safety gate: both QR and classification required
    roboflow_enabled: bool  # Whether Roboflow is currently enabled


class CameraWorker(QThread):
    """
    Background worker thread for camera capture and QR detection.
    Emits processed frames with detection results to the main thread.
    """

    # Signals
    frame_ready = pyqtSignal(object)  # Emits FrameData
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = False
        self._mutex = QMutex()

        # Smoother for bounding box stabilization
        self._smoother = BoundingBoxSmoother(persistence_frames=5, smoothing_alpha=0.6)

        # Vision model client and state
        if USE_LOCAL_YOLO:
            self._roboflow_client = LocalYoloClient()
        else:
            self._roboflow_client = RoboflowClient()
        self._roboflow_enabled = False
        self._qr_enabled = True
        self._roboflow_frame_counter = 0
        self._classification_detected = False
        self._classification_bbox: Optional[ClassificationBBox] = None
        self._frames_without_classification = 0

        # Async Roboflow processing
        self._roboflow_queue: queue.Queue = queue.Queue(maxsize=1)
        self._roboflow_result_lock = threading.Lock()
        self._roboflow_thread: Optional[threading.Thread] = None
        self._roboflow_thread_running = False

    @property
    def smoothing_alpha(self) -> float:
        return self._smoother.alpha

    @smoothing_alpha.setter
    def smoothing_alpha(self, value: float):
        self._smoother.alpha = value

    @property
    def roboflow_enabled(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._roboflow_enabled

    @roboflow_enabled.setter
    def roboflow_enabled(self, value: bool):
        with QMutexLocker(self._mutex):
            self._roboflow_enabled = value
            if not value:
                # Reset classification state when disabled
                self._classification_detected = False
                self._classification_bbox = None
                self._frames_without_classification = 0

    @property
    def qr_enabled(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._qr_enabled

    @qr_enabled.setter
    def qr_enabled(self, value: bool):
        with QMutexLocker(self._mutex):
            self._qr_enabled = value
            if not value:
                self._smoother.reset()

    def run(self):
        """Main thread loop - captures frames and processes QR detection."""
        # Try to open camera with retries
        cap = None
        max_retries = 5
        retry_delay = 1.0  # seconds

        for attempt in range(max_retries):
            # On macOS, AVFoundation is the most reliable backend for local/continuity cameras.
            if platform.system() == "Darwin":
                cap = cv2.VideoCapture(self.camera_index, cv2.CAP_AVFOUNDATION)
            else:
                cap = cv2.VideoCapture(self.camera_index)
            if cap.isOpened():
                # Try to read a test frame
                ret, _ = cap.read()
                if ret:
                    break

            # Release and retry
            if cap:
                cap.release()
            cap = None

            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)

        if cap is None or not cap.isOpened():
            self.error_occurred.emit(
                f"Failed to open camera {self.camera_index}.\n\n"
                "Please check:\n"
                "1. Camera permissions in System Preferences > Privacy & Security > Camera\n"
                "2. No other application is using the camera\n"
                "3. Your camera is properly connected"
            )
            return

        # Set camera properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)

        self._running = True
        frames_failed = 0

        while self._running:
            ret, frame = cap.read()
            if not ret:
                frames_failed += 1
                if frames_failed > 30:  # ~1 second of failures
                    self.error_occurred.emit("Camera feed lost. Please check camera connection.")
                    break
                continue

            frames_failed = 0  # Reset on successful read

            # Flip horizontally for mirror effect (more intuitive for webcam)
            frame = cv2.flip(frame, 1)

            # Detect QR codes
            with QMutexLocker(self._mutex):
                qr_enabled = self._qr_enabled
            detection = self._detect_qr(frame) if qr_enabled else None

            # Apply smoothing
            with QMutexLocker(self._mutex):
                smoothed = self._smoother.update(detection)
                roboflow_enabled = self._roboflow_enabled

            robot_detected = smoothed is not None

            # Process Roboflow classification if enabled (non-blocking)
            classification_detected = False
            classification_bbox = None

            if roboflow_enabled:
                # Start Roboflow thread if not running
                if self._roboflow_thread is None or not self._roboflow_thread.is_alive():
                    self._roboflow_thread_running = True
                    self._roboflow_thread = threading.Thread(
                        target=self._roboflow_worker, daemon=True
                    )
                    self._roboflow_thread.start()

                self._roboflow_frame_counter += 1

                # Queue frame for Roboflow (non-blocking, drops if busy)
                if self._roboflow_frame_counter >= ROBOFLOW_FRAME_INTERVAL:
                    self._roboflow_frame_counter = 0
                    try:
                        # Try to queue frame, skip if worker is busy
                        self._roboflow_queue.put_nowait(frame.copy())
                    except queue.Full:
                        pass  # Worker still processing, skip this frame

                # Get latest result (non-blocking)
                with self._roboflow_result_lock:
                    classification_detected = self._classification_detected
                    classification_bbox = self._classification_bbox

            # Compute safety gate
            if roboflow_enabled:
                can_continue_moving = robot_detected and classification_detected
            else:
                can_continue_moving = robot_detected

            # Emit result
            frame_data = FrameData(
                frame=frame,
                detection=smoothed,
                robot_detected=robot_detected,
                qr_enabled=qr_enabled,
                classification_detected=classification_detected,
                classification_bbox=classification_bbox,
                can_continue_moving=can_continue_moving,
                roboflow_enabled=roboflow_enabled,
            )
            self.frame_ready.emit(frame_data)

        cap.release()

        # Stop Roboflow worker thread
        self._roboflow_thread_running = False
        if self._roboflow_thread and self._roboflow_thread.is_alive():
            try:
                self._roboflow_queue.put_nowait(None)  # Signal to exit
            except queue.Full:
                pass

    def _roboflow_worker(self):
        """Background thread for Roboflow API calls."""
        while self._roboflow_thread_running:
            try:
                # Wait for a frame with timeout
                frame = self._roboflow_queue.get(timeout=0.5)
                if frame is None:
                    break  # Exit signal

                # Call Roboflow API (this is the slow part)
                result = self._roboflow_client.detect(frame)

                # Update shared state
                with self._roboflow_result_lock:
                    if result.detected and result.detection:
                        self._classification_detected = True
                        self._frames_without_classification = 0
                        det = result.detection
                        bbox = det.bbox
                        self._classification_bbox = ClassificationBBox(
                            x=bbox[0],
                            y=bbox[1],
                            width=bbox[2],
                            height=bbox[3],
                        )
                    else:
                        self._frames_without_classification += 1
                        if self._frames_without_classification >= ROBOFLOW_PERSISTENCE_FRAMES:
                            self._classification_detected = False
                            self._classification_bbox = None

            except queue.Empty:
                continue
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Roboflow worker error: {e}")

    def _detect_qr(self, frame: np.ndarray) -> Optional[DetectedQR]:
        """
        Detect QR codes in the frame and filter for target payload.
        Uses pyzbar for fast detection with downscaled frames.
        Returns DetectedQR if target found, None otherwise.
        """
        # Downscale for faster detection
        height, width = frame.shape[:2]
        small_width = int(width * QR_DETECTION_SCALE)
        small_height = int(height * QR_DETECTION_SCALE)
        small_frame = cv2.resize(frame, (small_width, small_height))

        # Convert to grayscale for pyzbar
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

        # Detect QR codes using pyzbar (much faster than OpenCV)
        decoded = pyzbar.decode(gray, symbols=[ZBarSymbol.QRCODE])

        for qr in decoded:
            data = qr.data.decode('utf-8')
            if data == TARGET_PAYLOAD:
                # Get bounding box and scale back to original resolution
                rect = qr.rect
                scale_inv = 1.0 / QR_DETECTION_SCALE

                box = BoundingBox(
                    x=rect.left * scale_inv,
                    y=rect.top * scale_inv,
                    width=rect.width * scale_inv,
                    height=rect.height * scale_inv
                )
                return DetectedQR(payload=data, bounding_box=box)

        return None

    def stop(self):
        """Signal the thread to stop."""
        self._running = False
        self.wait()


class CameraManager(QObject):
    """
    High-level camera manager that wraps the worker thread.
    Provides a clean interface for the UI to interact with.
    """

    # Signals forwarded from worker
    frame_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self._worker: Optional[CameraWorker] = None
        self._camera_index = camera_index
        self._roboflow_enabled = False
        self._qr_enabled = True

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    @property
    def smoothing_alpha(self) -> float:
        if self._worker:
            return self._worker.smoothing_alpha
        return 0.6

    @smoothing_alpha.setter
    def smoothing_alpha(self, value: float):
        if self._worker:
            self._worker.smoothing_alpha = value

    @property
    def roboflow_enabled(self) -> bool:
        if self._worker:
            return self._worker.roboflow_enabled
        return self._roboflow_enabled

    @roboflow_enabled.setter
    def roboflow_enabled(self, value: bool):
        self._roboflow_enabled = value
        if self._worker:
            self._worker.roboflow_enabled = value

    @property
    def qr_enabled(self) -> bool:
        if self._worker:
            return self._worker.qr_enabled
        return self._qr_enabled

    @qr_enabled.setter
    def qr_enabled(self, value: bool):
        self._qr_enabled = value
        if self._worker:
            self._worker.qr_enabled = value

    def start(self):
        """Start the camera capture and detection."""
        if self._worker is not None:
            return

        self._worker = CameraWorker(self._camera_index)
        self._worker.roboflow_enabled = self._roboflow_enabled
        self._worker.qr_enabled = self._qr_enabled
        self._worker.frame_ready.connect(self.frame_ready.emit)
        self._worker.error_occurred.connect(self.error_occurred.emit)
        self._worker.start()

    def stop(self):
        """Stop the camera capture."""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None
