"""Roboflow API client for object detection."""

import base64
import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import requests

from config import (
    ROBOFLOW_API_KEY,
    ROBOFLOW_ENDPOINT,
    ROBOFLOW_TARGET_CLASS,
)

logger = logging.getLogger(__name__)


@dataclass
class RoboflowDetection:
    """Represents a detection from Roboflow."""

    class_name: str
    confidence: float
    x: float  # Center x
    y: float  # Center y
    width: float
    height: float

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Return bounding box as (x, y, width, height) where x,y is top-left."""
        return (
            self.x - self.width / 2,
            self.y - self.height / 2,
            self.width,
            self.height,
        )


@dataclass
class RoboflowResult:
    """Result from Roboflow API call."""

    detected: bool
    detection: Optional[RoboflowDetection]
    image_width: int
    image_height: int


class RoboflowClient:
    """Client for Roboflow API calls."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ROBOFLOW_API_KEY
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def detect(self, frame: np.ndarray) -> RoboflowResult:
        """
        Send a frame to Roboflow for detection.

        Args:
            frame: BGR image from OpenCV

        Returns:
            RoboflowResult with detection information
        """
        if not self.api_key:
            logger.warning("Roboflow API key not configured")
            return RoboflowResult(
                detected=False,
                detection=None,
                image_width=frame.shape[1],
                image_height=frame.shape[0],
            )

        try:
            # Encode frame to JPEG base64
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            base64_image = base64.b64encode(buffer).decode("utf-8")

            # Prepare request payload
            payload = {
                "api_key": self.api_key,
                "inputs": {"image": {"type": "base64", "value": base64_image}},
            }

            # Make API request
            logger.debug(f"Sending frame to Roboflow ({frame.shape[1]}x{frame.shape[0]})")
            response = self._session.post(ROBOFLOW_ENDPOINT, json=payload, timeout=10)
            response.raise_for_status()

            result = self._parse_response(response.json(), frame.shape)
            if result.detected:
                det = result.detection
                logger.info(f"Roboflow: Detected '{det.class_name}' (conf: {det.confidence:.2f}) at ({det.x:.0f}, {det.y:.0f})")
            else:
                logger.debug("Roboflow: No detection")
            return result

        except requests.exceptions.Timeout:
            logger.warning("Roboflow API request timed out")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Roboflow API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Roboflow detection: {e}")

        return RoboflowResult(
            detected=False,
            detection=None,
            image_width=frame.shape[1],
            image_height=frame.shape[0],
        )

    def _parse_response(
        self, response: dict, frame_shape: tuple
    ) -> RoboflowResult:
        """Parse Roboflow API response."""
        height, width = frame_shape[:2]

        try:
            outputs = response.get("outputs", [])
            if not outputs:
                return RoboflowResult(
                    detected=False, detection=None, image_width=width, image_height=height
                )

            predictions_data = outputs[0].get("predictions", {})
            predictions = predictions_data.get("predictions", [])

            # Find target class detection (laptop = robot mock)
            for pred in predictions:
                if pred.get("class") == ROBOFLOW_TARGET_CLASS:
                    detection = RoboflowDetection(
                        class_name=pred["class"],
                        confidence=pred.get("confidence", 0),
                        x=pred.get("x", 0),
                        y=pred.get("y", 0),
                        width=pred.get("width", 0),
                        height=pred.get("height", 0),
                    )
                    return RoboflowResult(
                        detected=True,
                        detection=detection,
                        image_width=width,
                        image_height=height,
                    )

        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Failed to parse Roboflow response: {e}")

        return RoboflowResult(
            detected=False, detection=None, image_width=width, image_height=height
        )
