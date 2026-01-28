"""
UI control widgets: Status banner, smoothing slider, and Roboflow toggle.
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QSlider, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPainter, QColor, QBrush, QPen


class SafetyStatusBanner(QWidget):
    """
    Primary status banner showing whether robot can continue moving.
    Green when safe, red when must stop.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._can_continue = False

        # Fixed size for the pill
        self.setFixedHeight(44)
        self.setMinimumWidth(280)

        # Create label
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont("Arial", 14, QFont.Weight.DemiBold))
        self._label.setStyleSheet("color: white; background: transparent;")

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._update_display()

    @property
    def can_continue(self) -> bool:
        return self._can_continue

    @can_continue.setter
    def can_continue(self, value: bool):
        if self._can_continue != value:
            self._can_continue = value
            self._update_display()
            self.update()

    def _update_display(self):
        if self._can_continue:
            self._label.setText("Robot Can Continue Moving")
        else:
            self._label.setText("Robot Must Stop")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw pill background
        if self._can_continue:
            color = QColor(34, 197, 94)  # Green
        else:
            color = QColor(239, 68, 68)  # Red

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))

        # Draw rounded rect (pill shape)
        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)


class SecondaryStatusIndicator(QWidget):
    """
    Smaller status indicator for individual detection states.
    Shows label and detected/not detected status.
    """

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label_text = label
        self._detected = False

        self.setFixedHeight(28)
        self.setMinimumWidth(120)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        # Label
        self._title_label = QLabel(f"{label}:")
        self._title_label.setFont(QFont("Arial", 11, QFont.Weight.Medium))
        self._title_label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self._title_label)

        # Status
        self._status_label = QLabel()
        self._status_label.setFont(QFont("Arial", 11, QFont.Weight.DemiBold))
        self._status_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._update_display()

    @property
    def detected(self) -> bool:
        return self._detected

    @detected.setter
    def detected(self, value: bool):
        if self._detected != value:
            self._detected = value
            self._update_display()
            self.update()

    def _update_display(self):
        if self._detected:
            self._status_label.setText("Detected")
            self._status_label.setStyleSheet("color: #22C55E; background: transparent;")  # Green
        else:
            self._status_label.setText("Not Detected")
            self._status_label.setStyleSheet("color: #9CA3AF; background: transparent;")  # Gray

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))

        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)


class StatusBanner(QWidget):
    """
    Pill-shaped status indicator showing detection state.
    Green when robot detected, gray when not.
    (Legacy - kept for compatibility)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._detected = False

        # Fixed size for the pill
        self.setFixedHeight(44)
        self.setMinimumWidth(200)

        # Create label
        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont("Arial", 14, QFont.Weight.DemiBold))
        self._label.setStyleSheet("color: white; background: transparent;")

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        self._update_display()

    @property
    def detected(self) -> bool:
        return self._detected

    @detected.setter
    def detected(self, value: bool):
        if self._detected != value:
            self._detected = value
            self._update_display()
            self.update()

    def _update_display(self):
        if self._detected:
            self._label.setText("Robot R1 detected")
        else:
            self._label.setText("No robot marker detected")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw pill background
        if self._detected:
            color = QColor(34, 197, 94)  # Green
        else:
            color = QColor(107, 114, 128)  # Gray

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))

        # Draw rounded rect (pill shape)
        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)


class RoboflowToggle(QWidget):
    """
    Toggle switch for enabling/disabling Roboflow classification.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True  # Default to ON

        self.setFixedHeight(40)
        self.setMinimumWidth(160)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # Label
        self._label = QLabel("Vision Model")
        self._label.setFont(QFont("Arial", 11, QFont.Weight.Medium))
        self._label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self._label)

        # Toggle button
        self._toggle_btn = QPushButton("ON")
        self._toggle_btn.setFixedSize(60, 28)
        self._toggle_btn.setFont(QFont("Arial", 10, QFont.Weight.DemiBold))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        layout.addStretch()

        self._update_style()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if self._enabled != value:
            self._enabled = value
            self._update_style()

    def _on_toggle(self):
        self._enabled = not self._enabled
        self._update_style()
        self.toggled.emit(self._enabled)

    def _update_style(self):
        if self._enabled:
            self._toggle_btn.setText("ON")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22C55E;
                    color: white;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                }
            """)
        else:
            self._toggle_btn.setText("OFF")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6B7280;
                    color: white;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #4B5563;
                }
            """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))

        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)


class QRToggle(QWidget):
    """
    Toggle switch for enabling/disabling QR detection.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True

        self.setFixedHeight(40)
        self.setMinimumWidth(160)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # Label
        self._label = QLabel("QR Detection")
        self._label.setFont(QFont("Arial", 11, QFont.Weight.Medium))
        self._label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self._label)

        # Toggle button
        self._toggle_btn = QPushButton("ON")
        self._toggle_btn.setFixedSize(60, 28)
        self._toggle_btn.setFont(QFont("Arial", 10, QFont.Weight.DemiBold))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        layout.addStretch()

        self._update_style()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        if self._enabled != value:
            self._enabled = value
            self._update_style()

    def _on_toggle(self):
        self._enabled = not self._enabled
        self._update_style()
        self.toggled.emit(self._enabled)

    def _update_style(self):
        if self._enabled:
            self._toggle_btn.setText("ON")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22C55E;
                    color: white;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                }
            """)
        else:
            self._toggle_btn.setText("OFF")
            self._toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6B7280;
                    color: white;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #4B5563;
                }
            """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))

        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)


class SmoothingControl(QWidget):
    """
    Collapsible control panel for adjusting the smoothing alpha value.
    """

    smoothing_changed = pyqtSignal(float)

    def __init__(self, initial_value: float = 0.6, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._value = initial_value

        self.setFixedWidth(180)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Collapsible panel
        self._panel = QFrame()
        self._panel.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
            }
        """)
        self._panel.setVisible(False)

        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(8)

        # Title
        title = QLabel("Smoothing")
        title.setFont(QFont("Arial", 10, QFont.Weight.Medium))
        title.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(title)

        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(int(initial_value * 100))
        self._slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid rgba(255, 255, 255, 0.3);
                height: 6px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
        """)
        self._slider.valueChanged.connect(self._on_slider_changed)
        panel_layout.addWidget(self._slider)

        # Value display
        self._value_label = QLabel(f"{initial_value:.2f}")
        self._value_label.setFont(QFont("Menlo", 14, QFont.Weight.Medium))
        self._value_label.setStyleSheet("color: white; background: transparent;")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self._value_label)

        # Description
        desc = QLabel("Lower = smoother\nHigher = snappier")
        desc.setFont(QFont("Arial", 9))
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.6); background: transparent;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(desc)

        main_layout.addWidget(self._panel)

        # Toggle button
        self._toggle_btn = QPushButton("⚙")
        self._toggle_btn.setFixedSize(40, 40)
        self._toggle_btn.setFont(QFont("Arial", 18))
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.7);
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_panel)

        # Container for button alignment
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        btn_layout.addWidget(self._toggle_btn)

        main_layout.addWidget(btn_container)
        main_layout.addStretch()

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val: float):
        self._value = max(0.0, min(1.0, val))
        self._slider.blockSignals(True)
        self._slider.setValue(int(self._value * 100))
        self._slider.blockSignals(False)
        self._value_label.setText(f"{self._value:.2f}")

    def _toggle_panel(self):
        self._expanded = not self._expanded
        self._panel.setVisible(self._expanded)

    def _on_slider_changed(self, value: int):
        self._value = value / 100.0
        self._value_label.setText(f"{self._value:.2f}")
        self.smoothing_changed.emit(self._value)


class DistanceThresholdControl(QWidget):
    """
    Small control for setting the distance threshold.
    If target is farther than threshold, robot can move freely.
    """

    threshold_changed = pyqtSignal(int)

    def __init__(self, initial_value: int = 100, parent=None):
        super().__init__(parent)
        self._threshold = initial_value

        self.setFixedHeight(36)
        self.setMinimumWidth(200)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Label
        self._label = QLabel("Safe dist:")
        self._label.setFont(QFont("Arial", 10, QFont.Weight.Medium))
        self._label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        layout.addWidget(self._label)

        # Spinbox for threshold value
        self._spinbox = QSpinBox()
        self._spinbox.setRange(10, 500)
        self._spinbox.setValue(initial_value)
        self._spinbox.setSuffix(" cm")
        self._spinbox.setFixedWidth(90)
        self._spinbox.setFont(QFont("Arial", 10, QFont.Weight.Medium))
        self._spinbox.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                padding: 2px 6px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid white;
                width: 0; height: 0;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid white;
                width: 0; height: 0;
            }
        """)
        self._spinbox.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._spinbox)

        layout.addStretch()

    @property
    def threshold(self) -> int:
        return self._threshold

    @threshold.setter
    def threshold(self, value: int):
        self._threshold = value
        self._spinbox.blockSignals(True)
        self._spinbox.setValue(value)
        self._spinbox.blockSignals(False)

    def _on_value_changed(self, value: int):
        self._threshold = value
        self.threshold_changed.emit(value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))

        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)


class DistanceDisplay(QWidget):
    """
    Displays the distance reading with large, readable text.
    """
    def __init__(self, label: str = "Distance", unit: str = "cm", parent=None):
        super().__init__(parent)
        self._distance = 0
        self._unit = unit

        self.setFixedHeight(44)
        self.setMinimumWidth(180)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        # Label
        self._title_label = QLabel(f"{label}:")
        self._title_label.setFont(QFont("Arial", 14, QFont.Weight.Medium))
        self._title_label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self._title_label)

        # Distance value - large and bold
        self._status_label = QLabel(f"-- {unit}")
        self._status_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self._status_label.setStyleSheet("color: #3B82F6; background: transparent;")  # Blue color
        layout.addWidget(self._status_label)

        layout.addStretch()

    def set_distance(self, distance: int):
        self._distance = distance
        self._status_label.setText(f"{distance} {self._unit}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))

        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)


class TrackingButton(QWidget):
    """
    Button to start/stop tracking session that captures 2000 frames.
    Records distance, robot detection status, and QR code detection status.
    """
    
    tracking_started = pyqtSignal()
    tracking_stopped = pyqtSignal()
    
    def __init__(self, target_frames: int = 2000, parent=None):
        super().__init__(parent)
        self._is_tracking = False
        self._target_frames = target_frames
        self._current_frame = 0
        self._data = []  # List to store captured data
        
        self.setFixedHeight(40)
        self.setMinimumWidth(200)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)
        
        # Label
        self._label = QLabel("Tracking")
        self._label.setFont(QFont("Arial", 11, QFont.Weight.Medium))
        self._label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self._label)
        
        # Start/Stop button
        self._btn = QPushButton("Start")
        self._btn.setFixedSize(80, 28)
        self._btn.setFont(QFont("Arial", 10, QFont.Weight.DemiBold))
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.clicked.connect(self._on_click)
        layout.addWidget(self._btn)
        
        # Progress label
        self._progress_label = QLabel("")
        self._progress_label.setFont(QFont("Arial", 10))
        self._progress_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        layout.addWidget(self._progress_label)
        
        layout.addStretch()
        
        self._update_style()
    
    @property
    def is_tracking(self) -> bool:
        return self._is_tracking
    
    @property
    def current_frame(self) -> int:
        return self._current_frame
    
    @property
    def target_frames(self) -> int:
        return self._target_frames
    
    def _on_click(self):
        if self._is_tracking:
            self.stop_tracking()
        else:
            self.start_tracking()
    
    def start_tracking(self):
        """Start a new tracking session."""
        self._is_tracking = True
        self._current_frame = 0
        self._data = []
        self._update_style()
        self._update_progress()
        self.tracking_started.emit()
    
    def stop_tracking(self):
        """Stop tracking and save the data."""
        self._is_tracking = False
        self._save_data()
        self._update_style()
        self._progress_label.setText("Saved!")
        self.tracking_stopped.emit()
    
    def record_frame(self, distance: int, robot_detected: bool, qr_detected: bool):
        """
        Record data for the current frame.
        
        Args:
            distance: Distance reading in cm
            robot_detected: Whether robot was detected via vision model
            qr_detected: Whether QR code was detected
        """
        if not self._is_tracking:
            return
            
        from datetime import datetime
        
        self._data.append({
            'frame': self._current_frame,
            'timestamp': datetime.now().isoformat(),
            'distance_cm': distance,
            'robot_detected': robot_detected,
            'qr_detected': qr_detected
        })
        
        self._current_frame += 1
        self._update_progress()
        
        # Auto-stop when target reached
        if self._current_frame >= self._target_frames:
            self.stop_tracking()
    
    def _update_progress(self):
        if self._is_tracking:
            percentage = (self._current_frame / self._target_frames) * 100
            self._progress_label.setText(f"{self._current_frame}/{self._target_frames} ({percentage:.1f}%)")
        else:
            self._progress_label.setText("")
    
    def _save_data(self):
        """Save captured data to a CSV file."""
        if not self._data:
            return
            
        import csv
        from datetime import datetime
        import os
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(logs_dir, f'tracking_{timestamp}.csv')
        
        # Write data to CSV
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['frame', 'timestamp', 'distance_cm', 'robot_detected', 'qr_detected'])
            writer.writeheader()
            writer.writerows(self._data)
        
        print(f"Tracking data saved to: {filename}")
    
    def _update_style(self):
        if self._is_tracking:
            self._btn.setText("Stop")
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                }
            """)
        else:
            self._btn.setText("Start")
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                    border: none;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #2563EB;
                }
            """)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw semi-transparent background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))

        radius = self.height() // 2
        painter.drawRoundedRect(self.rect(), radius, radius)

