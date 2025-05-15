# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\python\src\hardware\arduino_interface.py
The Python code defines a system for interfacing with Arduino hardware, specifically focusing on controlling servos to perform animations based on different emotions. 

### Key Components:

1. **ArduinoInterface Class**:
   - Manages the connection to an Arduino device via a specified port and baud rate.
   - Supports a "dry run" mode for testing without actual hardware.
   - Provides methods to connect, disconnect, send commands, and check connection status.
   - Integrates a `ServoController` to manage servo animations.

2. **Servo Class**:
   - Represents individual servos with properties like ID, angle, velocity, range, and animation interval.
   - Includes a method to move the servo to a specified angle within its range.

3. **ServoController Class**:
   - Manages multiple servos and their configurations.
   - Defines animations for various emotions (e.g., happy, angry, sad) with specific parameters like velocities, target factors, idle ranges, and intervals.
   - Provides methods to print servo statuses and set emotions, adjusting servos accordingly.

### Purpose and Logic:
- The system is designed to control servos connected to an Arduino, allowing them to perform animations that correspond to different emotional states.
- The `ArduinoInterface` handles communication with the Arduino, while the `ServoController` manages the logic for animating servos based on predefined emotional configurations.
- The code supports testing without hardware through a dry run mode, ensuring flexibility in development and debugging.
