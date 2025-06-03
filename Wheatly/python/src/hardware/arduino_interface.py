# Arduino interface for communicating with Arduino hardware

class ArduinoInterface:
    def __init__(self, port, baud_rate=115200, dry_run=False):
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

    def fetch_servo_config_from_m5(self):
        """Fetch servo config from M5Stack if available, else use defaults."""
        if self.dry_run or not self.serial_connection or not self.serial_connection.is_open:
            print("[DRY RUN or not connected] Using default servo config.")
            return
        import time
        self.serial_connection.reset_input_buffer()
        # Wait and look for SERVO_CONFIG: line (wait up to 60 seconds)
        start = time.time()
        config_line = None
        while time.time() - start < 60.0:  # Wait up to 60 seconds
            if self.serial_connection.in_waiting:
                line = self.serial_connection.readline().decode(errors='ignore').strip()
                if line.startswith('SERVO_CONFIG:'):
                    config_line = line[len('SERVO_CONFIG:'):]
                    break
            time.sleep(0.05)  # Avoid busy loop
        if config_line:
            print(f"[INFO] Got servo config from M5Stack: {config_line}")
            self.update_servo_config_from_string(config_line)
        else:
            print("[WARN] No servo config received from M5Stack after 60s, using defaults.")

    def update_servo_config_from_string(self, config_str):
        """Parse and update servo configs from calibration string."""
        # Format: id,min,max,ping;id,min,max,ping;...
        chunks = config_str.strip().split(';')
        for chunk in chunks:
            if not chunk: continue
            parts = chunk.split(',')
            if len(parts) != 4:
                continue
            try:
                idx = int(parts[0])
                mn = float(parts[1])
                mx = float(parts[2])
                ping = int(parts[3])
                if 0 <= idx < len(self.servo_controller.servos):
                    servo = self.servo_controller.servos[idx]
                    servo.min_angle = mn
                    servo.max_angle = mx
                    # Optionally, you can store ping status if needed
            except Exception as e:
                print(f"[ERROR] Failed to parse servo config chunk '{chunk}': {e}")

    def disconnect(self):
        """Close the connection to the Arduino."""
        if self.dry_run:
            print(f"[DRY RUN] Would disconnect from Arduino on port {self.port}.")
            return
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

    def send_command(self, command):
        """Send a command to the Arduino."""
        if self.dry_run:
            #print(f"Dry run command: {command}")
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

    def read_response(self):
        """Read a response from the Arduino."""
        if self.dry_run:
            print(f"[DRY RUN] Would read response from Arduino.")
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
    def __init__(self, servo_id, initial_angle=0, velocity=5, min_angle=0, max_angle=180, idle_range=10, name=None, interval=2000):
        self.servo_id = servo_id
        self.current_angle = initial_angle
        self.velocity = velocity
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.idle_range = idle_range  # New: maximum idle range in angle
        self.name = name if name is not None else f"Servo {servo_id}"
        self.interval = interval  # New: default animation interval

    def move_to(self, target_angle):
        # Clamp target_angle within allowed range
        clamped_angle = min(max(self.min_angle, target_angle), self.max_angle)
        command = f"MOVE_SERVO;ID={self.servo_id};TARGET={clamped_angle};VELOCITY={self.velocity}"
        self.current_angle = clamped_angle
        #print(f"{self.name} (ID: {self.servo_id}): {command}")

class ServoController:
    def __init__(self, servo_count=7):
        self.servo_count = servo_count
        # Updated servo configurations with names and sensible ranges.
        servo_configs = [
            {'name': 'lens',    "idle_range": 10, 'min_angle': -720, 'max_angle': 720, 'interval': 2000},
            {'name': 'eyelid1', "idle_range": 10, 'min_angle': 30,  'max_angle': 60,  'interval': 2000},
            {'name': 'eyelid2', "idle_range": 10, 'min_angle': 30,  'max_angle': 60,  'interval': 2000},
            {'name': 'eyeX',    "idle_range": 10, 'min_angle': 45,  'max_angle': 135, 'interval': 2000},
            {'name': 'eyeY',    "idle_range": 10, 'min_angle': 40,  'max_angle': 140, 'interval': 2000},
            {'name': 'handle1', "idle_range": 10, 'min_angle': 0,   'max_angle': 170, 'interval': 2000},
            {'name': 'handle2', "idle_range": 10, 'min_angle': 0,   'max_angle': 170, 'interval': 2000}
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
        # and add idle_ranges for each emotion.
        self.emotion_animations = {
            "happy": {
                "velocities": [5] * self.servo_count,
                "target_factors": [0.22, 0.25, 0.22, 0.25, 0.22, 0.25, 0.22],
                "idle_ranges": [100, 10, 10, 10, 10, 10, 10],
                "intervals": [1200, 1200, 1200, 1000, 1000, 15000, 15000],
                "color": (255, 255, 0),        # yellow
            },
            "angry": {
                "velocities": [8] * self.servo_count,
                "target_factors": [0.60, 0.65, 0.60, 0.65, 0.60, 0.65, 0.60],
                "idle_ranges": [5, 5, 5, 5, 5, 5, 5],
                "intervals": [700, 700, 700, 600, 600, 900, 900],
                "color": (255, 0, 0),          # red
            },
            "sad": {
                "velocities": [3] * self.servo_count,
                "target_factors": [0.10, 0.15, 0.10, 0.15, 0.10, 0.15, 0.10],
                "idle_ranges": [15, 15, 15, 15, 15, 15, 15],
                "intervals": [2500, 2500, 2500, 2000, 2000, 3000, 3000],
                "color": (0, 0, 255),          # blue
            },
            "neutral": {
                "velocities": [4] * self.servo_count,
                "target_factors": [0.5] * self.servo_count,
                "idle_ranges": [8, 8, 8, 8, 8, 8, 8],
                "intervals": [2000, 2000, 2000, 2000, 2000, 2000, 2000],
                "color": (255, 255, 255),      # white
            },
            "excited": {
                "velocities": [9] * self.servo_count,
                "target_factors": [0.70] * self.servo_count,
                "idle_ranges": [3, 3, 3, 3, 3, 3, 3],
                "intervals": [500, 500, 500, 400, 400, 600, 600],
                "color": (255, 128, 0),        # orange
            },
            "confused": {
                "velocities": [6, 5, 6, 5, 6, 5, 6],
                "target_factors": [0.45, 0.55, 0.45, 0.55, 0.45, 0.55, 0.45],
                "idle_ranges": [20, 15, 20, 15, 20, 15, 20],
                "intervals": [1800, 1700, 1800, 1700, 1800, 1700, 1800],
                "color": (128, 0, 255),        # purple
            },
            "surprised": {
                "velocities": [10, 9, 10, 9, 10, 9, 10],
                "target_factors": [0.85, 0.80, 0.85, 0.80, 0.85, 0.80, 0.85],
                "idle_ranges": [2, 2, 2, 2, 2, 2, 2],
                "intervals": [300, 300, 300, 250, 250, 350, 350],
                "color": (0, 255, 255),        # cyan
            },
            "curious": {
                "velocities": [7, 6, 7, 6, 7, 6, 7],
                "target_factors": [0.60, 0.55, 0.60, 0.55, 0.60, 0.55, 0.60],
                "idle_ranges": [12, 10, 12, 10, 12, 10, 12],
                "intervals": [1200, 1100, 1200, 1100, 1200, 1100, 1200],
                "color": (0, 255, 128),        # teal
            },
            "bored": {
                "velocities": [2] * self.servo_count,
                "target_factors": [0.35, 0.30, 0.35, 0.30, 0.35, 0.30, 0.35],
                "idle_ranges": [30, 30, 30, 30, 30, 30, 30],
                "intervals": [4000, 4000, 4000, 3500, 3500, 5000, 5000],
                "color": (128, 128, 128),      # gray
            },
            "fearful": {
                "velocities": [10, 8, 10, 8, 10, 8, 10],
                "target_factors": [0.15, 0.80, 0.15, 0.80, 0.15, 0.80, 0.15],
                "idle_ranges": [5, 5, 5, 5, 5, 5, 5],
                "intervals": [400, 400, 400, 350, 350, 500, 500],
                "color": (255, 0, 255),        # magenta
            },
            "hopeful": {
                "velocities": [6, 5, 6, 5, 6, 5, 6],
                "target_factors": [0.65, 0.60, 0.65, 0.60, 0.65, 0.60, 0.65],
                "idle_ranges": [10, 10, 10, 10, 10, 10, 10],
                "intervals": [1500, 1500, 1500, 1400, 1400, 1600, 1600],
                "color": (0, 255, 0),          # green
            },
            "embarrassed": {
                "velocities": [4, 7, 4, 7, 4, 7, 4],
                "target_factors": [0.40, 0.20, 0.40, 0.20, 0.40, 0.20, 0.40],
                "idle_ranges": [18, 8, 18, 8, 18, 8, 18],
                "intervals": [2200, 1000, 2200, 1000, 2200, 1000, 2200],
                "color": (255, 192, 203),      # pink
            },
            "frustrated": {
                "velocities": [9, 8, 9, 8, 9, 8, 9],
                "target_factors": [0.75, 0.20, 0.75, 0.20, 0.75, 0.20, 0.75],
                "idle_ranges": [6, 6, 6, 6, 6, 6, 6],
                "intervals": [800, 800, 800, 700, 700, 900, 900],
                "color": (255, 69, 0),         # orange-red
            },
            "proud": {
                "velocities": [7, 6, 7, 6, 7, 6, 7],
                "target_factors": [0.80, 0.75, 0.80, 0.75, 0.80, 0.75, 0.80],
                "idle_ranges": [8, 8, 8, 8, 8, 8, 8],
                "intervals": [1300, 1300, 1300, 1200, 1200, 1400, 1400],
                "color": (255, 215, 0),        # gold
            },
            "nostalgic": {
                "velocities": [3, 4, 3, 4, 3, 4, 3],
                "target_factors": [0.30, 0.60, 0.30, 0.60, 0.30, 0.60, 0.30],
                "idle_ranges": [20, 15, 20, 15, 20, 15, 20],
                "intervals": [3000, 2500, 3000, 2500, 3000, 2500, 3000],
                "color": (255, 182, 193),      # light pink
            },
            "relieved": {
                "velocities": [5, 4, 5, 4, 5, 4, 5],
                "target_factors": [0.55, 0.60, 0.55, 0.60, 0.55, 0.60, 0.55],
                "idle_ranges": [12, 12, 12, 12, 12, 12, 12],
                "intervals": [1700, 1700, 1700, 1600, 1600, 1800, 1800],
                "color": (173, 216, 230),      # light blue
            },
            "grateful": {
                "velocities": [6, 5, 6, 5, 6, 5, 6],
                "target_factors": [0.60, 0.65, 0.60, 0.65, 0.60, 0.65, 0.60],
                "idle_ranges": [10, 10, 10, 10, 10, 10, 10],
                "intervals": [1400, 1400, 1400, 1300, 1300, 1500, 1500],
                "color": (0, 255, 127),        # spring green
            },
            "shy": {
                "velocities": [3, 5, 3, 5, 3, 5, 3],
                "target_factors": [0.25, 0.20, 0.25, 0.20, 0.25, 0.20, 0.25],
                "idle_ranges": [25, 8, 25, 8, 25, 8, 25],
                "intervals": [2600, 1000, 2600, 1000, 2600, 1000, 2600],
                "color": (238, 130, 238),      # violet
            },
            "disappointed": {
                "velocities": [2, 3, 2, 3, 2, 3, 2],
                "target_factors": [0.15, 0.10, 0.15, 0.10, 0.15, 0.10, 0.15],
                "idle_ranges": [20, 20, 20, 20, 20, 20, 20],
                "intervals": [3500, 3500, 3500, 3000, 3000, 4000, 4000],
                "color": (105, 105, 105),      # dim gray
            },
            "jealous": {
                "velocities": [7, 6, 7, 6, 7, 6, 7],
                "target_factors": [0.40, 0.80, 0.40, 0.80, 0.40, 0.80, 0.40],
                "idle_ranges": [10, 5, 10, 5, 10, 5, 10],
                "intervals": [1200, 800, 1200, 800, 1200, 800, 1200],
                "color": (0, 128, 0),          # dark green
            },
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
        """Adjust each servo based on the desired emotion's standby animation"""
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
        for servo, factor, velocity, idle, interval in zip(self.servos, target_factors, velocities, idle_ranges_config, intervals):
            servo.velocity = velocity
            servo.idle_range = idle
            target_angle = servo.min_angle + factor * (servo.max_angle - servo.min_angle)
            servo.move_to(target_angle)
        return params

    def get_led_color(self, emotion):
        return self.emotion_animations.get(emotion, {}).get("color", (255, 255, 255))

