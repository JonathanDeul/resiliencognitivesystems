"""Local YOLO inference client for object detection."""

import logging
from typing import Optional

import numpy as np

from config import YOLO_CONFIDENCE, YOLO_INPUT_SIZE, YOLO_MODEL_PATH, YOLO_TARGET_CLASS
from roboflow_client import RoboflowDetection, RoboflowResult

logger = logging.getLogger(__name__)


class LocalYoloClient:
    """Run YOLO locally using ultralytics."""

    def __init__(self, model_path: Optional[str] = None):
        self._model_path = model_path or YOLO_MODEL_PATH
        self._model = None
        self._names = None
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as e:
            logger.error(
                "Ultralytics not available. Install with `pip install ultralytics`."
            )
            raise e

        logger.info(f"Loading YOLO model from {self._model_path}")
        self._model = YOLO(self._model_path)
        self._names = self._model.names

    def detect(self, frame: np.ndarray) -> RoboflowResult:
        """
        Run local YOLO detection on a frame.

        Args:
            frame: BGR image from OpenCV

        Returns:
            RoboflowResult with detection information
        """
        if self._model is None:
            return RoboflowResult(
                detected=False,
                detection=None,
                image_width=frame.shape[1],
                image_height=frame.shape[0],
            )

        try:
            results = self._model.predict(
                frame,
                imgsz=YOLO_INPUT_SIZE,
                conf=YOLO_CONFIDENCE,
                verbose=False,
            )
            if not results:
                return RoboflowResult(
                    detected=False,
                    detection=None,
                    image_width=frame.shape[1],
                    image_height=frame.shape[0],
                )

            best_det = None
            best_conf = 0.0
            names = self._names or {}

            boxes = results[0].boxes
            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls.item())
                    class_name = names.get(cls_id, str(cls_id))
                    conf = float(box.conf.item())
                    if class_name != YOLO_TARGET_CLASS:
                        continue
                    if conf >= best_conf:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        width = x2 - x1
                        height = y2 - y1
                        best_conf = conf
                        best_det = RoboflowDetection(
                            class_name=class_name,
                            confidence=conf,
                            x=x1 + width / 2,
                            y=y1 + height / 2,
                            width=width,
                            height=height,
                        )

            if best_det:
                return RoboflowResult(
                    detected=True,
                    detection=best_det,
                    image_width=frame.shape[1],
                    image_height=frame.shape[0],
                )

        except Exception as e:
            logger.error(f"Local YOLO inference failed: {e}")

        return RoboflowResult(
            detected=False,
            detection=None,
            image_width=frame.shape[1],
            image_height=frame.shape[0],
        )
