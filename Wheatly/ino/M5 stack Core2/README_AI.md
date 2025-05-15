# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\M5 stack Core2\test.ino
This Arduino sketch is designed to control and display the status of multiple servos using an M5Stack device, which includes an LCD screen and buttons. Here's a breakdown of its purpose, main functions, and hardware usage:

### Purpose
The sketch manages up to 11 servos, with 7 being actively adjustable. It allows for manual and automated control of servo angles, displaying their status on an LCD screen, and accepting serial commands to adjust servo parameters.

### Main Functions

1. **Servo Management**: 
   - Each servo has properties like angle, velocity, min/max angles, idle range, and idle update interval.
   - Servos can be moved to specific angles with defined velocities and idle behaviors.

2. **Display**:
   - The LCD displays the current status of each servo, including its ID, angle, velocity, idle range, and update interval.
   - The display updates dynamically as servos are adjusted.

3. **Serial Command Handling**:
   - Commands can be sent via serial to move servos to target angles with specified parameters.
   - The command format is `MOVE_SERVO;ID=x;TARGET=y;VELOCITY=z;IDLE=a;INTERVAL=b`.

4. **Idle Movement**:
   - Servos can perform random idle movements within a specified range and interval, simulating natural motion.

5. **Button Controls**:
   - Button A decreases the selected servo's angle.
   - Button B increases the selected servo's angle.
   - Button C cycles through the servos, updating the display to reflect the current selection.

### Hardware Peripherals

- **M5Stack Device**: 
  - **LCD Screen**: Used to display servo information and status.
  - **Buttons (A, B, C)**: Allow manual control of servo angles and selection of servos.
  - **Serial Communication**: Enables external control and configuration of servos via serial commands.

This setup is ideal for applications requiring precise servo control and monitoring, such as robotics or interactive displays.
