import time
import serial
import threading
from collections import deque
from PyQt6.QtCore import QObject, pyqtSignal
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


try:
    import serial_protocol
except ImportError:
    from . import serial_protocol

class DistanceSensor(QObject):
    """
    Handles reading from the specific mmWave radar sensor via serial.
    Implements a sliding window filter (minimum value) as used in the prototyping script.
    """
    distance_updated = pyqtSignal(int)  # Signal carrying the filtered distance in cm
    error_occurred = pyqtSignal(str)

    def __init__(self, port=None, baudrate=None):
        super().__init__()
        # Load from environment variables if not provided
        self.port = port or os.getenv('SERIAL_PORT', '/dev/tty.usbserial-2130')
        self.baudrate = baudrate or int(os.getenv('SERIAL_BAUDRATE', '256000'))
        self.running = False
        self.thread = None
        self.window_size = 5
        self.window_buffer = deque(maxlen=self.window_size)
    
    def start(self):
        """Start the serial reading thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the serial reading thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _read_loop(self):
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=1)
        except serial.SerialException as e:
            self.error_occurred.emit(f"Failed to open serial port {self.port}: {e}")
            self.running = False
            return

        while self.running:
            try:
                # read_until blocks until sequence found or timeout
                serial_port_line = ser.read_until(b'\xF8\xF7\xF6\xF5')
                
                if not serial_port_line:
                    continue

                target_values = serial_protocol.read_basic_mode(serial_port_line)
                
                if target_values is None:
                    continue

                # Unpack values (target_state, moving_dist, moving_energy, static_dist, static_energy, distance)
                # We only interest in the last one: distance
                distance = target_values[5]

                # Filter logic: sliding window minimum
                self.window_buffer.append(distance)
                filtered_val = min(self.window_buffer)

                self.distance_updated.emit(filtered_val)

            except Exception as e:
                # Log error but don't crash thread immediately, maybe retry
                print(f"Error in sensor loop: {e}")
                time.sleep(1)
        
        try:
            ser.close()
        except:
            pass
