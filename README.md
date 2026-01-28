# Robot QR Detection - Desktop Application

A Python desktop application that detects and tracks a specific QR code marker ("ROBOT_R1") using your laptop's webcam.

## Features

- **Real-time QR Detection**: Uses OpenCV's built-in QRCodeDetector for fast, reliable detection
- **Targeted Tracking**: Only responds to QR codes with the payload "ROBOT_R1"
- **Visual Stabilization**: 
  - Exponential smoothing to reduce jitter in the bounding box
  - Persistence to maintain tracking during momentary occlusions
- **Full GUI**: 
  - Live camera feed with overlay
  - Green bounding box around detected robot
  - Status banner indicating detection state
  - Adjustable smoothing control

## Requirements

- Python 3.8+
- macOS, Windows, or Linux
- Webcam

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (macOS only) Grant camera permissions:
   - Go to **System Preferences > Privacy & Security > Camera**
   - Enable camera access for Terminal or your Python environment

## Usage

```bash
python main.py
```

### Selecting a Camera (including Continuity Camera)

This app uses OpenCV (`cv2.VideoCapture(index)`) and by default opens **camera index 0**.
If your desired camera (e.g., iPhone Continuity Camera) is a different index, probe and select it:

```bash
python main.py --list-cameras
python main.py --camera-index 1
```

The application will:
1. Open your default webcam
2. Display the live feed in a window
3. Show "Robot R1 detected" (green banner) when the target QR code is visible
4. Draw a bounding box around the detected QR code

### Adjusting Smoothing

Click the ⚙ button in the bottom-right corner to access the smoothing control:
- **Lower values (0.1-0.3)**: Smoother motion, but more lag
- **Higher values (0.7-0.9)**: Snappier response, but more jitter
- **Default (0.6)**: Balanced between smoothness and responsiveness

## Creating a Test QR Code

Generate a QR code with the exact payload `ROBOT_R1` using any QR code generator, for example:
- https://www.qr-code-generator.com/
- https://www.the-qrcode-generator.com/

Print or display the QR code on screen to test the detection.

## Troubleshooting

### Camera not working
- Check that no other application is using the camera
- On macOS: Grant camera permissions in System Preferences
- Try unplugging and replugging external cameras

### Qt plugin errors
The application automatically handles Qt plugin paths for Anaconda environments. If you still see errors, try:
```bash
export QT_PLUGIN_PATH=$(python -c "import PyQt6; print(PyQt6.__path__[0])")/Qt6/plugins
```

### QR code not detected
- Ensure good lighting
- Hold the QR code steady
- Make sure the QR code payload is exactly "ROBOT_R1" (case-sensitive)
- Try moving closer or farther from the camera

