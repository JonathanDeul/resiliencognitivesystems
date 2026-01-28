"""Configuration management for the desktop QR detection app."""

import os
from pathlib import Path
from typing import Optional


def _load_env_file() -> dict[str, str]:
    """Load environment variables from .env file if it exists."""
    env_vars = {}
    env_path = Path(__file__).parent / ".env"

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")

    return env_vars


# Load .env file on module import
_env_file_vars = _load_env_file()


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable, checking .env file first, then system env."""
    return _env_file_vars.get(key) or os.environ.get(key) or default


# Roboflow configuration
ROBOFLOW_API_KEY: Optional[str] = get_env("ROBOFLOW_API_KEY")
ROBOFLOW_API_URL = "https://serverless.roboflow.com"
ROBOFLOW_WORKSPACE = "cdtm-x-mona"
ROBOFLOW_WORKFLOW_ID = "find-laptops"
ROBOFLOW_ENDPOINT = f"{ROBOFLOW_API_URL}/{ROBOFLOW_WORKSPACE}/workflows/{ROBOFLOW_WORKFLOW_ID}"

# Detection settings
ROBOFLOW_FRAME_INTERVAL = 3  # Send every Nth frame to Roboflow (lower = more responsive, more API calls)
ROBOFLOW_PERSISTENCE_FRAMES = 3  # Frames to persist detection after losing it
ROBOFLOW_TARGET_CLASS = "laptop"  # Class name to detect (mocked as robot)

# Local YOLO configuration
USE_LOCAL_YOLO = get_env("USE_LOCAL_YOLO", "false").lower() in ("1", "true", "yes")
YOLO_MODEL_PATH = get_env("YOLO_MODEL_PATH", "yolov8n.pt")  # downloaded by ultralytics if missing
YOLO_TARGET_CLASS = get_env("YOLO_TARGET_CLASS", "cell phone")
YOLO_INPUT_SIZE = int(get_env("YOLO_INPUT_SIZE", "640"))
YOLO_CONFIDENCE = float(get_env("YOLO_CONFIDENCE", "0.25"))
