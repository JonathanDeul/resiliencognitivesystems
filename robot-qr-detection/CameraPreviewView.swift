//
//  CameraPreviewView.swift
//  robot-qr-detection
//

import SwiftUI
import AVFoundation

#if os(iOS)
struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession
    
    func makeUIView(context: Context) -> PreviewView {
        let view = PreviewView()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }
    
    func updateUIView(_ uiView: PreviewView, context: Context) {
        // session binding handled in makeUIView
    }
    
    class PreviewView: UIView {
        override class var layerClass: AnyClass {
            AVCaptureVideoPreviewLayer.self
        }
        
        var previewLayer: AVCaptureVideoPreviewLayer {
            layer as! AVCaptureVideoPreviewLayer
        }
    }
}
#else
// macOS fallback - just show placeholder
struct CameraPreviewView: View {
    let session: AVCaptureSession
    
    var body: some View {
        Rectangle()
            .fill(.black)
            .overlay {
                Text("Camera preview not available on this platform")
                    .foregroundStyle(.white)
            }
    }
}
#endif




