# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\M5 stack Core2\M5Stack_Core2.ino
This Arduino sketch is designed to control a 7-servo robotic head using a touch UI on the M5Stack Core-2 device. It communicates with an OpenRB-150 board via UART2 and manages a NeoPixel LED strip for visual feedback. Here's a detailed breakdown:

### Purpose
The sketch provides a user interface to control servos and manage LED feedback, with communication between the M5Stack Core-2 and the OpenRB-150 board. It also includes a demo mode for operation without a successful handshake.

### Key Components and Functions

#### Libraries
- **M5Unified**: For handling the M5Stack Core-2 hardware.
- **HardwareSerial**: For serial communication.
- **Adafruit_NeoPixel**: To control the NeoPixel LED strip.

#### Hardware Peripherals
- **UART2**: Used for communication with the OpenRB-150 board.
- **NeoPixel LED Strip**: Provides visual feedback with 16 LEDs.
- **M5Stack Core-2 Buttons**: Used for user interaction to control servos.

#### Global Variables
- **OpenRB**: Serial object for UART2 communication.
- **leds**: NeoPixel object for controlling the LED strip.
- **servos**: Array of `ServoState` structs to manage servo configurations.
- **selected**: Index of the currently selected servo in the UI.
- **demoMode**: Flag indicating if the system is in demo mode.

#### Functions
- **setup()**: Initializes the hardware, sets up serial communication, and performs a startup LED test.
- **loop()**: Main loop handling communication, UI updates, and servo control.
- **setAll()**: Sets all LEDs to a specified color.
- **blinkScreen()**: Blinks the screen in red as part of the handshake process.
- **processLedCommand()**: Parses and executes LED commands received via serial.
- **enterDemoMode()**: Activates demo mode if no handshake is received within a timeout.
- **drawWindow()**: Draws the UI window showing servo states.
- **sendMoveServoCommand()**: Sends a command to move a specific servo.
- **handleCalibrationData()**: Processes calibration data received from the OpenRB-150.
- **handleUsbCommands()**: Processes commands received via USB serial.
- **handleLink()**: Handles communication with the OpenRB-150 board.

### Code Structure
- **Initialization**: Sets up hardware and performs initial tests.
- **Main Loop**: Continuously checks for serial input, updates the UI, and manages servo movements.
- **LED Management**: Provides functions to control the NeoPixel strip based on received commands.
- **Servo Control**: Manages servo states and sends movement commands based on user input or idle jitter logic.

### Interaction and Logic
- **User Input**: Buttons on the M5Stack Core-2 are used to select and adjust servo positions.
- **Communication**: Commands are sent and received over UART2 and USB serial, with specific handling for LED and servo configuration commands.
- **Idle Jitter**: Implements random idle movements for servos when not actively controlled.

### Notable Algorithms
- **Idle Jitter**: Randomly adjusts servo positions within a defined range to simulate idle behavior.
- **Demo Mode**: Automatically activates if no handshake is received within 10 seconds, allowing limited functionality.

### Configuration and Environment
- **Baud Rate**: Communication with the OpenRB-150 is set at 115200 baud.
- **Pins**: Specific GPIO pins are configured for UART2 and the NeoPixel strip.

This sketch effectively combines hardware control, user interface management, and communication protocols to provide a comprehensive control system for a servo-based robotic head.
