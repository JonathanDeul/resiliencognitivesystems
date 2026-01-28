# Robot QR Detection System - Code Features & Architecture

## High-Level Overview
This project implements a robust computer vision system designed to detect and track a specific robot (identified by the unique QR code payload `"ROBOT_R1"`) in real-time.

The core function of the application is to act as a visual tracking sensor. By utilizing a camera feed (such as a laptop webcam), it identifies the target robot's position in the frame, draws a stabilized bounding box around it, and reports its presence. The system is engineered to ignore irrelevant QR codes and focuses solely on the designated target.

Key capabilities include:
- **Targeted Identification**: Filters out noise and other QR codes, reacting only to the specific robot marker.
- **Visual Stabilization**: employs advanced smoothing algorithms to ensure the tracking box moves fluidly, avoiding the jitter common in raw computer vision outputs.
- **Robustness**: Handles momentary obstructions or lighting changes without immediately losing lock on the target.

---

## Technical Architecture Breakdown

This document provides a detailed technical breakdown of the codebase logic. The system is designed to perform real-time detection, tracking, and stabilization.

## 1. Camera & Session Management
**Core Logic:** `CameraManager.swift`

The `CameraManager` class acts as the central controller for `AVCaptureSession`.

- **Session Configuration**:
  - Uses `AVCaptureSession` with a `.high` resolution preset for optimal detection accuracy.
  - Configures the **back wide-angle camera** (`.builtInWideAngleCamera`) as the input device.
  - Adds an `AVCaptureVideoDataOutput` to intercept raw video frames for processing.
  - **Performance**: Sets `alwaysDiscardsLateVideoFrames = true` to drop frames if the processing queue is blocked, preventing memory spikes and latency.

- **Concurrency Model**:
  - **Processing**: Frame analysis occurs on a dedicated serial background queue (`"qr.processing"`).
  - **State Updates**: Detection results are dispatched back to the `@MainActor` to update SwiftUI views safely.

- **Permission Handling**:
  - Manages authorization states (`unknown`, `granted`, `denied`).
  - Contains specific logic to request video access via `AVCaptureDevice`.

## 2. Computer Vision & Detection Logic
**Core Logic:** `CameraManager.swift` (extension)

The system uses Apple's **Vision** framework for robust detection.

- **Detection Request**: Uses `VNDetectBarcodesRequest` instead of the older `AVMetadataOutput`. This allows for processing on specific frames and easier integration with other Vision requests if needed later.
- **Filtering**:
  - **Symbology**: Strictly filters for `.qr`.
  - **Payload Validation**: Checks `payloadStringValue` against the specific target string `"ROBOT_R1"`. All other QR codes are ignored.
- **Coordinates**:
  - The Vision framework returns **normalized coordinates** (0.0 to 1.0) with the origin at the **bottom-left**.
  - The UI layer is responsible for converting these to screen pixels and flipping the Y-axis to match the standard UI coordinate system (top-left origin).

## 3. Tracking Stabilization & Smoothing
**Core Logic:** `CameraManager.swift`

To ensure a professional feel and accurate tracking, the system implements two stabilization techniques:

### A. Persistence (Debouncing)
Prevents the bounding box from flickering when detection momentarily fails (due to motion blur, lighting, or partial occlusion).
- **Mechanism**: A counter `framesWithoutDetection` tracks missed frames.
- **Threshold**: The system maintains the last known position for **5 frames** (`persistenceFrames`) before considering the object lost.

### B. Exponential Smoothing
Prevents "jitter" in the bounding box caused by micro-fluctuations in detection coordinates.
- **Algorithm**: Linear interpolation (Lerp) between the old box and the new box.
  ```swift
  smoothed = (alpha * newBox) + ((1 - alpha) * oldBox)
  ```
- **Alpha (`smoothingAlpha`)**: A configurable factor (default `0.6`).
  - **Lower Alpha**: Smoother motion, but more "lag" (drag behind object).
  - **Higher Alpha**: Snappier response, but more jitter.

## 4. User Interface Architecture
**Core Logic:** `ContentView.swift`, `CameraPreviewView.swift`

- **Live Preview**:
  - Wraps `AVCaptureVideoPreviewLayer` in a `UIViewRepresentable` (iOS) or `NSViewRepresentable` (macOS).
  - Handles the rendering of the raw camera feed.

- **Dynamic Overlay**:
  - **Bounding Box**: A SwiftUI view drawn purely based on the normalized coordinates from the Vision result.
  - **Padding**: Adds **20% padding** around the detected QR code to ensure the box frames the marker nicely without touching edges.
  - **Label**: Displays a "Robot R1" tag attached to the box.

- **Interactive Controls**:
  - **Status Banner**: Visual feedback (Green/Gray pill) indicating global detection state.
  - **Smoothing Tuner**: An on-screen UI widget to adjust the `smoothingAlpha` value in real-time for testing.

## 5. Desktop Application Porting Strategy
To adapt this for a macOS desktop application, the following changes are required:

1.  **Camera Selection**:
    - Replace `AVCaptureDevice.default(.builtInWideAngleCamera...)` (which defaults to rear cameras on phones) with `AVCaptureDevice.DiscoverySession` to find the FaceTime HD Camera or external USB webcams.
2.  **Preview Layer**:
    - Replace `UIViewRepresentable` with `NSViewRepresentable`.
    - Wrap `NSView` instead of `UIView`.
3.  **Window Management**:
    - Ensure the window aspect ratio matches the camera preset (usually 4:3 or 16:9) to prevent letterboxing.
4.  **Permissions**:
    - Add `NSCameraUsageDescription` to the macOS target `Info.plist`.

