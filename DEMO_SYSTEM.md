ROBOT SAFETY DETECTION DEMO SYSTEM
===================================

OVERVIEW

This desktop application demonstrates a multi-sensor safety system for human-robot collaboration. It combines computer vision (camera-based QR code and object detection) with mmWave radar distance sensing to determine whether a robot can safely continue moving.


HOW IT WORKS

Sensor Inputs

1. Camera Feed - Captures live video from webcam
2. QR Code Detection - Scans for a specific QR code (ROBOT_R1) that identifies the robot
3. Vision Model - Uses YOLO/Roboflow to detect objects (currently configured for laptops/phones as robot proxies)
4. mmWave Radar - Measures distance to nearest target via serial connection


Safety Logic

The system uses a layered safety approach:

    Is Distance > Threshold?
        YES --> Robot can move freely (target is far away)
        NO  --> Apply detection checks:
                - If Vision Model ON: require BOTH QR code AND vision detection
                - If Vision Model OFF: require QR code detection only

Safety States:
    - Green ("Robot Can Continue Moving") - All safety conditions met
    - Red ("Robot Must Stop") - One or more safety conditions failed


UI Controls

    QR Detection     Toggle QR code scanning on/off
    Vision Model     Toggle YOLO/Roboflow object detection (default: ON)
    Safe dist        Distance threshold in cm (default: 100cm). Above this, robot moves freely
    Smoothing        Bounding box smoothing factor for stable visualization


Display Elements

    - Main Video Feed: Live camera with detection overlays (green box = QR, blue box = vision model)
    - Safety Banner: Large status indicator at top
    - Target Dist: Current mmWave distance reading in cm
    - QR Code / Vision Model Status: Individual detection states


CONFIGURATION

Environment variables (.env file):
    - USE_LOCAL_YOLO: Use local YOLO model instead of Roboflow API
    - YOLO_MODEL_PATH: Path to YOLO weights
    - YOLO_TARGET_CLASS: Object class to detect (e.g., "cell phone")
    - ROBOFLOW_API_KEY: API key for cloud-based detection


================================================================================
LIMITATIONS (DEMO VS. PRODUCTION SYSTEM)
================================================================================

1. NO ROBOT SHAPE VERIFICATION

Demo: Simply detects presence of QR code.

Production: QR code would encode the robot's expected shape/dimensions. The vision system would verify that the detected object matches the encoded shape, preventing spoofing (e.g., someone holding a printed QR code).


2. NO MULTI-SENSOR CORRELATION

Demo: Camera and mmWave operate independently.

Production: Would correlate mmWave tracking data with camera detection to verify the detected object is actually the robot, not a person standing behind a robot with a QR code trying to bypass safety.


3. BASIC MMWAVE USAGE

Demo: Simple distance threshold check.

Production: mmWave radar can detect micro-movements including breathing patterns. The system would:
    - Distinguish humans from robots by detecting respiratory signatures
    - Stop immediately if human breathing is detected within the safety zone
    - Track multiple targets and their movement patterns


4. NO TRAJECTORY PREDICTION

Demo: Point-in-time safety decision.

Production: Would predict robot and human trajectories to preemptively slow/stop before potential collision paths intersect.


5. SINGLE CAMERA LIMITATION

Demo: Single webcam with limited field of view.

Production: Multiple cameras for 360 degree coverage, depth cameras for precise 3D positioning, and sensor fusion across all inputs.


6. NO FAIL-SAFE REDUNDANCY

Demo: Software-only safety logic.

Production: Hardware safety interlocks, redundant sensor systems, and fail-safe defaults (robot stops if any sensor fails or communication is lost).


================================================================================
ARCHITECTURE
================================================================================

    +------------------+         +-------------------+
    |   USB Camera     |-------->|   CameraManager   |
    +------------------+         |   - QR Detection  |
                                 |   - YOLO/Roboflow |
                                 +---------+---------+
                                           |
                                           v
    +------------------+         +-------------------+         +------------------+
    |  mmWave Sensor   |-------->|    MainWindow     |-------->|  Safety Banner   |
    |  (Serial)        |         |  (Safety Logic)   |         |  (UI Output)     |
    +------------------+         +-------------------+         +------------------+


================================================================================
RUNNING THE DEMO
================================================================================

    cd desktop-qr-detection
    source .venv/bin/activate
    python main.py

Requirements: Python 3.11+, PyQt6, OpenCV, pyzbar, ultralytics (for local YOLO)
