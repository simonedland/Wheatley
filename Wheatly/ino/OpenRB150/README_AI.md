# AI Summary

### C:\GIT\eatly\Wheatley\Weatly\ino\OpenRB150\default.ino
This Arduino sketch is designed to facilitate communication between a computer and a Dynamixel servo motor using a microcontroller. Here's a breakdown of its purpose, main functions, and hardware usage:

### Overall Purpose
The sketch acts as a bridge to transmit data between a computer (via USB) and a Dynamixel servo motor (via a serial bus). It ensures that data sent from the computer is forwarded to the servo and vice versa.

### Main Functions

1. **Setup Function:**
   - Initializes the built-in LED as an output.
   - Sets up the USB serial communication at a baud rate of 57600.
   - Initializes the serial communication for the Dynamixel bus to match the USB baud rate.

2. **Loop Function:**
   - Continuously calls `dataTransceiver()` to handle data transmission.
   - Checks if the USB baud rate matches the Dynamixel bus baud rate and updates if necessary.

3. **dataTransceiver Function:**
   - Handles data transfer in both directions:
     - **USB to Dynamixel (DXL):** Reads available data from the USB and writes it to the Dynamixel bus.
     - **Dynamixel to USB:** Reads available data from the Dynamixel bus, stores it in a buffer, and writes it back to the USB.
   - Calls `ledStatus()` to update the LED based on data activity.

4. **ledStatus Function:**
   - Toggles the built-in LED to indicate data transmission activity. The LED turns on for 200 milliseconds when data is being transmitted.

### Hardware Peripherals Used

- **Serial Communication:**
  - **USB Serial (Serial):** Used for communication with a computer.
  - **Dynamixel Bus (Serial1):** Used for communication with the Dynamixel servo motor.

- **Built-in LED:**
  - Used as a visual indicator of data transmission activity. It blinks when data is being sent or received.

This setup allows for real-time data exchange between a computer and a Dynamixel motor, with visual feedback provided by the LED.

### C:\GIT\eatly\Wheatley\Weatly\ino\OpenRB150\test_calibration.ino
This Arduino sketch is designed to calibrate the range of motion for DYNAMIXEL servos that support Protocol 2.0 and Extended-Position mode. The goal is to find the mechanical limits of the servo by moving it until it stalls, indicating a physical stop. If no stop is detected within one full rotation, it defaults to a ±30° range.

### Main Functions:

1. **Setup Function:**
   - Initializes serial communication for debugging and servo control.
   - Enables power to the servos by setting a specific pin high.
   - Iterates through a list of servo IDs to calibrate each one.

2. **Calibrate Function:**
   - Turns off the servo torque to allow EEPROM writes.
   - Sets the servo to Extended-Position mode.
   - Finds the minimum and maximum mechanical limits by moving the servo in both directions until it stalls.
   - If no stall is detected, it defaults to a ±30° range.
   - Centers the servo and turns on its LED to indicate completion.

3. **FindLimit Function:**
   - Moves the servo in small increments (creeping) to detect when it stalls.
   - Returns the position where the stall is detected or a fallback value if no stall is found.

### Hardware Peripherals Used:

- **DYNAMIXEL Servos:** Controlled via a half-duplex UART connection. The sketch communicates with the servos to set positions and read current positions.
- **Serial Communication:** Used for debugging via USB-C and for controlling the servos.
- **Power Control Pin (BDPIN_DXL_PWR_EN):** A pin that enables or disables power to the servos. It must be set high to allow the servos to move.

Overall, this sketch automates the calibration of servo limits, ensuring they operate within safe mechanical boundaries.
