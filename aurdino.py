import serial
import time
import sys

class ArduinoUltrasonic:
    def __init__(self, port='COM11', baudrate=9600, timeout=1):
        """
        Initialize Arduino connection for ultrasonic sensor
        
        Args:
            port: COM port (e.g., 'COM11' on Windows)
            baudrate: Communication speed (default: 9600)
            timeout: Serial timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.arduino = None
        self.connected = False
        
    def connect(self):
        """Establish connection with Arduino"""
        try:
            self.arduino = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Wait for Arduino to reset
            # Clear initial buffer
            self.arduino.reset_input_buffer()
            self.connected = True
            print(f"✓ Connected to Arduino on {self.port}")
            return True
        except serial.SerialException as e:
            self.connected = False
            print(f"✗ Error connecting to Arduino: {e}")
            print("\nAvailable COM ports:")
            self.list_ports()
            return False
    
    def list_ports(self):
        """List available COM ports"""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(f"  - {port.device}: {port.description}")
    
    def read_distance(self):
        """Read distance from ultrasonic sensor"""
        if not self.arduino or not self.arduino.is_open:
            return None
        
        try:
            # Clear old buffer to get fresh data
            self.arduino.reset_input_buffer()
            
            # Wait for new data
            time.sleep(0.15)
            
            # Read the latest distance value
            distance = None
            attempts = 0
            
            while attempts < 5 and self.arduino.in_waiting > 0:
                line = self.arduino.readline().decode('utf-8').strip()
                if line and line != "Ultrasonic Sensor Ready":
                    try:
                        distance = float(line)
                        # Got valid reading, break
                        break
                    except ValueError:
                        pass
                attempts += 1
            
            return distance
        except Exception as e:
            print(f"✗ Error reading data: {e}")
            self.connected = False
            return None
    
    def run(self, duration=None):
        """
        Continuously read and display distance measurements
        
        Args:
            duration: How long to run (seconds). None = run indefinitely
        """
        if not self.connect():
            return
        
        print("\n📏 Reading ultrasonic sensor data...")
        print("Press Ctrl+C to stop\n")
        
        start_time = time.time()
        
        try:
            while True:
                distance = self.read_distance()
                
                if distance is not None:
                    print(f"Distance: {distance:.2f} cm", end='\r')
                
                # Check duration
                if duration and (time.time() - start_time) > duration:
                    break
                
                time.sleep(0.1)  # Small delay
                
        except KeyboardInterrupt:
            print("\n\n✓ Stopped by user")
        finally:
            self.close()
    
    def close(self):
        """Close Arduino connection"""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
            self.connected = False
            print("✓ Connection closed")
    
    def is_connected(self):
        """Check if Arduino is connected"""
        return self.connected and self.arduino and self.arduino.is_open


def main():
    # Configuration
    PORT = 'COM3'  # Change this to your Arduino's COM port
    
    # Create Arduino instance
    arduino = ArduinoUltrasonic(port=PORT)
    
    # Run continuously
    arduino.run()


if __name__ == "__main__":
    main()
