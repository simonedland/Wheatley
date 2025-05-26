# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\M5 stack Core2\M5Stack_Core2.ino
This Arduino sketch is designed to control a 7-servo robotic head using a touch interface on an M5Stack Core2 device. It communicates with an OpenRB-150 controller via UART2 to manage servo movements.

### Overall Purpose
The sketch provides a user interface to control and monitor the state of seven servos in a robotic head. It handles communication with the OpenRB-150 controller to send commands and receive calibration data.

### Main Functions
1. **Setup and Initialization:**
   - Initializes the M5Stack Core2 and sets up UART2 for communication with the OpenRB-150.
   - Draws the initial user interface on the screen.
   - Sends a proactive handshake message ("ESP32") to the OpenRB-150.

2. **Communication Handling:**
   - Listens for messages from the OpenRB-150. Handles "HELLO" messages by responding and blinking the screen.
   - Processes calibration data to update servo limits and availability.
   - Handles other commands by printing them for debugging.

3. **User Interface:**
   - Displays a scrolling list of servos, showing their current angle, velocity, and idle range.
   - Highlights the selected servo and shows disabled servos in grey.
   - Allows interaction through buttons to adjust servo angles.

4. **Servo Control:**
   - Sends commands to move servos based on user input or idle animations.
   - Implements idle animations by randomly adjusting servo angles within specified limits when the system is idle.

5. **Button Handling:**
   - Uses buttons A, B, and C on the M5Stack to decrease, increase, or switch the selected servo, respectively.

### Hardware Peripherals Used
- **M5Stack Core2:**
  - Acts as the main interface device, providing a touchscreen and buttons for user interaction.
  - Displays the servo control interface.

- **UART2:**
  - Used for communication with the OpenRB-150 controller, sending servo commands and receiving calibration data.
  - Configured with specific RX and TX pins and a baud rate of 115200.

This setup allows for interactive control of the robotic head's servos, providing feedback and ensuring safe operation through calibration and status checks.
