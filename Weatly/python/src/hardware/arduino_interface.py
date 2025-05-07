# Arduino interface for communicating with Arduino hardware

class ArduinoInterface:
    def __init__(self, port, baud_rate=9600, dry_run=False):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connection = None
        self.dry_run = dry_run
        # NEW: Initialize servo controller for managing servo animations based on emotions
        self.servo_controller = ServoController()

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
        if self.dry_run:
            print(f"Dry run command: {command}")
        else:
            self.send_command_to_m5(command)

    def send_command_to_m5(self, command):
        # NEW: Send command to M5 stack core2 which controls the Dynamixel board
        print(f"Sending command to M5 stack core2: {command}")

    def read_response(self):
        """Read a response from the Arduino."""
        if self.serial_connection and self.serial_connection.is_open:
            return self.serial_connection.readline().decode().strip()

    def is_connected(self):
        """Check if the connection to the Arduino is established."""
        return self.serial_connection is not None and self.serial_connection.is_open

    def set_animation(self, animation):
        """Set animation on the Arduino hardware."""
        if self.is_connected() or self.dry_run:
            command = f"{animation}"
            self.send_command(command)
            # Optionally, update servo animations for the given emotion
            self.servo_controller.set_emotion(animation)
        else:
            print("Arduino not connected. Cannot set animation.")

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

class Servo:
    def __init__(self, servo_id, initial_angle=0, velocity=5, min_angle=0, max_angle=180, idle_range=10, name=None):
        self.servo_id = servo_id
        self.current_angle = initial_angle
        self.velocity = velocity
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.idle_range = idle_range  # New: maximum idle range in angle
        self.name = name if name is not None else f"Servo {servo_id}"

    def move_to(self, target_angle):
        # Clamp target_angle within allowed range
        clamped_angle = min(max(self.min_angle, target_angle), self.max_angle)
        command = f"MOVE_SERVO;ID={self.servo_id};TARGET={clamped_angle};VELOCITY={self.velocity}"
        self.current_angle = clamped_angle
        print(f"{self.name} (ID: {self.servo_id}): {command}")

class ServoController:
    def __init__(self, servo_count=7):
        self.servo_count = servo_count
        # Updated servo configurations with names and sensible ranges.
        servo_configs = [
            {'name': 'lens',    'min_angle': -720, 'max_angle': 720},  # Updated to 2 rotations
            {'name': 'eyelid1', 'min_angle': 30,  'max_angle': 60},
            {'name': 'eyelid2', 'min_angle': 30,  'max_angle': 60},
            {'name': 'eyeX',    'min_angle': 45,  'max_angle': 135},
            {'name': 'eyeY',    'min_angle': 40,  'max_angle': 140},
            {'name': 'handle1', 'min_angle': 0,   'max_angle': 170},
            {'name': 'handle2', 'min_angle': 0,   'max_angle': 170}
        ]
        self.servos = []
        for i in range(self.servo_count):
            config = servo_configs[i]
            self.servos.append(Servo(
                i,
                idle_range=10,
                min_angle=config['min_angle'],
                max_angle=config['max_angle'],
                name=config['name']
            ))
        # Update emotion animations using target_factors (value between 0 and 1),
        # and add idle_ranges for each emotion.
        self.emotion_animations = {
            "happy": {
                "velocities": [5] * self.servo_count,
                "target_factors": [0.22, 0.25, 0.22, 0.25, 0.22, 0.25, 0.22],
                "idle_ranges": [10, 10, 10, 10, 10, 10, 10],
            },
            "angry": {
                "velocities": [8] * self.servo_count,
                "target_factors": [0.60, 0.65, 0.60, 0.65, 0.60, 0.65, 0.60],
                "idle_ranges": [5, 5, 5, 5, 5, 5, 5],
            },
            "sad": {
                "velocities": [3] * self.servo_count,
                "target_factors": [0.10, 0.15, 0.10, 0.15, 0.10, 0.15, 0.10],
                "idle_ranges": [15, 15, 15, 15, 15, 15, 15],
            },
            "neutral": {
                "velocities": [4] * self.servo_count,
                "target_factors": [0.5] * self.servo_count,
                "idle_ranges": [8, 8, 8, 8, 8, 8, 8],
            },
            "excited": {
                "velocities": [9] * self.servo_count,
                "target_factors": [0.70] * self.servo_count,
                "idle_ranges": [3, 3, 3, 3, 3, 3, 3],
            }
        }

    def print_servo_status(self):
        """Print the status of each servo in a formatted table."""
        print("-" * 80)
        print(f"{'Name':<10} {'ID':<3} {'Angle':<8} {'Velocity':<8} {'Range':<20} {'IdleRange':<10}")
        print("-" * 80)
        for servo in self.servos:
            range_str = f"({servo.min_angle}-{servo.max_angle})"
            print(f"{servo.name:<10} {servo.servo_id:<3} {servo.current_angle:<8.2f} {servo.velocity:<8} {range_str:<20} {servo.idle_range:<10}")
        print("-" * 80)

    def set_emotion(self, emotion):
        """Adjust each servo based on the desired emotion's standby animation."""
        if emotion not in self.emotion_animations:
            print(f"Emotion '{emotion}' not supported. Using 'neutral'.")
            emotion = 'neutral'
        params = self.emotion_animations[emotion]
        velocities = params['velocities']
        target_factors = params['target_factors']
        idle_ranges_config = params['idle_ranges']
        # Compute each servo's target angle relative to its individual range,
        # and update its idle_range accordingly.
        for servo, factor, velocity, idle in zip(self.servos, target_factors, velocities, idle_ranges_config):
            servo.velocity = velocity
            servo.idle_range = idle
            target_angle = servo.min_angle + factor * (servo.max_angle - servo.min_angle)
            servo.move_to(target_angle)
        return params

