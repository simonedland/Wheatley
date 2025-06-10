# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\default.ino
This Arduino sketch is designed to facilitate communication between a computer and Dynamixel motors using an Arduino board. The sketch uses the `Dynamixel2Arduino` library to manage communication with the motors via a serial interface.

### Overall Purpose
The primary purpose of this sketch is to act as a bridge, transferring data between a computer (via USB) and Dynamixel motors (via a serial bus). It reads data from the USB port and sends it to the Dynamixel bus, and vice versa.

### Main Functions and Responsibilities

1. **setup()**: 
   - Initializes the built-in LED pin as an output.
   - Begins serial communication on the USB port at a baud rate of 57600.
   - Initializes the Dynamixel bus with the same baud rate.

2. **loop()**: 
   - Continuously calls `dataTransceiver()` to handle data transfer.
   - Checks if the USB baud rate matches the Dynamixel port baud rate and updates if necessary.

3. **dataTransceiver()**:
   - Handles data transfer between the USB port and the Dynamixel bus.
   - Reads available data from the USB and sends it to the Dynamixel bus.
   - Reads available data from the Dynamixel bus and sends it to the USB.
   - Calls `ledStatus()` to update the LED indicator.

4. **ledStatus()**:
   - Toggles the built-in LED to indicate data transmission activity.
   - The LED is turned on for 200 milliseconds whenever data is transferred.

### Key Classes and Libraries

- **Dynamixel2Arduino**: 
  - This library is used to communicate with Dynamixel motors. It provides functions to initialize and manage the serial communication protocol required by these motors.

### Hardware Peripherals Used

- **Serial Ports**: 
  - `Serial1` is used for communication with the Dynamixel motors.
  - `Serial` is used for communication with the computer via USB.

- **LED_BUILTIN**: 
  - Used as a status indicator to show when data is being transmitted.

### Code Structure and Interaction

- The sketch initializes the necessary hardware in the `setup()` function.
- The `loop()` function ensures continuous data transfer and checks for baud rate mismatches.
- The `dataTransceiver()` function is responsible for the core functionality of data transfer, reading from one interface and writing to the other.
- The `ledStatus()` function provides visual feedback on data transmission.

### Notable Algorithms or Logic

- The sketch uses a simple buffer to store data temporarily when transferring between interfaces.
- It ensures that the buffer does not overflow by limiting the length of data read from the Dynamixel bus to the buffer size.

### External Libraries and Dependencies

- **Dynamixel2Arduino**: This library must be installed to compile and run the sketch. It handles the specifics of the Dynamixel communication protocol.

### Configuration and Environment Requirements

- The sketch assumes the use of an Arduino board with a built-in LED and multiple serial ports.
- The Dynamixel motors should be set to communicate at a baud rate of 57600, matching the configuration in the sketch.
- The environment should support the `Dynamixel2Arduino` library, which may require specific hardware like a Dynamixel Shield.

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\OpenRB-150.ino
This Arduino sketch is designed to create a UART bridge between an OpenRB-150 board and a Core-2 device, while also demonstrating multi-servo calibration using Dynamixel servos. The sketch includes functions for handling communication, servo calibration, and a demo sweep.

### Purpose
The sketch's main purpose is to facilitate communication between the OpenRB-150 and Core-2, calibrate multiple servos, and demonstrate their operation. It also provides a mechanism to handle commands from the Core-2 device to control the servos.

### Key Components and Functions

1. **Libraries and Definitions**
   - **Arduino.h**: Core Arduino functions.
   - **Dynamixel2Arduino.h**: For controlling Dynamixel servos.
   - **stdarg.h and stdio.h**: For handling formatted output.
   - **PRINT_HAS_PRINTF**: Ensures printf compatibility across different architectures.

2. **Serial Aliases**
   - **DEBUG_SERIAL**: Alias for `Serial` used for debugging.
   - **LINK_SERIAL**: Alias for `Serial3`, used for communication with Core-2.
   - **DXL_SERIAL**: Alias for `Serial1`, used for Dynamixel communication.

3. **Constants and Configuration**
   - **DXL_DIR_PIN, DXL_PWR_EN, DXL_BAUD, DXL_PROTOCOL**: Configuration for the Dynamixel bus.
   - **LINK_BAUD, HANDSHAKE_TIMEOUT_MS**: Configuration for the UART link.
   - **Calibration Settings**: Constants like `STEP_DEG`, `STALL_THRESHOLD`, etc., for servo calibration.

4. **Helper Functions**
   - **deg2t() and t2deg()**: Convert between degrees and servo ticks.
   - **findLimit()**: Determines the mechanical limit of a servo in a given direction.
   - **printAllServoStatus()**: Prints the status of all servos.
   - **calibrateOrAssignLimits()**: Calibrates servos or assigns manual limits.
   - **sendLimitsToCore2()**: Sends calibration results to Core-2.
   - **handleMoveServoCommand()**: Parses and executes servo movement commands from Core-2.
   - **blinkOnboardLED()**: Blinks the onboard LED a specified number of times.

5. **Setup Function**
   - Initializes serial communication for debugging and the Core-2 link.
   - Powers and initializes the Dynamixel bus.
   - Performs a handshake with Core-2 to determine if it's connected.
   - Probes and calibrates each servo, storing their limits and status.

6. **Loop Function**
   - Continuously checks for commands from Core-2 and executes them.
   - Demonstrates servo movement by sweeping the first servo back and forth.

### Structure and Interaction
- **Setup Phase**: Initializes communication and performs a handshake with Core-2. If successful, it calibrates the servos.
- **Loop Phase**: Listens for commands from Core-2 to move servos and runs a demo sweep of the first servo.

### Notable Algorithms
- **Servo Calibration**: Uses a stepwise approach to find mechanical limits by moving the servo until it stalls, indicating a limit.
- **Communication Protocol**: Uses a simple handshake and command-response mechanism over UART to interact with Core-2.

### External Libraries
- **Dynamixel2Arduino**: Required for controlling Dynamixel servos.

### Environment Requirements
- **Hardware**: OpenRB-150 board, Core-2 device, Dynamixel servos.
- **Connections**: Serial connections for debugging and communication with Core-2 and servos.

This sketch demonstrates a robust approach to integrating servo control and UART communication, suitable for robotics applications requiring precise servo movements and remote command execution.
