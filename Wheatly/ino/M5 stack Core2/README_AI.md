# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\M5 stack Core2\M5Stack_Core2.ino
This Arduino sketch is designed to control a 7-servo robotic head using an ESP32 microcontroller. It communicates with an OpenRB-150 board via UART2 and provides a touch-based user interface on an M5Stack Core2 device. The sketch also manages NeoPixel LEDs for visual feedback.

### Purpose
The sketch's primary purpose is to control and monitor a set of servos, displaying their states on a touch interface and allowing user interaction to adjust servo angles. It also handles communication with an OpenRB-150 board for servo calibration and status updates.

### Main Components and Functions

1. **HardwareSerial OpenRB(2):** 
   - Initializes UART2 for communication with the OpenRB-150 board.
   - Uses GPIO pins 13 (RX) and 14 (TX) for data transmission.

2. **ServoState Structure:**
   - Holds the configuration and state for each servo, including current angle, velocity, and idle behavior parameters.

3. **Servo Management:**
   - `totalServos` and `activeServos` define the number of servos and those that are controllable.
   - `servos[]` array stores the state for each servo.
   - `SERVO_NAMES[]` provides labels for the UI.

4. **UI Layout:**
   - Manages the display of servo information using parameters like `lineHeight`, `yOffset`, and `visibleRows`.
   - Functions like `drawLine()`, `drawWindow()`, and `drawSingle()` handle the drawing of the UI.

5. **Runtime Flags:**
   - `dryRun`: Prevents servo commands until a successful handshake and calibration.
   - `servoPingResult[]`: Tracks the status of each servo.
   - `calibrationReceived`: Ensures UI interaction only after calibration data is received.

6. **Communication:**
   - `handleLink()`: Manages incoming messages from the OpenRB-150, handling handshakes, calibration data, and other commands.
   - `sendMoveServoCommand()`: Sends commands to move servos to specified angles.

7. **LED Management:**
   - Uses the Adafruit_NeoPixel library to control a strip of NeoPixel LEDs connected to GPIO pin 21.
   - Provides visual feedback for events like handshakes.

8. **Setup and Loop:**
   - `setup()`: Initializes the M5Stack, UART, and LEDs, and attempts an initial handshake.
   - `loop()`: Continuously updates the UI, processes user input, handles idle animations, and manages communication with the OpenRB-150.

### External Libraries
- **M5Unified:** For managing the M5Stack Core2 hardware.
- **HardwareSerial:** For serial communication.
- **Adafruit_NeoPixel:** For controlling the NeoPixel LED strip.

### Key Logic and Algorithms
- **Idle Animation:** Randomly moves servos within a defined range when idle, ensuring continuous motion.
- **UI Interaction:** Allows users to select and adjust servo angles using buttons on the M5Stack.
- **Handshake and Calibration:** Ensures the system is ready for operation by waiting for a successful handshake and calibration data from the OpenRB-150.

### Configuration and Environment
- Requires an ESP32-based M5Stack Core2.
- Connected to an OpenRB-150 board via UART2.
- Uses a NeoPixel LED strip for visual feedback.
- The sketch assumes a specific hardware setup with defined GPIO pins for communication and LED control.

This sketch provides a comprehensive interface for controlling servos, with robust communication and user interaction capabilities, suitable for applications requiring precise servo management and feedback.
