"""
Video display widget with bounding box overlay.
Renders the camera feed and draws detection overlays.
"""

import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QImage, QColor, QPen, QBrush, QFont
from typing import Optional

from smoothing import BoundingBox, DetectedQR
from camera_manager import ClassificationBBox


class VideoWidget(QWidget):
    """
    Custom widget that displays camera frames and overlays bounding boxes.
    Handles coordinate conversion and rendering of detection results.
    """

    # Colors for QR code detection
    QR_BOX_COLOR = QColor(34, 197, 94)  # Green
    QR_LABEL_BG_COLOR = QColor(34, 197, 94)
    QR_LABEL_TEXT_COLOR = QColor(255, 255, 255)

    # Colors for Roboflow classification detection
    CLASSIFICATION_BOX_COLOR = QColor(59, 130, 246)  # Blue
    CLASSIFICATION_LABEL_BG_COLOR = QColor(59, 130, 246)
    CLASSIFICATION_LABEL_TEXT_COLOR = QColor(255, 255, 255)

    # Styling
    BOX_LINE_WIDTH = 3
    BOX_CORNER_RADIUS = 8
    LABEL_FONT_SIZE = 12
    BOX_PADDING_RATIO = 0.2  # 20% padding around detection

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_frame: Optional[np.ndarray] = None
        self._current_detection: Optional[DetectedQR] = None
        self._classification_bbox: Optional[ClassificationBBox] = None
        self._q_image: Optional[QImage] = None

        # Widget sizing
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 480)

        # Enable smooth scaling
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def update_frame(
        self,
        frame: np.ndarray,
        detection: Optional[DetectedQR],
        classification_bbox: Optional[ClassificationBBox] = None,
    ):
        """
        Update the displayed frame and detection.
        Called from the main thread when new frame data arrives.
        """
        self._current_frame = frame
        self._current_detection = detection
        self._classification_bbox = classification_bbox

        # Convert OpenCV BGR frame to QImage
        if frame is not None:
            height, width, channels = frame.shape
            bytes_per_line = channels * width
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._q_image = QImage(
                rgb_frame.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            ).copy()  # Copy to ensure data ownership

        self.update()  # Trigger repaint

    def paintEvent(self, event):
        """Paint the frame and overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        if self._q_image is None:
            # No frame yet - show placeholder
            painter.setPen(QColor(128, 128, 128))
            painter.setFont(QFont("Arial", 14))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Waiting for camera..."
            )
            return

        # Calculate scaled image rect (maintain aspect ratio)
        img_rect = self._calculate_image_rect()

        # Draw the frame
        scaled_image = self._q_image.scaled(
            img_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        painter.drawImage(img_rect.topLeft(), scaled_image)

        # Draw QR code bounding box overlay (green)
        if self._current_detection is not None:
            self._draw_qr_bounding_box(painter, img_rect)

        # Draw classification bounding box overlay (blue)
        if self._classification_bbox is not None:
            self._draw_classification_bounding_box(painter, img_rect)

    def _calculate_image_rect(self) -> QRect:
        """Calculate the rectangle where the image should be drawn."""
        if self._q_image is None:
            return self.rect()

        widget_w = self.width()
        widget_h = self.height()
        img_w = self._q_image.width()
        img_h = self._q_image.height()

        # Calculate scale to fit while maintaining aspect ratio
        scale = min(widget_w / img_w, widget_h / img_h)
        scaled_w = int(img_w * scale)
        scaled_h = int(img_h * scale)

        # Center the image
        x = (widget_w - scaled_w) // 2
        y = (widget_h - scaled_h) // 2

        return QRect(x, y, scaled_w, scaled_h)

    def _draw_qr_bounding_box(self, painter: QPainter, img_rect: QRect):
        """Draw the QR detection bounding box and label."""
        if self._current_detection is None or self._q_image is None:
            return

        box = self._current_detection.bounding_box

        # Add padding
        padded_box = box.with_padding(self.BOX_PADDING_RATIO)

        # Convert from frame coordinates to widget coordinates
        scale_x = img_rect.width() / self._q_image.width()
        scale_y = img_rect.height() / self._q_image.height()

        screen_x = img_rect.x() + int(padded_box.x * scale_x)
        screen_y = img_rect.y() + int(padded_box.y * scale_y)
        screen_w = int(padded_box.width * scale_x)
        screen_h = int(padded_box.height * scale_y)

        # Draw rounded rectangle border
        pen = QPen(self.QR_BOX_COLOR, self.BOX_LINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            screen_x, screen_y, screen_w, screen_h,
            self.BOX_CORNER_RADIUS, self.BOX_CORNER_RADIUS
        )

        # Draw label
        label_text = "Robot R1"
        self._draw_label(
            painter, label_text,
            screen_x, screen_y, screen_w, screen_h,
            self.QR_LABEL_BG_COLOR, self.QR_LABEL_TEXT_COLOR
        )

    def _draw_classification_bounding_box(self, painter: QPainter, img_rect: QRect):
        """Draw the Roboflow classification bounding box and label."""
        if self._classification_bbox is None or self._q_image is None:
            return

        bbox = self._classification_bbox

        # Add padding (20% on each side)
        pad_w = bbox.width * self.BOX_PADDING_RATIO
        pad_h = bbox.height * self.BOX_PADDING_RATIO
        padded_x = bbox.x - pad_w / 2
        padded_y = bbox.y - pad_h / 2
        padded_w = bbox.width + pad_w
        padded_h = bbox.height + pad_h

        # Convert from frame coordinates to widget coordinates
        scale_x = img_rect.width() / self._q_image.width()
        scale_y = img_rect.height() / self._q_image.height()

        screen_x = img_rect.x() + int(padded_x * scale_x)
        screen_y = img_rect.y() + int(padded_y * scale_y)
        screen_w = int(padded_w * scale_x)
        screen_h = int(padded_h * scale_y)

        # Draw rounded rectangle border
        pen = QPen(self.CLASSIFICATION_BOX_COLOR, self.BOX_LINE_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            screen_x, screen_y, screen_w, screen_h,
            self.BOX_CORNER_RADIUS, self.BOX_CORNER_RADIUS
        )

        # Draw label
        label_text = "Robot R1 (Vision)"
        self._draw_label(
            painter, label_text,
            screen_x, screen_y, screen_w, screen_h,
            self.CLASSIFICATION_LABEL_BG_COLOR, self.CLASSIFICATION_LABEL_TEXT_COLOR,
            position="bottom"  # Place below box to avoid overlapping with QR label
        )

    def _draw_label(
        self,
        painter: QPainter,
        text: str,
        box_x: int,
        box_y: int,
        box_w: int,
        box_h: int,
        bg_color: QColor,
        text_color: QColor,
        position: str = "top"
    ):
        """Draw a label for a bounding box."""
        font = QFont("Arial", self.LABEL_FONT_SIZE, QFont.Weight.Bold)
        painter.setFont(font)

        # Calculate label dimensions
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text)
        text_height = font_metrics.height()

        label_padding_h = 8
        label_padding_v = 4
        label_w = text_width + label_padding_h * 2
        label_h = text_height + label_padding_v * 2

        # Position label
        label_x = box_x
        if position == "top":
            label_y = box_y - label_h - 4
            # Ensure label stays within widget bounds
            if label_y < 0:
                label_y = box_y + box_h + 4
        else:  # bottom
            label_y = box_y + box_h + 4
            # Ensure label stays within widget bounds
            if label_y + label_h > self.height():
                label_y = box_y - label_h - 4

        # Draw label background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(label_x, label_y, label_w, label_h, 4, 4)

        # Draw label text
        painter.setPen(text_color)
        painter.drawText(
            label_x + label_padding_h,
            label_y + label_padding_v + font_metrics.ascent(),
            text
        )
