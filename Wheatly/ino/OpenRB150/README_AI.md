# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\default.ino
This Arduino sketch is designed to facilitate communication between a computer and Dynamixel motors using an Arduino board. Here's a breakdown of its purpose, main functions, and hardware usage:

### Purpose
The sketch acts as a bridge, transferring data between a computer (via USB) and Dynamixel motors (via a serial bus). It allows commands and data to be sent and received between the two, enabling control and monitoring of the motors.

### Main Functions
1. **Setup Function:**
   - Initializes the built-in LED as an output.
   - Sets up the USB serial communication at a baud rate of 57600.
   - Initializes the Dynamixel communication using the same baud rate.

2. **Loop Function:**
   - Continuously calls the `dataTransceiver` function to handle data transmission.
   - Checks if the USB baud rate has changed and updates the Dynamixel communication accordingly.

3. **dataTransceiver Function:**
   - Handles data transfer in two directions:
     - **USB to Dynamixel (DXL):** Reads available data from the USB and writes it to the Dynamixel bus.
     - **Dynamixel to USB:** Reads available data from the Dynamixel bus and writes it to the USB.
   - Calls `ledStatus` to update the LED indicator.

4. **ledStatus Function:**
   - Toggles the built-in LED every 200 milliseconds to indicate activity.

### Hardware Peripherals Used
- **Serial Ports:**
  - **USB Serial:** Used for communication with the computer.
  - **DXL_BUS (Serial1):** Used for communication with the Dynamixel motors.
  
- **Built-in LED:**
  - Provides a visual indicator of data transmission activity. It blinks every 200 milliseconds when data is being transferred.

This setup allows for real-time communication and control of Dynamixel motors from a computer, with visual feedback provided by the LED.

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\OpenRB-150.ino
This Arduino sketch is designed to control and calibrate multiple servos using a UART bridge between an OpenRB-150 and a Core-2 microcontroller. It facilitates communication and servo calibration, allowing for precise control and monitoring of servo positions.

### Overall Purpose
The sketch serves as a bridge between the OpenRB-150 and Core-2, enabling servo calibration and control through UART communication. It can automatically calibrate servos or use predefined limits, and it communicates the results back to the Core-2.

### Main Functions
1. **Setup and Initialization:**
   - Initializes serial communication for debugging and linking with Core-2.
   - Powers up and configures the Dynamixel bus for servo control.
   - Performs a handshake with Core-2 to determine if it should proceed with calibration or enter a dry-run mode.

2. **Servo Calibration:**
   - Calibrates each servo by finding mechanical limits unless manual limits are specified.
   - Uses functions like `findLimit` to determine the range of motion for each servo.

3. **Communication:**
   - Sends calibration results and servo status to Core-2 as a CSV string.
   - Listens for and executes servo movement commands from Core-2.

4. **Demo Mode:**
   - Demonstrates servo movement by sweeping the first servo back and forth.
   - Turns on an LED on the servo to indicate the end of the demo.

### Hardware Peripherals Used
- **Dynamixel Servos:**
  - Controlled via a dedicated serial port (`Serial1`).
  - Calibrated for position using feedback from the servos.

- **UART Communication:**
  - Uses `Serial3` for communication with Core-2.
  - Exchanges handshake messages and servo commands.

- **Onboard LED:**
  - Used for visual feedback during the handshake process and demo mode.

- **Power Control:**
  - A pin (`DXL_PWR_EN`) is used to enable power to the servos.

This sketch effectively manages servo calibration and control, providing a robust interface for interacting with multiple servos through a UART bridge.
