# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\default.ino
This Arduino sketch is designed to facilitate communication between a computer and a Dynamixel device using a microcontroller. It acts as a bridge, transferring data between the USB serial interface and the Dynamixel bus.

### Overall Purpose
The sketch enables data transmission between a computer connected via USB and a Dynamixel device connected via a serial bus. It also provides visual feedback using the built-in LED to indicate data transmission activity.

### Main Functions and Responsibilities

1. **Setup Function (`setup`)**:
   - Initializes the built-in LED for output.
   - Sets up the USB serial communication at a baud rate of 57600.
   - Initializes the Dynamixel bus with the same baud rate to ensure compatibility.
   - Configures the protocol version for communication with the Dynamixel device.

2. **Loop Function (`loop`)**:
   - Continuously calls the `dataTransceiver` function to handle data transmission.
   - Checks if the USB baud rate matches the Dynamixel port baud rate and reinitializes if necessary.

3. **Data Transceiver Function (`dataTransceiver`)**:
   - Handles data transfer in both directions:
     - **USB to Dynamixel (DXL)**: Reads available data from the USB and writes it to the Dynamixel bus.
     - **Dynamixel to USB**: Reads available data from the Dynamixel bus and writes it to the USB.
   - Calls `ledStatus` to update the LED based on data transmission activity.

4. **LED Status Function (`ledStatus`)**:
   - Toggles the built-in LED to indicate data transmission.
   - Uses a timestamp to control the LED's on/off state, updating every 200 milliseconds.

### Hardware Peripherals Used
- **Built-in LED**: Provides visual feedback for data transmission activity.
- **Serial Interfaces**:
  - **USB Serial**: For communication with a computer.
  - **Dynamixel Serial (DXL_BUS)**: For communication with the Dynamixel device.

### Key Classes and Libraries
- **Dynamixel2Arduino**: This library facilitates communication with Dynamixel devices. It provides methods for setting up and managing the serial communication protocol specific to Dynamixel.

### Structure and Interaction
- The sketch initializes the necessary hardware and continuously loops to manage data transfer.
- The `dataTransceiver` function acts as the core, managing data flow between the USB and Dynamixel bus.
- The `ledStatus` function provides feedback by controlling the LED based on data activity.

### Notable Algorithms and Logic
- The sketch uses a simple buffer mechanism to handle data transfer, ensuring that data is read and written efficiently.
- The LED status logic uses a time-based toggle to indicate ongoing data transmission.

### External Libraries and Dependencies
- **Dynamixel2Arduino**: Required for handling Dynamixel communication. Ensure this library is installed in the Arduino IDE.

### Configuration and Environment Requirements
- The baud rate for both USB and Dynamixel communication must be set to 57600.
- The protocol version must match the Dynamixel device's protocol version.
- The sketch assumes the use of a microcontroller compatible with the Dynamixel2Arduino library and with a built-in LED.

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\OpenRB-150.ino
This Arduino sketch is designed to operate as a UART bridge and perform multi-servo calibration using the Dynamixel2Arduino library. It facilitates communication between an OpenRB-150 board and a Core-2 device, while also calibrating and controlling multiple servos.

### Overall Purpose
The sketch serves two main purposes:
1. **UART Bridge**: Establishes a communication link between the OpenRB-150 and a Core-2 device using UART.
2. **Servo Calibration and Control**: Calibrates multiple servos, sets their limits, and allows for control commands to be sent from the Core-2 device.

### Main Functions and Responsibilities

1. **UART Communication**:
   - **Serial Setup**: Initializes serial communication on different ports for debugging (`Serial`), linking to Core-2 (`Serial3`), and controlling servos (`Serial1`).
   - **Handshake**: Performs a 10-second handshake with the Core-2 device to ensure communication is established.

2. **Servo Calibration**:
   - **Calibration**: Automatically or manually sets limits for each servo based on predefined settings or by finding mechanical limits.
   - **Status Reporting**: Sends calibration results and servo status back to the Core-2 device.

3. **Command Handling**:
   - **MOVE_SERVO Command**: Parses and executes commands to move servos to specified positions at given velocities.

4. **Demo Functionality**:
   - **Servo Sweep**: Demonstrates servo movement by sweeping the first servo back and forth.

### Key Classes and Functions

- **Dynamixel2Arduino**: A library used to interface with Dynamixel servos.
  - **dxl.begin()**: Initializes the Dynamixel bus.
  - **dxl.ping()**: Checks if a servo is connected.
  - **dxl.setGoalPosition()**: Moves a servo to a specified position.
  - **dxl.getPresentPosition()**: Retrieves the current position of a servo.
  - **dxl.torqueOn() / dxl.torqueOff()**: Enables or disables torque for a servo.

- **Helper Functions**:
  - **findLimit()**: Determines the mechanical limit of a servo in a specified direction.
  - **printAllServoStatus()**: Prints the status of all servos to the debug serial.
  - **calibrateOrAssignLimits()**: Calibrates or assigns manual limits to a servo.
  - **sendLimitsToCore2()**: Sends calibration data to the Core-2 device.
  - **handleMoveServoCommand()**: Parses and executes MOVE_SERVO commands.
  - **blinkOnboardLED()**: Blinks the onboard LED a specified number of times.

### Structure and Interaction

- **Setup Function**: Initializes serial communications, performs a handshake with the Core-2 device, and calibrates servos.
- **Loop Function**: Continuously checks for incoming commands from Core-2 and executes a demo sweep of the first servo.

### Notable Algorithms and Logic

- **Handshake Logic**: Uses a timeout mechanism to establish communication with the Core-2 device.
- **Calibration Logic**: Uses a combination of automatic and manual methods to set servo limits, employing a stall detection threshold to identify mechanical limits.

### External Libraries and Dependencies

- **Dynamixel2Arduino**: Required for interfacing with Dynamixel servos.
- **Arduino Core**: Provides core functionalities for serial communication and I/O operations.

### Configuration and Environment Requirements

- **Hardware**: Requires an OpenRB-150 board, Core-2 device, and Dynamixel servos.
- **Serial Ports**: Uses `Serial` for debugging, `Serial1` for servo communication, and `Serial3` for Core-2 communication.
- **Baud Rates**: Configured for 57600 bps for Dynamixel and 115200 bps for Core-2 communication.

This sketch is a comprehensive solution for bridging UART communication and managing multiple servos with calibration capabilities.
