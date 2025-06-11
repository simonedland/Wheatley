# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatly\ino\M5 stack Core2\M5Stack_Core2.ino
Certainly! Here’s a **plain English summary** of the provided Arduino sketch, covering its **purpose, structure, hardware use, key logic, and dependencies**.

---

## **Overall Purpose**

This Arduino sketch implements a **touch-based user interface** for controlling a robotic head with **seven servos** and a **NeoPixel LED strip**. It runs on an **M5Stack Core2** (ESP32-based device), communicates with an **OpenRB-150** controller board via UART2, and provides a scrolling UI for servo control, calibration, and monitoring. It also supports USB serial commands for configuration and LED control, and features a "demo mode" if the OpenRB-150 is not detected.

---

## **Main Hardware Peripherals Used**

- **M5Stack Core2**: Main microcontroller with LCD touchscreen and three physical buttons (A, B, C).
- **UART2 (HardwareSerial)**: Communicates with OpenRB-150 (robot controller) on pins 13 (RX) and 14 (TX) at 115200 baud.
- **NeoPixel (Adafruit_NeoPixel)**: 16-LED RGB strip on pin 27 for visual feedback and status indication.
- **USB Serial**: For debugging, configuration, and command pass-through.

---

## **Key Classes, Functions, and Responsibilities**

### **Global State & Data Structures**

- **ServoState struct**: Holds each servo’s angle, velocity, calibration limits, idle jitter range, and timing.
- **servos[]**: Array of ServoState for each of the 7 active servos.
- **servoPingResult[]**: Tracks which servos are responsive (set by calibration).
- **Flags**: `dryRun`, `demoMode`, `handshakeReceived`, `calibrationReceived` for controlling UI and logic flow.

### **LED Control**

- **setAll(col)**: Sets all NeoPixels to a given color, logs the change.
- **blinkScreen(times)**: Blinks the LED strip red/black for handshake feedback.
- **blinkColor(col, times, onMs, offMs)**: Blinks the strip with any color.
- **processLedCommand(cmd)**: Parses and executes LED color commands from serial or UART.

### **Servo & Link Handling**

- **sendMoveServoCommand(id, tgt, vel)**: Sends a formatted servo move command to OpenRB-150.
- **handleCalibrationData(line)**: Parses calibration data from OpenRB-150, updates servo limits and status.
- **sendServoConfig()**: Sends current servo configuration over USB serial.

### **UI Drawing**

- **drawLine(i, y)**: Draws a single row (servo) in the UI, showing its state.
- **drawWindow()**: Draws the full visible list of servos.
- **drawSingle(i)**: Redraws a single servo row.

### **Command Handling**

- **handleUsbCommands()**: Processes commands from USB serial, including LED and servo configuration, and forwards unknown commands to OpenRB-150.
- **handleLink()**: Processes messages from OpenRB-150, including handshake, calibration, and LED commands.

### **Demo Mode**

- **enterDemoMode()**: Enables demo mode if no handshake is received after 10 seconds, sets up fake calibration, and blinks blue.

---

## **Code Structure & Component Interaction**

1. **setup()**
   - Initializes M5Stack, UART2, NeoPixel strip, and LCD.
   - Performs a startup LED test.
   - Draws the initial UI.
   - Sends a handshake ("ESP32") to OpenRB-150.

2. **loop()**
   - Updates M5Stack state.
   - Handles incoming UART and USB serial commands.
   - If no handshake after 10 seconds, enters demo mode.
   - Handles servo idle jitter: randomly moves servos within a range if idle.
   - Handles button input:
     - **A**: Decrement selected servo’s angle.
     - **B**: Increment selected servo’s angle.
     - **C**: Cycle to next available servo.
   - UI is updated as needed.
   - Small delay for loop timing.

3. **Communication**
   - **OpenRB-150**: Receives commands to move servos, calibration data, and LED commands. Sends back handshake and calibration.
   - **USB Serial**: Receives commands for LED/servo config, passes unknown commands to OpenRB-150.

4. **LED Feedback**
   - Visual feedback for handshake, demo mode, and status via NeoPixel strip.

---

## **Notable Logic & Algorithms**

- **Idle Jitter**: If enabled, each servo randomly moves within a defined range and interval to simulate "life" when idle.
- **Calibration Handling**: Servo limits and status are updated only after receiving calibration data from OpenRB-150.
- **Demo Mode**: If OpenRB-150 is not detected, the UI and logic simulate normal operation but do not send real servo commands.
- **Scrolling UI**: Only a subset of servos is visible at once; selection and scrolling are handled with button presses.

---

## **External Libraries & Dependencies**

- **M5Unified.h**: For M5Stack Core2 hardware abstraction (LCD, buttons, etc).
- **HardwareSerial**: For UART2 communication.
- **Adafruit_NeoPixel.h**: For controlling the NeoPixel LED strip.

---

## **Configuration & Environment Requirements**

- **Hardware**: M5Stack Core2 (ESP32), OpenRB-150 controller, NeoPixel strip (16 LEDs on pin 27).
- **Connections**: UART2 on pins 13 (RX) and 14 (TX) to OpenRB-150.
- **Libraries**: M5Unified, Adafruit_NeoPixel.
- **Baud Rate**: 115200 for both USB serial and UART2.
- **LED Strip**: 16 LEDs, GRB order, 800kHz.

---

## **Summary Table of Main Features**

| Feature                | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| Servo Control          | UI for 7 servos, with angle, velocity, idle jitter, and calibration limits. |
| OpenRB-150 Link        | UART2 communication for servo commands and calibration.                     |
| LED Strip              | Visual feedback, status, and commandable via serial.                        |
| Touch/Button UI        | Scrollable list, selection, and control via buttons.                        |
| USB Serial             | Command/configuration interface, pass-through to OpenRB-150.                |
| Demo Mode              | Simulated operation if OpenRB-150 not detected.                             |
| Calibration            | Updates servo limits/status from OpenRB-150.                                |

---

## **Conclusion**

This sketch provides a robust, interactive interface for controlling a multi-servo robotic head, with extensive feedback and configuration options, and is designed for reliability (demo mode) and ease of use (UI, LED feedback). It is modular, with clear separation between UI, hardware control, and communication logic.
