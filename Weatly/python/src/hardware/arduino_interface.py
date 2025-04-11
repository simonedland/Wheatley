# Arduino interface for communicating with Arduino hardware

class ArduinoInterface:
    def __init__(self, port, baud_rate=9600):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connection = None

    def connect(self):
        """Establish a connection to the Arduino."""
        import serial
        self.serial_connection = serial.Serial(self.port, self.baud_rate)

    def disconnect(self):
        """Close the connection to the Arduino."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

    def send_command(self, command):
        """Send a command to the Arduino."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.write(command.encode())

    def read_response(self):
        """Read a response from the Arduino."""
        if self.serial_connection and self.serial_connection.is_open:
            return self.serial_connection.readline().decode().strip()

    def is_connected(self):
        """Check if the connection to the Arduino is established."""
        return self.serial_connection is not None and self.serial_connection.is_open

    @staticmethod
    def create(use_raspberry, port='/dev/ttyACM0', baud_rate=9600):
        """Create and initialize an ArduinoInterface if use_raspberry is True."""
        if use_raspberry:
            try:
                iface = ArduinoInterface(port, baud_rate)
                iface.connect()
                return iface
            except Exception as e:
                print(f"Warning: Arduino not connected or could not open port: {e}")
        return None