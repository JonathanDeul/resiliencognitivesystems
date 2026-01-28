//
//  CameraManager.swift
//  robot-qr-detection
//

import AVFoundation
import Vision
import SwiftUI

// tracks camera permission state
enum CameraPermission: Sendable {
    case unknown
    case granted
    case denied
}

// holds detected QR info
struct DetectedQR: Equatable, Sendable {
    let payload: String
    let boundingBox: CGRect  // normalized coords (0-1)
}

// holds classification bounding box (pixel coordinates)
struct ClassificationBBox: Equatable, Sendable {
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat
    let imageWidth: CGFloat
    let imageHeight: CGFloat

    // Normalized bounding box (0-1 range)
    var normalized: CGRect {
        CGRect(
            x: x / imageWidth,
            y: y / imageHeight,
            width: width / imageWidth,
            height: height / imageHeight
        )
    }
}

@MainActor
@Observable
final class CameraManager: NSObject {
    var permissionStatus: CameraPermission = .unknown
    var robotDetected: Bool = false
    var detectedQR: DetectedQR?
    var classificationDetected: Bool = false
    var classificationBBox: ClassificationBBox?
    var canContinueMoving: Bool = false

    // Roboflow toggle (default OFF)
    var roboflowEnabled: Bool = false {
        didSet {
            if !roboflowEnabled {
                // Clear classification state when disabled
                classificationDetected = false
                classificationBBox = nil
                framesWithoutClassification = 0
            }
            updateCanContinueMoving()
        }
    }

    // how many frames without detection before we clear the box
    private let persistenceFrames = 3
    private var framesWithoutDetection = 0
    private var framesWithoutClassification = 0

    // smoothing: lower alpha = smoother but laggier, higher = more responsive
    var smoothingAlpha: CGFloat = 0.6
    private var smoothedBoundingBox: CGRect?

    // Roboflow configuration
    // private let roboflowAPIKey = "kv3J0L9qAUKkULgh6RLv"
    private let roboflowEndpoint = "https://serverless.roboflow.com/cdtm-x-mona/workflows/find-laptops"

    // Frame throttling for Roboflow API calls
    private var frameCounter: Int = 0
    private let roboflowFrameInterval = 3
    
    // AVFoundation stuff needs to be nonisolated
    nonisolated let session = AVCaptureSession()
    private nonisolated let videoOutput = AVCaptureVideoDataOutput()
    private nonisolated let processingQueue = DispatchQueue(label: "qr.processing", qos: .userInitiated)
    
    private var isSessionConfigured = false
    
    override nonisolated init() {
        super.init()
        Task { @MainActor in
            self.checkPermission()
        }
    }
    
    func checkPermission() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            permissionStatus = .granted
        case .denied, .restricted:
            permissionStatus = .denied
        case .notDetermined:
            permissionStatus = .unknown
        @unknown default:
            permissionStatus = .unknown
        }
    }
    
    nonisolated func requestPermission() {
        AVCaptureDevice.requestAccess(for: .video) { granted in
            Task { @MainActor in
                self.permissionStatus = granted ? .granted : .denied
                if granted {
                    self.setupSession()
                }
            }
        }
    }
    
    func setupSession() {
        guard !isSessionConfigured else { return }
        
        session.beginConfiguration()
        session.sessionPreset = .high
        
        // camera input
        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: camera) else {
            session.commitConfiguration()
            return
        }
        
        if session.canAddInput(input) {
            session.addInput(input)
        }
        
        // video output for frame processing
        videoOutput.setSampleBufferDelegate(self, queue: processingQueue)
        videoOutput.alwaysDiscardsLateVideoFrames = true
        
        if session.canAddOutput(videoOutput) {
            session.addOutput(videoOutput)
        }
        
        session.commitConfiguration()
        isSessionConfigured = true
    }
    
    func startSession() {
        guard isSessionConfigured, !session.isRunning else { return }
        processingQueue.async {
            self.session.startRunning()
        }
    }
    
    func stopSession() {
        guard session.isRunning else { return }
        processingQueue.async {
            self.session.stopRunning()
        }
    }
    
    // MARK: - Roboflow API Integration
    private nonisolated func sendFrameToRoboflow(_ pixelBuffer: CVPixelBuffer) {
        Task {
            do {
                // Convert pixel buffer to JPEG data
                let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
                let context = CIContext()
                
                guard let cgImage = context.createCGImage(ciImage, from: ciImage.extent) else {
                    print("Failed to create CGImage from pixel buffer")
                    return
                }
                
                #if os(iOS)
                let uiImage = UIImage(cgImage: cgImage)
                guard let jpegData = uiImage.jpegData(compressionQuality: 0.7) else {
                    print("Failed to convert image to JPEG")
                    return
                }
                #else
                // macOS fallback (not used in iOS app)
                return
                #endif
                
                // Encode to base64
                let base64String = jpegData.base64EncodedString()
                
                // Prepare request
                guard let url = URL(string: roboflowEndpoint) else {
                    print("Invalid Roboflow URL")
                    return
                }
                
                var request = URLRequest(url: url)
                request.httpMethod = "POST"
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                
                let payload: [String: Any] = [
                    "api_key": roboflowAPIKey,
                    "inputs": [
                        "image": [
                            "type": "base64",
                            "value": base64String
                        ]
                    ]
                ]
                
                request.httpBody = try JSONSerialization.data(withJSONObject: payload)
                
                // Make the request
                let (data, response) = try await URLSession.shared.data(for: request)
                
                // Check HTTP response
                if let httpResponse = response as? HTTPURLResponse {
                    guard httpResponse.statusCode == 200 else {
                        print("Roboflow API error: HTTP \(httpResponse.statusCode)")
                        return
                    }
                }
                
                // Get image dimensions for bounding box conversion
                let imageWidth = CGFloat(CVPixelBufferGetWidth(pixelBuffer))
                let imageHeight = CGFloat(CVPixelBufferGetHeight(pixelBuffer))

                // Parse response
                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let outputs = json["outputs"] as? [[String: Any]],
                   let firstOutput = outputs.first,
                   let predictions = firstOutput["predictions"] as? [String: Any],
                   let predictionsArray = predictions["predictions"] as? [[String: Any]] {

                    // Look for "laptop" class in predictions and extract bbox
                    var laptopBBox: ClassificationBBox?
                    for prediction in predictionsArray {
                        if let className = prediction["class"] as? String, className == "laptop" {
                            // Extract bounding box (center coordinates from Roboflow)
                            if let x = prediction["x"] as? Double,
                               let y = prediction["y"] as? Double,
                               let width = prediction["width"] as? Double,
                               let height = prediction["height"] as? Double {
                                // Roboflow returns center coords, convert to top-left
                                laptopBBox = ClassificationBBox(
                                    x: CGFloat(x - width / 2),
                                    y: CGFloat(y - height / 2),
                                    width: CGFloat(width),
                                    height: CGFloat(height),
                                    imageWidth: imageWidth,
                                    imageHeight: imageHeight
                                )
                            }
                            break
                        }
                    }

                    // Update classification state on main thread
                    await MainActor.run {
                        self.updateClassificationDetection(laptopBBox != nil, bbox: laptopBBox)
                    }
                } else {
                    // No predictions found
                    await MainActor.run {
                        self.updateClassificationDetection(false, bbox: nil)
                    }
                }
                
            } catch {
                print("Roboflow API error: \(error.localizedDescription)")
            }
        }
    }
    
    @MainActor
    private func updateClassificationDetection(_ detected: Bool, bbox: ClassificationBBox?) {
        if detected {
            framesWithoutClassification = 0
            classificationDetected = true
            classificationBBox = bbox
        } else {
            framesWithoutClassification += 1

            if framesWithoutClassification >= persistenceFrames {
                classificationDetected = false
                classificationBBox = nil
            }
        }

        updateCanContinueMoving()
    }

    @MainActor
    private func updateCanContinueMoving() {
        // Update overall movement permission
        // If Roboflow is disabled, only QR detection matters
        if roboflowEnabled {
            canContinueMoving = robotDetected && classificationDetected
        } else {
            canContinueMoving = robotDetected
        }
    }
}

// MARK: - Frame processing + QR detection
extension CameraManager: AVCaptureVideoDataOutputSampleBufferDelegate {
    nonisolated func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        // Call Roboflow if enabled (every Nth frame)
        Task { @MainActor in
            guard self.roboflowEnabled else { return }
            self.frameCounter += 1
            if self.frameCounter % self.roboflowFrameInterval == 0 {
                self.sendFrameToRoboflow(pixelBuffer)
            }
        }
        
        let request = VNDetectBarcodesRequest { [weak self] request, error in
            guard let self = self else { return }
            guard error == nil,
                  let results = request.results as? [VNBarcodeObservation] else {
                self.updateDetection(nil)
                return
            }
            
            // look for our robot QR
            let robotQR = results.first { barcode in
                barcode.symbology == .qr &&
                barcode.payloadStringValue == "ROBOT_R1"
            }
            
            if let qr = robotQR {
                let detected = DetectedQR(
                    payload: qr.payloadStringValue ?? "",
                    boundingBox: qr.boundingBox
                )
                self.updateDetection(detected)
            } else {
                self.updateDetection(nil)
            }
        }
        
        // only look for QR codes
        request.symbologies = [.qr]
        
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .right)
        try? handler.perform([request])
    }
    
    private nonisolated func updateDetection(_ qr: DetectedQR?) {
        Task { @MainActor in
            if let qr = qr {
                // detected - reset counter
                self.framesWithoutDetection = 0
                self.robotDetected = true
                
                // apply exponential smoothing to bounding box
                let smoothedBox = self.smoothBox(qr.boundingBox)
                self.detectedQR = DetectedQR(payload: qr.payload, boundingBox: smoothedBox)
            } else {
                // not detected this frame
                self.framesWithoutDetection += 1
                
                // only clear after N consecutive frames without detection
                if self.framesWithoutDetection >= self.persistenceFrames {
                    self.detectedQR = nil
                    self.robotDetected = false
                    self.smoothedBoundingBox = nil  // reset smoothing
                }
                // otherwise keep the old bounding box in place
            }
            
            // Update overall movement permission
            self.updateCanContinueMoving()
        }
    }

    // blend new box with previous smoothed box
    private func smoothBox(_ newBox: CGRect) -> CGRect {
        guard let oldBox = smoothedBoundingBox else {
            // first detection, no smoothing yet
            smoothedBoundingBox = newBox
            return newBox
        }
        
        let alpha = smoothingAlpha
        let smoothed = CGRect(
            x: alpha * newBox.origin.x + (1 - alpha) * oldBox.origin.x,
            y: alpha * newBox.origin.y + (1 - alpha) * oldBox.origin.y,
            width: alpha * newBox.width + (1 - alpha) * oldBox.width,
            height: alpha * newBox.height + (1 - alpha) * oldBox.height
        )
        
        smoothedBoundingBox = smoothed
        return smoothed
    }
}
