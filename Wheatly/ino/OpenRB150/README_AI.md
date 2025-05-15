# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\default.ino
This Arduino sketch is designed to facilitate communication between a computer and Dynamixel motors using a microcontroller. Here's a breakdown of its purpose, main functions, and hardware usage:

### Overall Purpose
The sketch acts as a bridge to transmit data between a computer (via USB) and Dynamixel motors (via a serial bus). It allows for sending and receiving data packets between these two interfaces.

### Main Functions
1. **setup()**: 
   - Initializes the built-in LED for output.
   - Sets up the USB serial communication at a baud rate of 57600.
   - Initializes the Dynamixel communication with the same baud rate.

2. **loop()**:
   - Continuously calls the `dataTransceiver()` function to handle data transmission.
   - Checks if the USB baud rate matches the Dynamixel port baud rate and updates it if necessary.

3. **dataTransceiver()**:
   - Handles data transfer in both directions:
     - **USB to Dynamixel (DXL)**: Reads available data from the USB and writes it to the Dynamixel bus.
     - **Dynamixel to USB**: Reads available data from the Dynamixel bus, stores it in a buffer, and writes it to the USB.
   - Calls `ledStatus()` to update the LED status after data transfer.

4. **ledStatus()**:
   - Toggles the built-in LED every 200 milliseconds to indicate activity.

### Hardware Peripherals Used
- **Serial Ports**: 
  - `Serial1` (DXL_BUS) is used for communication with the Dynamixel motors.
  - `Serial` (USB) is used for communication with the computer.
  
- **Built-in LED**: 
  - Used as a visual indicator to show data transmission activity. It blinks every 200 milliseconds during data transfer.

This setup allows for real-time communication and control of Dynamixel motors from a computer, using the microcontroller as an intermediary.

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\OpenRB150\test_calibration.ino
This Arduino sketch is designed to calibrate the range of motion for DYNAMIXEL servos that support Protocol 2.0 and Extended-Position mode. The calibration process involves finding the mechanical limits of the servo by moving it until the shaft stalls. If no stop is detected within one turn, it defaults to a ±30° range.

### Overall Purpose
The main goal is to determine the mechanical minimum and maximum positions of the servos, which helps in accurately controlling their motion within safe limits.

### Main Functions

1. **findLimit**: This function moves the servo incrementally in a specified direction until it detects a stall (indicating a mechanical limit) or reaches a maximum sweep angle. It returns the position where the stall is detected or a default value if no stall is found.

2. **calibrate**: This function calibrates a single servo by:
   - Turning off the torque to allow EEPROM writes.
   - Setting the servo to Extended-Position mode.
   - Finding the minimum and maximum positions using `findLimit`.
   - Using default limits if no mechanical stops are detected.
   - Parking the servo at the center of the detected range and turning on an LED to indicate completion.

3. **setup**: Initializes the serial ports, enables power to the servos, and iterates through a list of servo IDs to calibrate each one. It reports any non-responsive servos.

4. **loop**: Remains empty as the calibration is a one-time setup process.

### Hardware Peripherals

- **Serial1**: Used for communication with the DYNAMIXEL servos via a hardware UART interface.
- **Serial**: Used for debugging and outputting information to the USB-C console.
- **BDPIN_DXL_PWR_EN (Pin 31)**: Controls the power to the servos. It must be turned on to enable servo movement.
- **Servos**: The sketch is configured to work with servos specified by their IDs in the `SERVOS` array.

The sketch ensures that the servos are properly calibrated to avoid mechanical damage by detecting their physical limits or using a safe default range if limits are not detected.
