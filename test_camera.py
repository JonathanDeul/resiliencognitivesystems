#!/usr/bin/env python3
"""Simple camera test to trigger macOS permission dialog"""
import cv2
import sys
import time

print("=" * 50)
print("CAMERA PERMISSION TEST")
print("=" * 50)
print()
print("If you see a macOS permission dialog, click 'OK' to allow camera access.")
print("Then restart this script.")
print()
print("Attempting to access camera...")
sys.stdout.flush()

# This should trigger the permission dialog on macOS
cap = cv2.VideoCapture(0)

time.sleep(2)  # Give time for dialog to appear

if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print("✓ SUCCESS! Camera is working!")
        print(f"  Frame size: {frame.shape[1]}x{frame.shape[0]}")
    else:
        print("✗ Camera opened but cannot read frames")
    cap.release()
else:
    print("✗ Camera access denied")
    print()
    print("SOLUTION:")
    print("1. Open System Settings")
    print("2. Go to Privacy & Security → Camera")
    print("3. Enable camera access for Terminal")
    print("4. Run this script again")
