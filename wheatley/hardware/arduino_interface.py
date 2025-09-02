"""Interface classes for controlling the Arduino-based servo hardware."""


class ArduinoInterface:
    """Interface for communicating with Arduino-based servo hardware and managing servo animations."""

    def __init__(self, port, baud_rate=115200, dry_run=False):
        """Initialize the ArduinoInterface with serial port, baud rate, and dry run mode."""
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connection = None
        self.dry_run = dry_run
        # NEW: Initialize servo controller for managing servo animations based on emotions
        self.servo_controller = ServoController()

    def connect(self):
        """Establish a connection to the Arduino."""
        if self.dry_run:
            print(f"[DRY RUN] Would connect to Arduino on port {self.port} at {self.baud_rate} baud.")
            return
        import serial
        self.serial_connection = serial.Serial(self.port, self.baud_rate, timeout=2)
        # NEW: Try to fetch servo config from M5Stack after connecting
        self.fetch_servo_config_from_m5()

    def fetch_servo_config_from_m5(self, active_timeout: float = 10.0, passive_timeout: float = 60.0):
        """
        Try to obtain the current servo-calibration table from the M5Stack.

        1. Actively send GET_SERVO_CONFIG and wait up to ``active_timeout`` s.
        2. If nothing is received, keep listening passively for up to
           ``passive_timeout`` s (covers the case where calibration hasn’t
           finished yet and the ESP32 will push the table later).
        3. On success the table is parsed via
           ``update_servo_config_from_string()``; otherwise default limits stay.
        """
        if self.dry_run or not self.serial_connection or not self.serial_connection.is_open:
            print("[DRY RUN or not connected] Using default servo config.")
            return

        import time

        # ---- phase 1: active request ---------------------------------------
        self.serial_connection.reset_input_buffer()
        self.serial_connection.write(b"GET_SERVO_CONFIG\n")

        start = time.time()
        config_line = None
        while time.time() - start < active_timeout:
            if self.serial_connection.in_waiting:
                line = self.serial_connection.readline().decode(errors="ignore").strip()
                if line.startswith("SERVO_CONFIG:"):
                    config_line = line[len("SERVO_CONFIG:"):]
                    break
            time.sleep(0.05)

        # ---- phase 2: passive wait (only if active request failed) ---------
        if config_line is None:
            start = time.time()
            while time.time() - start < passive_timeout:
                if self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode(errors="ignore").strip()
                    if line.startswith("SERVO_CONFIG:"):
                        config_line = line[len("SERVO_CONFIG:"):]
                        break
                time.sleep(0.05)

        # ---- final-step: apply or warn -------------------------------------
        if config_line:
            print(f"[INFO] Got servo config from M5Stack: {config_line}")
            self.update_servo_config_from_string(config_line)
        else:
            print(f"[WARN] No servo config received from M5Stack after {active_timeout + passive_timeout:.0f}s, using defaults.")

    def update_servo_config_from_string(self, config_str):
        """Parse and update servo configs from calibration string."""
        chunks = config_str.strip().split(';')
        for chunk in chunks:
            if not chunk:
                continue
            parts = chunk.split(',')
            if len(parts) != 4:
                continue
            try:
                idx = int(parts[0])
                mn = float(parts[1])
                mx = float(parts[2])
                if 0 <= idx < len(self.servo_controller.servos):
                    servo = self.servo_controller.servos[idx]
                    servo.min_angle = mn
                    servo.max_angle = mx
            except Exception as e:
                print(f"[ERROR] Failed to parse servo config chunk '{chunk}': {e}")

    def send_command(self, command):
        """Send a command to the Arduino."""
        if self.dry_run:
            # print(f"Dry run command: {command}")
            return
        self.send_command_to_m5(command)

    def send_command_to_m5(self, command):
        """Send a command to the Arduino via serial."""
        if self.dry_run:
            print(f"[DRY RUN] Would send command to Arduino: {command}")
            return None
        if self.serial_connection and self.serial_connection.is_open:
            print(f"Sending command to Arduino: {command.strip()}")
            self.serial_connection.write(command.encode())
            response = self.read_response()
            print(f"Arduino response: {response}")
        else:
            print("Arduino not connected. Cannot send command.")
        return response

    def set_mic_led_color(self, r, g, b):
        """Set only the microphone status NeoPixel to the given color, scaling brightness by dividing by 5."""
        r = int(int(r) / 5)
        g = int(int(g) / 5)
        b = int(int(b) / 5)
        led_command = f"SET_MIC_LED;R={r};G={g};B={b}\n"
        self.send_command(led_command)

    def read_response(self):
        """Read a response from the Arduino."""
        if self.dry_run:
            print("[DRY RUN] Would read response from Arduino.")
            return None
        if self.serial_connection and self.serial_connection.is_open:
            return self.serial_connection.readline().decode().strip()

    def is_connected(self):
        """Check if the connection to the Arduino is established."""
        if self.dry_run:
            return False
        return self.serial_connection is not None and self.serial_connection.is_open

    def set_animation(self, animation):
        """Set servo configs for the given animation on the Arduino hardware. Uses per-animation intervals from emotion_animations. Also sets LED color."""
        if self.is_connected() or self.dry_run:
            params = self.servo_controller.set_emotion(animation)
            velocities = params['velocities']
            target_factors = params['target_factors']
            idle_ranges = params['idle_ranges']
            intervals = params['intervals']
            # Set each servo's config (target, velocity, idle_range)
            for i, servo in enumerate(self.servo_controller.servos):
                target_angle = servo.min_angle + target_factors[i] * (servo.max_angle - servo.min_angle)
                servo.velocity = velocities[i]
                servo.idle_range = idle_ranges[i]
                servo.interval = intervals[i]
                servo.current_angle = int(target_angle)
            self.send_servo_config()  # Send all configs in one command
            # Set LED color for this emotion
            r, g, b = self.servo_controller.get_led_color(animation)
            led_command = f"SET_LED;R={r};G={g};B={b}\n"
            self.send_command(led_command)
        else:
            print("Arduino not connected. Cannot set animation.")

    @staticmethod
    def create(use_raspberry, port='COM7', baud_rate=9600):
        """Create and initialize an ArduinoInterface if use_raspberry is True."""
        if use_raspberry:
            try:
                iface = ArduinoInterface(port, baud_rate)
                iface.connect()
                return iface
            except Exception as e:
                print(f"Warning: Arduino not connected or could not open port: {e}")
        return None

    def send_servo_config(self):
        """Send all servo configs to the M5Stack using SET_SERVO_CONFIG:id,target,vel,idle_range,interval;..."""
        config_chunks = []
        for servo in self.servo_controller.servos:
            # Compose config: id,target,velocity,idle_range,interval
            chunk = f"{servo.servo_id},{servo.current_angle},{servo.velocity},{servo.idle_range},{servo.interval}"
            config_chunks.append(chunk)
        config_str = ";".join(config_chunks)
        command = f"SET_SERVO_CONFIG:{config_str}\n"
        self.send_command(command)


class Servo:
    """Representation of a single servo motor."""

    def __init__(
        self,
        servo_id,
        initial_angle=0,
        velocity=5,
        min_angle=0,
        max_angle=180,
        idle_range=10,
        name=None,
        interval=2000,
    ):
        """Initialize a Servo with its parameters and defaults."""
        self.servo_id = servo_id
        self.current_angle = initial_angle
        self.velocity = velocity
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.idle_range = idle_range  # New: maximum idle range in angle
        self.name = name if name is not None else f"Servo {servo_id}"
        self.interval = interval  # New: default animation interval

    def move_to(self, target_angle):
        """Move servo to ``target_angle`` respecting configured limits."""
        # Clamp target_angle within allowed range
        clamped_angle = min(max(self.min_angle, target_angle), self.max_angle)
        self.current_angle = clamped_angle


class ServoController:
    """Manage servo configurations and emotion animations."""

    def __init__(self, servo_count=10):
        """Initialize the ServoController with a given number of servos and their configurations."""
        self.servo_count = servo_count
        # Updated servo configurations with names and sensible ranges.
        # New servos: eyeX2, eyeY2 mirror eyeX/eyeY; eyeZ is a twist axis similar to handles.
        servo_configs = [
            {'name': 'lens', 'idle_range': 700, 'min_angle': 0, 'max_angle': 0, 'interval': 2000},
            {'name': 'eyelid1', 'idle_range': 40, 'min_angle': 180, 'max_angle': 220, 'interval': 2000},
            {'name': 'eyelid2', 'idle_range': 40, 'min_angle': 140, 'max_angle': 180, 'interval': 2000},
            {'name': 'eyeX', 'idle_range': 90, 'min_angle': 130, 'max_angle': 220, 'interval': 2000},
            {'name': 'eyeY', 'idle_range': 80, 'min_angle': 140, 'max_angle': 210, 'interval': 2000},
            {'name': 'handle1', 'idle_range': 10, 'min_angle': -60, 'max_angle': 60, 'interval': 2000},
            {'name': 'handle2', 'idle_range': 10, 'min_angle': -60, 'max_angle': 60, 'interval': 2000},
            # Test constraint: new axes locked to 180° ±5° with small idle
            {'name': 'eyeX2', 'idle_range': 5, 'min_angle': 150, 'max_angle': 180, 'interval': 2000},
            {'name': 'eyeY2', 'idle_range': 5, 'min_angle': 130, 'max_angle': 200, 'interval': 2000},
            {'name': 'eyeZ', 'idle_range': 5, 'min_angle': 140, 'max_angle': 220, 'interval': 2000},
        ]
        self.servos = []
        for i in range(self.servo_count):
            config = servo_configs[i]
            self.servos.append(Servo(
                i,
                idle_range=config['idle_range'],
                min_angle=config['min_angle'],
                max_angle=config['max_angle'],
                name=config['name'],
                interval=config['interval']
            ))
        # Update emotion animations using target_factors (value between 0 and 1),
        # and add idle_ranges for each emotion. Start from 7-servo presets,
        # then expand to servo_count by mirroring eyeX->eyeX2, eyeY->eyeY2,
        # and handle1->eyeZ as sensible defaults.
        self.emotion_animations = {
            "angry": {
                "velocities": [5, 5, 5, 5, 5, 5, 5, 2, 2, 2],
                "target_factors": [0.185, 0.075, 0.925, 0.489, 0.486, 0.5, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 2, 2, 40, 3, 10, 10, 5, 5, 5],
                "intervals": [2000, 5000, 5000, 5000, 5000, 2000, 2000, 2000, 2000, 2000],
                "color": [255, 0, 0]
            },
            "happy": {
                "velocities": [10, 1, 1, 10, 1, 5, 5, 2, 2, 2],
                "target_factors": [0.865, 0.15, 0.0, 0.489, 0.043, 1.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 1, 40, 3, 10, 10, 5, 5, 5],
                "intervals": [2000, 1000, 5000, 3000, 5000, 2000, 2000, 2000, 2000, 2000],
                "color": [0, 255, 0]
            },
            "sad": {
                "velocities": [1, 1, 1, 1, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.927, 0.4, 0.65, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [50, 10, 10, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 5000, 5000, 5000, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [0, 0, 255]
            },
            "neutral": {
                "velocities": [1, 1, 1, 1, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.501, 0.75, 0.225, 0.489, 0.457, 1.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [400, 5, 5, 30, 30, 10, 10, 5, 5, 5],
                "intervals": [20000, 20000, 20000, 20000, 20000, 20000, 20000, 2000, 2000, 2000],
                "color": [255, 255, 255]
            },
            "excited": {
                "velocities": [20, 1, 1, 10, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.471, 0.475, 0.075, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [200, 5, 3, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 500, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [255, 128, 64]
            },
            "confused": {
                "velocities": [20, 1, 1, 10, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.471, 0.175, 0.5, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [200, 5, 5, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 500, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [128, 255, 255]
            },
            "surprised": {
                "velocities": [20, 5, 5, 10, 10, 1, 1, 2, 2, 2],
                "target_factors": [1.0, 1.0, 0.0, 0.489, 0.486, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [50, 1, 1, 10, 10, 10, 10, 5, 5, 5],
                "intervals": [500, 1000, 1000, 500, 500, 10500, 10600, 2000, 2000, 2000],
                "color": [255, 255, 0]
            },
            "curious": {
                "velocities": [10, 1, 1, 5, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.865, 0.375, 0.25, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 5, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 2000, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [255, 128, 0]
            },
            "bored": {
                "velocities": [5, 1, 1, 1, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.865, 1.0, 1.0, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 5, 20, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 2000, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [128, 0, 255]
            },
            "fearful": {
                "velocities": [10, 3, 3, 10, 10, 1, 1, 2, 2, 2],
                "target_factors": [0.854, 1.0, 0.0, 0.5, 0.486, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 2, 2, 40, 30, 10, 10, 5, 5, 5],
                "intervals": [1000, 1000, 1000, 1000, 1000, 10500, 10600, 2000, 2000, 2000],
                "color": [255, 0, 0]
            },
            "hopeful": {
                "velocities": [20, 1, 1, 10, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.47, 0.475, 0.075, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [200, 5, 3, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 500, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [128, 128, 255]
            },
            "embarrassed": {
                "velocities": [5, 1, 1, 5, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.491, 1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [300, 5, 3, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 1000, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [255, 0, 255]
            },
            "frustrated": {
                "velocities": [5, 1, 1, 5, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.032, 0.25, 0.75, 0.5, 0.5, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [10, 5, 3, 10, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 1000, 1000, 1000, 1000, 2000, 2000, 2000],
                "color": [255, 0, 0]
            },
            "proud": {
                "velocities": [10, 1, 1, 10, 1, 5, 5, 2, 2, 2],
                "target_factors": [0.865, 0.15, 0.0, 0.489, 0.043, 1.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 1, 40, 3, 10, 10, 5, 5, 5],
                "intervals": [2000, 1000, 5000, 3000, 5000, 2000, 2000, 2000, 2000, 2000],
                "color": [255, 255, 0]
            },
            "nostalgic": {
                "velocities": [10, 1, 1, 5, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.865, 0.375, 0.25, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 5, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 2000, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [0, 0, 64]
            },
            "relieved": {
                "velocities": [10, 1, 1, 10, 1, 5, 5, 2, 2, 2],
                "target_factors": [0.865, 0.15, 0.0, 0.489, 0.043, 1.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 1, 40, 3, 10, 10, 5, 5, 5],
                "intervals": [2000, 1000, 5000, 3000, 5000, 2000, 2000, 2000, 2000, 2000],
                "color": [0, 0, 160]
            },
            "grateful": {
                "velocities": [10, 1, 1, 10, 1, 5, 5, 2, 2, 2],
                "target_factors": [0.865, 0.15, 0.0, 0.489, 0.043, 1.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 1, 40, 3, 10, 10, 5, 5, 5],
                "intervals": [2000, 1000, 5000, 3000, 5000, 2000, 2000, 2000, 2000, 2000],
                "color": [0, 255, 255]
            },
            "shy": {
                "velocities": [5, 1, 1, 5, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.49, 1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [300, 5, 3, 50, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 1000, 10400, 10500, 10600, 2000, 2000, 2000],
                "color": [255, 0, 255]
            },
            "disappointed": {
                "velocities": [2, 1, 1, 1, 1, 1, 1, 2, 2, 2],
                "target_factors": [0.45, 1.0, 0.8, 0.5, 0.529, 0.0, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 5, 5, 20, 10, 10, 10, 5, 5, 5],
                "intervals": [5000, 1000, 1000, 2000, 1000, 1000, 1000, 2000, 2000, 2000],
                "color": [255, 255, 0]
            },
            "jealous": {
                "velocities": [2, 10, 10, 5, 5, 5, 5, 2, 2, 2],
                "target_factors": [0.16, 0.325, 0.625, 0.489, 0.486, 0.5, 0.0, 0.5, 0.5, 0.5],
                "idle_ranges": [100, 2, 2, 40, 3, 10, 10, 5, 5, 5],
                "intervals": [2000, 5000, 5000, 5000, 5000, 2000, 2000, 2000, 2000, 2000],
                "color": [128, 0, 255]
            }
        }

    def print_servo_status(self):
        """Print the status of each servo in a formatted table with improved alignment."""
        print("-" * 80)
        print(f"{'Name':<10} {'ID':<3} {'Angle':>8} {'Velocity':>9} {'Range':>18} {'IdleRange':>12} {'Frequency':>12}")
        print("-" * 80)
        for servo in self.servos:
            range_str = f"({servo.min_angle}-{servo.max_angle})"
            print(f"{servo.name:<10} {servo.servo_id:<3} {servo.current_angle:>8.2f} {servo.velocity:>9} {range_str:>18} {servo.idle_range:>12} {servo.interval:>12}")
        print("-" * 80)

    def set_emotion(self, emotion):
        """Adjust each servo based on the desired emotion's standby animation."""
        if emotion not in self.emotion_animations:
            print(f"Emotion '{emotion}' not supported. Using 'neutral'.")
            emotion = 'neutral'
        print(f"Setting emotion: {emotion}")
        params = self.emotion_animations[emotion]
        velocities = params['velocities']
        target_factors = params['target_factors']
        idle_ranges_config = params['idle_ranges']
        intervals = params['intervals']
        # Compute each servo's target angle relative to its individual range,
        # and update its idle_range accordingly.
        for servo, factor, velocity, idle, _interval in zip(self.servos, target_factors, velocities, idle_ranges_config, intervals):
            servo.velocity = velocity
            servo.idle_range = idle
            target_angle = servo.min_angle + factor * (servo.max_angle - servo.min_angle)
            servo.move_to(target_angle)
        return params

    def get_led_color(self, emotion):
        """Get the LED color tuple (r, g, b) for the given emotion, scaled for brightness."""
        color = self.emotion_animations.get(emotion, {}).get("color", (255, 255, 255))
        # Scale each channel down by dividing by 5 (e.g., 255 -> 51, 128 -> 25, etc.)
        if isinstance(color, (list, tuple)) and len(color) == 3:
            r = int(int(color[0]) / 5)
            g = int(int(color[1]) / 5)
            b = int(int(color[2]) / 5)
            return (r, g, b)
        return (51, 51, 51)
