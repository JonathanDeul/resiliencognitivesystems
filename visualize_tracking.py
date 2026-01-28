#!/usr/bin/env python3
"""
Tracking Data Visualizer

Reads a tracking CSV log file and creates a PNG graph showing:
- Frame number on X axis
- QR code detection status (binary)
- YOLO robot detection status (binary)
- Distance readings

Usage: python visualize_tracking.py <log_file.csv>
"""

import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


def load_tracking_data(csv_path: str) -> dict:
    """Load tracking data from CSV file."""
    data = {
        'frame': [],
        'distance_cm': [],
        'robot_detected': [],
        'qr_detected': []
    }
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data['frame'].append(int(row['frame']))
            data['distance_cm'].append(int(row['distance_cm']))
            data['robot_detected'].append(row['robot_detected'] == 'True')
            data['qr_detected'].append(row['qr_detected'] == 'True')
    
    return data


def create_visualization(data: dict, output_path: str):
    """Create and save a visualization of the tracking data."""
    frames = np.array(data['frame'])
    distances = np.array(data['distance_cm'])
    robot_detected = np.array(data['robot_detected']).astype(int)
    qr_detected = np.array(data['qr_detected']).astype(int)
    
    # Robot stops: distance < 150 AND robot not detected AND QR not detected
    robot_stops = (distances > 150) | ((robot_detected.astype(bool)) & (qr_detected.astype(bool)))
    #invert robot_stops
    robot_stops = np.invert(robot_stops)    

    # Create figure with 4 subplots
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    fig.suptitle('Tracking Data Visualization', fontsize=16, fontweight='bold')
    
    # Color scheme
    colors = {
        'distance': '#3B82F6',      # Blue
        'robot_detected': '#22C55E', # Green
        'robot_not_detected': '#EF4444', # Red
        'qr_detected': '#8B5CF6',    # Purple
        'qr_not_detected': '#F97316', # Orange
        'robot_continues': '#22C55E',  # Green - robot can continue
        'robot_stops': '#EF4444'       # Red - robot must stop
    }
    
    # Plot 1: Distance over frames
    ax1 = axes[0]
    ax1.fill_between(frames, 0, distances, alpha=0.3, color=colors['distance'])
    ax1.plot(frames, distances, color=colors['distance'], linewidth=1.5, label='Distance')
    ax1.set_ylabel('Distance (cm)', fontsize=12)
    ax1.set_title('Distance Sensor Readings', fontsize=12, fontweight='medium')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    
    # Add statistics
    avg_dist = np.mean(distances)
    max_dist = np.max(distances)
    min_dist = np.min(distances)
    ax1.axhline(y=avg_dist, color='gray', linestyle='--', alpha=0.5, label=f'Avg: {avg_dist:.1f}cm')
    ax1.text(frames[-1] * 0.98, avg_dist, f'Avg: {avg_dist:.1f}cm', 
             ha='right', va='bottom', fontsize=9, color='gray')
    
    # Plot 2: Robot Detection (YOLO)
    ax2 = axes[1]
    
    # Create colored segments for detection status
    for i in range(len(frames) - 1):
        if robot_detected[i]:
            ax2.axvspan(frames[i], frames[i+1], alpha=0.6, color=colors['robot_detected'])
        else:
            ax2.axvspan(frames[i], frames[i+1], alpha=0.6, color=colors['robot_not_detected'])
    
    ax2.plot(frames, robot_detected, color='black', linewidth=0.5, alpha=0.3)
    ax2.set_ylabel('Robot Detected', fontsize=12)
    ax2.set_ylim(-0.1, 1.1)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['Not Detected', 'Detected'])
    ax2.set_title('YOLO Robot Detection', fontsize=12, fontweight='medium')
    ax2.grid(True, alpha=0.3, axis='x')
    
    # Calculate detection rate
    robot_rate = np.mean(robot_detected) * 100
    ax2.text(frames[-1] * 0.02, 0.5, f'Detection Rate: {robot_rate:.1f}%', 
             ha='left', va='center', fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Plot 3: QR Code Detection
    ax3 = axes[2]
    
    # Create colored segments for detection status
    for i in range(len(frames) - 1):
        if qr_detected[i]:
            ax3.axvspan(frames[i], frames[i+1], alpha=0.6, color=colors['qr_detected'])
        else:
            ax3.axvspan(frames[i], frames[i+1], alpha=0.6, color=colors['qr_not_detected'])
    
    ax3.plot(frames, qr_detected, color='black', linewidth=0.5, alpha=0.3)
    ax3.set_ylabel('QR Detected', fontsize=12)
    ax3.set_ylim(-0.1, 1.1)
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(['Not Detected', 'Detected'])
    ax3.set_title('QR Code Detection', fontsize=12, fontweight='medium')
    ax3.grid(True, alpha=0.3, axis='x')
    
    # Calculate detection rate
    qr_rate = np.mean(qr_detected) * 100
    ax3.text(frames[-1] * 0.02, 0.5, f'Detection Rate: {qr_rate:.1f}%', 
             ha='left', va='center', fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Plot 4: Robot Stops Status
    ax4 = axes[3]
    
    # Create colored segments for robot stops status
    for i in range(len(frames) - 1):
        if robot_stops[i]:
            ax4.axvspan(frames[i], frames[i+1], alpha=0.6, color=colors['robot_stops'])
        else:
            ax4.axvspan(frames[i], frames[i+1], alpha=0.6, color=colors['robot_continues'])
    
    ax4.plot(frames, robot_stops.astype(int), color='black', linewidth=0.5, alpha=0.3)
    ax4.set_ylabel('Robot Status', fontsize=12)
    ax4.set_xlabel('Frame Number', fontsize=12)
    ax4.set_ylim(-0.1, 1.1)
    ax4.set_yticks([0, 1])
    ax4.set_yticklabels(['Continues', 'Stops'])
    ax4.set_title('Robot Stops (dist<150 & no robot & no QR)', fontsize=12, fontweight='medium')
    ax4.grid(True, alpha=0.3, axis='x')
    
    # Calculate robot stops rate
    stops_rate = np.mean(robot_stops) * 100
    ax4.text(frames[-1] * 0.02, 0.5, f'Robot Stops: {stops_rate:.1f}%', 
             ha='left', va='center', fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Add legends
    robot_patches = [
        mpatches.Patch(color=colors['robot_detected'], label='Detected', alpha=0.6),
        mpatches.Patch(color=colors['robot_not_detected'], label='Not Detected', alpha=0.6)
    ]
    ax2.legend(handles=robot_patches, loc='upper right')
    
    qr_patches = [
        mpatches.Patch(color=colors['qr_detected'], label='Detected', alpha=0.6),
        mpatches.Patch(color=colors['qr_not_detected'], label='Not Detected', alpha=0.6)
    ]
    ax3.legend(handles=qr_patches, loc='upper right')
    
    stops_patches = [
        mpatches.Patch(color=colors['robot_continues'], label='Robot Continues', alpha=0.6),
        mpatches.Patch(color=colors['robot_stops'], label='Robot Stops', alpha=0.6)
    ]
    ax4.legend(handles=stops_patches, loc='upper right')
    
    # Add summary statistics text box
    total_frames = len(frames)
    summary_text = (
        f"Summary:\n"
        f"Total Frames: {total_frames}\n"
        f"Distance Range: {min_dist}-{max_dist} cm\n"
        f"Robot Detection: {robot_rate:.1f}%\n"
        f"QR Detection: {qr_rate:.1f}%\n"
        f"Robot Stops: {stops_rate:.1f}%"
    )
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.94)
    
    # Save the figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"Visualization saved to: {output_path}")
    
    # Also display if running interactively
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description='Visualize tracking data from a CSV log file.'
    )
    parser.add_argument(
        'csv_file',
        help='Path to the tracking CSV file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output PNG file path (default: same as input with .png extension)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.csv_file):
        print(f"Error: File not found: {args.csv_file}")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base_name = os.path.splitext(args.csv_file)[0]
        output_path = f"{base_name}.png"
    
    # Load and visualize data
    print(f"Loading tracking data from: {args.csv_file}")
    data = load_tracking_data(args.csv_file)
    print(f"Loaded {len(data['frame'])} frames")
    
    create_visualization(data, output_path)


if __name__ == '__main__':
    main()
