//
//  Config.swift
//  robot-qr-detection
//

import Foundation

enum Config {
    static var roboflowAPIKey: String {
        // First try to get from environment
        if let key = ProcessInfo.processInfo.environment["ROBOFLOW_API_KEY"] {
            return key
        }

        // Fallback: try to read from .env file in project root
        if let envPath = Bundle.main.path(forResource: ".env", ofType: nil),
           let envContent = try? String(contentsOfFile: envPath, encoding: .utf8) {
            let lines = envContent.components(separatedBy: .newlines)
            for line in lines {
                let parts = line.components(separatedBy: "=")
                if parts.count == 2,
                   parts[0].trimmingCharacters(in: .whitespaces) == "ROBOFLOW_API_KEY" {
                    return parts[1].trimmingCharacters(in: .whitespaces)
                }
            }
        }

        // If no env variable or .env file found, return empty string
        // This will cause API calls to fail - which is safer than hardcoding
        fatalError("ROBOFLOW_API_KEY not found. Please set it in environment or .env file")
    }

    static let roboflowEndpoint = "https://serverless.roboflow.com/cdtm-x-mona/workflows/find-laptops"
}
