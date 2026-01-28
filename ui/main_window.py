"""
Main application window.
Assembles all UI components and wires them to the camera manager.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QStackedWidget, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from camera_manager import CameraManager, FrameData, check_camera_permission, request_camera_permission
from .video_widget import VideoWidget
from .controls import (
    StatusBanner, SmoothingControl, SafetyStatusBanner,
    SecondaryStatusIndicator, RoboflowToggle, QRToggle, DistanceDisplay, TrackingButton,
    DistanceThresholdControl
)
from distance_sensor import DistanceSensor


class MainWindow(QMainWindow):
    """
    Main application window with camera feed, status banner, and controls.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Robot QR Detection")
        self.setMinimumSize(800, 600)
        self.resize(1024, 768)

        # Set dark background
        self.setStyleSheet("background-color: #1a1a1a;")

        # Camera manager
        self._camera = CameraManager()
        self._camera.roboflow_enabled = True  # Vision Model ON by default
        self._camera.frame_ready.connect(self._on_frame_ready)
        self._camera.error_occurred.connect(self._on_error)

        # Distance sensor
        self._distance_sensor = DistanceSensor()
        self._distance_sensor.distance_updated.connect(self._on_distance_updated)
        # We start the sensor immediately; could also be conditional
        self._distance_sensor.start()
        
        # Current distance for tracking
        self._current_distance = 0

        # Distance threshold - if target is farther than this, robot can move freely
        self._distance_threshold = 100  # cm

        # Setup UI
        self._setup_ui()

        # Check camera permission and start
        QTimer.singleShot(100, self._check_and_start_camera)

    def _check_and_start_camera(self):
        """Check camera permission and start capture."""
        import platform

        if platform.system() == 'Darwin':
            # On macOS, check permission first
            status = check_camera_permission()

            if status == 'authorized':
                self._camera.start()
            elif status == 'not_determined':
                # Request permission
                def on_permission_result(granted):
                    if granted:
                        # Use QTimer to ensure we're on the main thread
                        QTimer.singleShot(100, self._camera.start)
                    else:
                        self._on_error(
                            "Camera access denied.\n\n"
                            "Please enable camera access in:\n"
                            "System Settings → Privacy & Security → Camera"
                        )

                request_camera_permission(on_permission_result)
            else:
                self._on_error(
                    "Camera access denied.\n\n"
                    "Please enable camera access in:\n"
                    "System Settings → Privacy & Security → Camera → Terminal"
                )
        else:
            # Non-macOS, just start
            self._camera.start()

    def _setup_ui(self):
        """Initialize all UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Content area (video + overlays)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Video widget
        self._video_widget = VideoWidget()
        content_layout.addWidget(self._video_widget)

        # Overlay container (for status banner and controls)
        overlay = QWidget(content)
        # IMPORTANT: overlay sits above the video widget; it must be visually transparent
        # so the camera feed remains visible underneath.
        overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        overlay.setStyleSheet("background: transparent;")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(20, 20, 20, 20)

        # Top row: safety status banner centered
        top_row = QHBoxLayout()
        top_row.addStretch()
        self._safety_banner = SafetyStatusBanner()
        top_row.addWidget(self._safety_banner)
        top_row.addStretch()
        overlay_layout.addLayout(top_row)

        # Secondary status row: QR and Vision status indicators
        secondary_row = QHBoxLayout()
        secondary_row.addStretch()
        self._qr_status = SecondaryStatusIndicator("QR Code")
        secondary_row.addWidget(self._qr_status)
        secondary_row.addSpacing(10)
        self._vision_status = SecondaryStatusIndicator("Vision Model")
        self._vision_status.setVisible(True)  # Visible by default since Vision Model starts ON
        secondary_row.addWidget(self._vision_status)
        
        secondary_row.addSpacing(10)
        self._distance_display = DistanceDisplay("Target Dist")
        secondary_row.addWidget(self._distance_display)
        secondary_row.addStretch()
        overlay_layout.addLayout(secondary_row)

        overlay_layout.addStretch()

        # Bottom row: toggles on left, smoothing control on the right
        bottom_row = QHBoxLayout()

        # QR toggle
        self._qr_toggle = QRToggle()
        self._qr_toggle.toggled.connect(self._on_qr_toggled)
        bottom_row.addWidget(self._qr_toggle)

        bottom_row.addSpacing(10)

        # Roboflow toggle
        self._roboflow_toggle = RoboflowToggle()
        self._roboflow_toggle.toggled.connect(self._on_roboflow_toggled)
        bottom_row.addWidget(self._roboflow_toggle)
        
        bottom_row.addSpacing(10)
        
        # Tracking button
        self._tracking_button = TrackingButton(target_frames=2000)
        bottom_row.addWidget(self._tracking_button)

        bottom_row.addSpacing(10)

        # Distance threshold control
        self._threshold_control = DistanceThresholdControl(initial_value=100)
        self._threshold_control.threshold_changed.connect(self._on_threshold_changed)
        bottom_row.addWidget(self._threshold_control)

        bottom_row.addStretch()

        # Smoothing control on right
        self._smoothing_control = SmoothingControl(initial_value=0.6)
        self._smoothing_control.smoothing_changed.connect(self._on_smoothing_changed)
        bottom_row.addWidget(self._smoothing_control)

        overlay_layout.addLayout(bottom_row)

        # Stack video and overlay
        # Use a stacked approach where overlay is positioned absolutely
        main_layout.addWidget(content)

        # Position overlay over content
        overlay.setParent(content)
        overlay.setGeometry(content.rect())

        # Store reference for resize handling
        self._overlay = overlay
        self._content = content

    def resizeEvent(self, event):
        """Handle window resize to keep overlay matched to content."""
        super().resizeEvent(event)
        if hasattr(self, '_overlay') and hasattr(self, '_content'):
            self._overlay.setGeometry(self._content.rect())

    def _on_frame_ready(self, frame_data: FrameData):
        """Handle new frame from camera."""
        # Update video widget with frame and both bounding boxes
        self._video_widget.update_frame(
            frame_data.frame,
            frame_data.detection,
            frame_data.classification_bbox
        )

        # Determine if robot can continue moving
        # If distance > threshold, robot can move freely (target is far away)
        # If distance <= threshold, apply QR/vision safety checks
        if self._current_distance > self._distance_threshold:
            # Target is far away - robot can move freely
            can_continue = True
        else:
            # Target is close - use frame_data's safety logic
            can_continue = frame_data.can_continue_moving

        # Update safety banner
        self._safety_banner.can_continue = can_continue

        # Update secondary status indicators
        self._qr_status.setVisible(frame_data.qr_enabled)
        self._qr_status.detected = frame_data.robot_detected

        # Show/hide vision status based on whether Roboflow is enabled
        self._vision_status.setVisible(frame_data.roboflow_enabled)
        if frame_data.roboflow_enabled:
            self._vision_status.detected = frame_data.classification_detected
        
        # Record tracking data if tracking is active
        if self._tracking_button.is_tracking:
            self._tracking_button.record_frame(
                distance=self._current_distance,
                robot_detected=frame_data.classification_detected if frame_data.roboflow_enabled else False,
                qr_detected=frame_data.robot_detected if frame_data.qr_enabled else False
            )

    def _on_qr_toggled(self, enabled: bool):
        """Handle QR toggle change."""
        self._camera.qr_enabled = enabled
        self._qr_status.setVisible(enabled)

    def _on_roboflow_toggled(self, enabled: bool):
        """Handle Roboflow toggle change."""
        self._camera.roboflow_enabled = enabled
        self._vision_status.setVisible(enabled)

    def _on_smoothing_changed(self, value: float):
        """Handle smoothing slider change."""
        self._camera.smoothing_alpha = value

    def _on_threshold_changed(self, value: int):
        """Handle distance threshold change."""
        self._distance_threshold = value

    def _on_distance_updated(self, distance: int):
        """Handle new distance reading."""
        self._current_distance = distance
        self._distance_display.set_distance(distance)

    def _on_error(self, message: str):
        """Handle camera errors."""
        QMessageBox.critical(self, "Camera Error", message)

    def closeEvent(self, event):
        """Clean up when window closes."""
        self._camera.stop()
        self._distance_sensor.stop()
        super().closeEvent(event)
