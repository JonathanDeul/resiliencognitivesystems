"""
Bounding box stabilization algorithms.
Implements persistence (debouncing) and exponential smoothing
to prevent flickering and jitter in the tracking overlay.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BoundingBox:
    """Represents a bounding box in pixel coordinates."""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center_x(self) -> float:
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        return self.y + self.height / 2
    
    def with_padding(self, padding_ratio: float = 0.2) -> 'BoundingBox':
        """Return a new box expanded by the given padding ratio."""
        pad_x = self.width * padding_ratio
        pad_y = self.height * padding_ratio
        return BoundingBox(
            x=self.x - pad_x,
            y=self.y - pad_y,
            width=self.width + pad_x * 2,
            height=self.height + pad_y * 2
        )


@dataclass
class DetectedQR:
    """Holds detected QR code information."""
    payload: str
    bounding_box: BoundingBox


class BoundingBoxSmoother:
    """
    Applies exponential smoothing and persistence to bounding box coordinates.
    
    - Persistence: Keeps the last known position for N frames after losing detection,
      preventing immediate disappearance on momentary occlusion.
    - Smoothing: Blends new coordinates with previous ones using exponential moving average,
      reducing jitter from frame-to-frame variations.
    """
    
    def __init__(self, persistence_frames: int = 5, smoothing_alpha: float = 0.6):
        """
        Args:
            persistence_frames: Number of frames to retain the box after losing detection.
            smoothing_alpha: Smoothing factor (0-1). Higher = more responsive, lower = smoother.
        """
        self.persistence_frames = persistence_frames
        self.smoothing_alpha = smoothing_alpha
        
        self._smoothed_box: Optional[BoundingBox] = None
        self._frames_without_detection: int = 0
        self._last_payload: Optional[str] = None
    
    @property
    def alpha(self) -> float:
        return self.smoothing_alpha
    
    @alpha.setter
    def alpha(self, value: float):
        self.smoothing_alpha = max(0.0, min(1.0, value))
    
    def update(self, detection: Optional[DetectedQR]) -> Optional[DetectedQR]:
        """
        Process a new detection (or None if nothing detected this frame).
        Returns the stabilized detection result.
        """
        if detection is not None:
            # Detection found - reset counter and apply smoothing
            self._frames_without_detection = 0
            self._last_payload = detection.payload
            smoothed_box = self._smooth_box(detection.bounding_box)
            return DetectedQR(payload=detection.payload, bounding_box=smoothed_box)
        else:
            # No detection this frame
            self._frames_without_detection += 1
            
            if self._frames_without_detection >= self.persistence_frames:
                # Exceeded persistence threshold - clear everything
                self._smoothed_box = None
                self._last_payload = None
                return None
            else:
                # Still within persistence window - return last known position
                if self._smoothed_box is not None and self._last_payload is not None:
                    return DetectedQR(
                        payload=self._last_payload,
                        bounding_box=self._smoothed_box
                    )
                return None
    
    def _smooth_box(self, new_box: BoundingBox) -> BoundingBox:
        """Apply exponential smoothing to the bounding box."""
        if self._smoothed_box is None:
            # First detection - no smoothing yet
            self._smoothed_box = new_box
            return new_box
        
        old = self._smoothed_box
        alpha = self.smoothing_alpha
        
        smoothed = BoundingBox(
            x=alpha * new_box.x + (1 - alpha) * old.x,
            y=alpha * new_box.y + (1 - alpha) * old.y,
            width=alpha * new_box.width + (1 - alpha) * old.width,
            height=alpha * new_box.height + (1 - alpha) * old.height
        )
        
        self._smoothed_box = smoothed
        return smoothed
    
    def reset(self):
        """Clear all state."""
        self._smoothed_box = None
        self._frames_without_detection = 0
        self._last_payload = None

