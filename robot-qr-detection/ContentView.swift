//
//  ContentView.swift
//  robot-qr-detection
//

import SwiftUI

struct ContentView: View {
    @State private var cameraManager = CameraManager()
    
    var body: some View {
        ZStack {
            switch cameraManager.permissionStatus {
            case .unknown:
                PermissionRequestView(onRequest: cameraManager.requestPermission)
                
            case .denied:
                PermissionDeniedView()
                
            case .granted:
                ScannerView(cameraManager: cameraManager)
            }
        }
        .ignoresSafeArea()
        .onAppear {
            if cameraManager.permissionStatus == .granted {
                cameraManager.setupSession()
                cameraManager.startSession()
            }
        }
        .onDisappear {
            cameraManager.stopSession()
        }
    }
}

// MARK: - Scanner View (main camera + overlay)
struct ScannerView: View {
    var cameraManager: CameraManager
    @State private var showSmoothingControl = false
    @State private var smoothingText = "0.6"

    var body: some View {
        GeometryReader { geo in
            ZStack {
                // camera feed
                CameraPreviewView(session: cameraManager.session)

                // QR code bounding box overlay (green)
                if let qr = cameraManager.detectedQR {
                    BoundingBoxOverlay(
                        boundingBox: qr.boundingBox,
                        viewSize: geo.size,
                        color: .green,
                        label: "Robot R1"
                    )
                }

                // Classification bounding box overlay (blue) - only when Roboflow enabled
                if cameraManager.roboflowEnabled, let bbox = cameraManager.classificationBBox {
                    BoundingBoxOverlay(
                        boundingBox: bbox.normalized,
                        viewSize: geo.size,
                        color: .blue,
                        label: "Robot R1 (Vision)",
                        labelPosition: .bottom
                    )
                }

                // three-tier status display
                VStack {
                    VStack(spacing: 12) {
                        // Primary status - Robot Can Continue Moving
                        PrimaryStatusBanner(canContinueMoving: cameraManager.canContinueMoving)

                        // QR Code detection status
                        SecondaryStatusBanner(
                            title: "QR Code",
                            isDetected: cameraManager.robotDetected
                        )

                        // Classification detection status (only when Roboflow enabled)
                        if cameraManager.roboflowEnabled {
                            SecondaryStatusBanner(
                                title: "Vision Model",
                                isDetected: cameraManager.classificationDetected
                            )
                        }
                    }
                    .padding(.top, 60)

                    Spacer()

                    // Bottom controls: Roboflow toggle on left, smoothing on right
                    HStack {
                        RoboflowToggle(isEnabled: Binding(
                            get: { cameraManager.roboflowEnabled },
                            set: { cameraManager.roboflowEnabled = $0 }
                        ))
                        .padding(.leading, 12)

                        Spacer()

                        SmoothingControl(
                            isExpanded: $showSmoothingControl,
                            smoothingText: $smoothingText,
                            onApply: {
                                if let value = Double(smoothingText), value >= 0, value <= 1 {
                                    cameraManager.smoothingAlpha = CGFloat(value)
                                }
                            }
                        )
                        .padding(.trailing, 12)
                    }
                    .padding(.bottom, 40)
                }
            }
        }
        .onAppear {
            cameraManager.setupSession()
            cameraManager.startSession()
            smoothingText = String(format: "%.1f", cameraManager.smoothingAlpha)
        }
    }
}

// MARK: - Roboflow Toggle
struct RoboflowToggle: View {
    @Binding var isEnabled: Bool

    var body: some View {
        Button(action: { isEnabled.toggle() }) {
            HStack(spacing: 8) {
                Image(systemName: isEnabled ? "eye.fill" : "eye.slash")
                    .font(.system(size: 14, weight: .medium))
                Text("Roboflow")
                    .font(.system(size: 14, weight: .medium))
                Text(isEnabled ? "ON" : "OFF")
                    .font(.system(size: 12, weight: .bold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(isEnabled ? Color.green : Color.gray)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.black.opacity(0.6))
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
    }
}

// MARK: - Smoothing Control
struct SmoothingControl: View {
    @Binding var isExpanded: Bool
    @Binding var smoothingText: String
    let onApply: () -> Void

    var body: some View {
        VStack(spacing: 8) {
            if isExpanded {
                VStack(spacing: 6) {
                    Text("Smooth")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.white.opacity(0.8))

                    TextField("0-1", text: $smoothingText)
                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                        .foregroundStyle(.white)
                        .multilineTextAlignment(.center)
                        .frame(width: 50)
                        .padding(.vertical, 6)
                        .background(Color.white.opacity(0.2))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                        .keyboardType(.decimalPad)
                        .onSubmit { onApply() }

                    Button(action: {
                        onApply()
                        isExpanded = false
                    }) {
                        Text("OK")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.white)
                            .frame(width: 50)
                            .padding(.vertical, 4)
                            .background(Color.blue)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                }
                .padding(10)
                .background(Color.black.opacity(0.7))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }

            Button(action: { isExpanded.toggle() }) {
                Image(systemName: "slider.horizontal.3")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(.white)
                    .frame(width: 36, height: 36)
                    .background(Color.black.opacity(0.5))
                    .clipShape(Circle())
            }
        }
    }
}

// MARK: - Status Banners

// Primary status - Robot Can Continue Moving
struct PrimaryStatusBanner: View {
    let canContinueMoving: Bool
    
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: canContinueMoving ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.system(size: 20, weight: .bold))
            
            Text(canContinueMoving ? "Robot Can Continue Moving" : "Robot Must Stop")
                .font(.system(size: 18, weight: .bold))
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 24)
        .padding(.vertical, 14)
        .background(
            Capsule()
                .fill(canContinueMoving ? Color.green : Color.red)
                .opacity(0.9)
        )
        .animation(.easeInOut(duration: 0.3), value: canContinueMoving)
    }
}

// Secondary status - QR Code & Classification
struct SecondaryStatusBanner: View {
    let title: String
    let isDetected: Bool
    
    var body: some View {
        HStack(spacing: 6) {
            Text(title + ":")
                .font(.system(size: 14, weight: .medium))
            
            Text(isDetected ? "Detected" : "Not Detected")
                .font(.system(size: 14, weight: .semibold))
            
            Image(systemName: isDetected ? "checkmark" : "xmark")
                .font(.system(size: 12, weight: .bold))
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(
            Capsule()
                .fill(isDetected ? Color.green.opacity(0.8) : Color.gray.opacity(0.7))
        )
        .animation(.easeInOut(duration: 0.2), value: isDetected)
    }
}

// MARK: - Bounding Box Overlay
enum LabelPosition {
    case top
    case bottom
}

struct BoundingBoxOverlay: View {
    let boundingBox: CGRect
    let viewSize: CGSize
    var color: Color = .green
    var label: String = "Robot R1"
    var labelPosition: LabelPosition = .top

    var body: some View {
        let rect = convertBoundingBox(boundingBox, to: viewSize)

        ZStack(alignment: .topLeading) {
            // colored box
            RoundedRectangle(cornerRadius: 8)
                .stroke(color, lineWidth: 3)
                .frame(width: rect.width, height: rect.height)
                .position(x: rect.midX, y: rect.midY)

            // label
            Text(label)
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(.white)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(color)
                .clipShape(RoundedRectangle(cornerRadius: 4))
                .position(
                    x: rect.minX + 50,
                    y: labelPosition == .top ? rect.minY - 15 : rect.maxY + 15
                )
        }
    }

    // Vision coords are normalized (0-1), origin bottom-left
    // Convert to screen coords with origin top-left, with some padding
    private func convertBoundingBox(_ box: CGRect, to size: CGSize) -> CGRect {
        let padding: CGFloat = 0.2  // 20% larger on each side
        let x = box.minX * size.width
        let y = (1 - box.maxY) * size.height  // flip Y
        let width = box.width * size.width
        let height = box.height * size.height

        // expand the box by padding amount
        let padX = width * padding
        let padY = height * padding
        return CGRect(
            x: x - padX,
            y: y - padY,
            width: width + padX * 2,
            height: height + padY * 2
        )
    }
}

// MARK: - Permission Views
struct PermissionRequestView: View {
    let onRequest: () -> Void
    
    var body: some View {
        ZStack {
            Color.black
            
            VStack(spacing: 24) {
                Image(systemName: "camera.fill")
                    .font(.system(size: 60))
                    .foregroundStyle(.white.opacity(0.8))
                
                Text("Camera Access Required")
                    .font(.title2.bold())
                    .foregroundStyle(.white)
                
                Text("This app needs camera access to detect robot QR markers.")
                    .font(.body)
                    .foregroundStyle(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                
                Button(action: onRequest) {
                    Text("Enable Camera")
                        .font(.headline)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 32)
                        .padding(.vertical, 14)
                        .background(Color.blue)
                        .clipShape(Capsule())
                }
                .padding(.top, 8)
            }
        }
    }
}

struct PermissionDeniedView: View {
    var body: some View {
        ZStack {
            Color.black
            
            VStack(spacing: 24) {
                Image(systemName: "camera.badge.exclamationmark")
                    .font(.system(size: 60))
                    .foregroundStyle(.orange)
                
                Text("Camera Access Denied")
                    .font(.title2.bold())
                    .foregroundStyle(.white)
                
                Text("Please enable camera access in Settings to use this app.")
                    .font(.body)
                    .foregroundStyle(.white.opacity(0.7))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
                
                Button(action: openSettings) {
                    Text("Open Settings")
                        .font(.headline)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 32)
                        .padding(.vertical, 14)
                        .background(Color.orange)
                        .clipShape(Capsule())
                }
                .padding(.top, 8)
            }
        }
    }
    
    private func openSettings() {
        #if os(iOS)
        if let url = URL(string: UIApplication.openSettingsURLString) {
            UIApplication.shared.open(url)
        }
        #endif
    }
}

#Preview {
    ContentView()
}
