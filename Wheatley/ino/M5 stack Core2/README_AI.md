# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\ino\M5 stack Core2\M5Stack_Core2.ino
Certainly! Here’s a **detailed summary** of the provided Arduino sketch, written in plain English, covering its purpose, structure, hardware use, key logic, and dependencies.

---

## **Overall Purpose**

This sketch implements a **touch-based user interface (UI) for controlling a 7-servo robotic head** using an M5Stack Core2 device. It communicates with an OpenRB-150 servo controller board over UART2, manages a 17-pixel NeoPixel LED strip (with special handling for a microphone status LED), and provides both serial and on-device UI for servo configuration and monitoring.

---

## **Main Hardware Peripherals Used**

1. **M5Stack Core2**:  
   - Provides LCD display, touch buttons (A/B/C), and main MCU.
2. **OpenRB-150 Board**:  
   - Connected via UART2 (pins 13/14), controls the actual servos.
3. **NeoPixel LED Strip**:  
   - 17 LEDs on pin 27, with the last LED (index 16) reserved for microphone status.
4. **USB Serial**:  
   - For debugging, configuration, and command input from a computer.

---

## **Key Libraries and Dependencies**

- **M5Unified.h**: For M5Stack Core2 device abstraction (LCD, buttons, etc.).
- **HardwareSerial**: For UART communication with OpenRB-150.
- **Adafruit_NeoPixel**: For controlling the RGB LED strip.

**Environment Requirements:**
- M5Stack Core2 (or compatible M5 device)
- OpenRB-150 board (or compatible servo controller)
- Adafruit NeoPixel library installed
- M5Unified library installed

---

## **Code Structure and Component Interaction**

### **Global State and Configuration**

- **ServoState struct**: Holds current angle, velocity, min/max limits, idle jitter parameters, etc. for each servo.
- **servos[]**: Array of ServoState for 7 active servos.
- **SERVO_NAMES[]**: Names for each servo, used in the UI.
- **Various flags**: Track handshake, demo mode, calibration, etc.

### **Setup**

- Initializes all hardware (M5Stack, UART, NeoPixel).
- Performs an LED strip test (cycling through red, green, blue).
- Draws the initial UI window.
- Sends an initial "ESP32" handshake to the OpenRB-150.

### **Main Loop**

- **handleLink()**: Processes incoming UART messages from OpenRB-150 (handshake, calibration, LED commands, etc.).
- **handleUsbCommands()**: Processes commands from USB serial (LED control, servo config, forwarding).
- **Handshake logic**: Retries handshake every second until successful, enters demo mode after 10 seconds if no response.
- **Idle Jitter**: If calibrated, periodically jitters servos within a small range for realism.
- **Button Handling**:  
  - **A**: Decrement selected servo angle.
  - **B**: Increment selected servo angle.
  - **C**: Cycle to next available servo.
- **UI Redraws**: Updates only affected lines for efficiency.

---

## **Key Classes, Functions, and Responsibilities**

### **LED Control**

- **setAll(col)**: Sets all LEDs (except MIC_LED_INDEX) to a color.
- **blinkScreen(times)**: Blinks the screen and LEDs red a number of times.
- **blinkColor(col, times, onMs, offMs)**: Blinks LEDs a specified color.

- **processLedCommand(cmd)**: Parses and executes "SET_LED;" commands for the LED strip (excluding MIC_LED).
- **processMicLedCommand(cmd)**: Handles "SET_MIC_LED;" commands, only affecting the microphone LED.

### **Servo Communication and State**

- **sendMoveServoCommand(id, tgt, vel)**: Sends a servo movement command to OpenRB-150.
- **handleCalibrationData(line)**: Parses calibration data from OpenRB-150, updates servo limits and status.
- **sendServoConfig()**: Reports current servo configuration over USB serial.

### **UI Drawing**

- **drawWindow()**: Draws the entire servo list window.
- **drawLine(i, y)**: Draws a single row (servo) at a given Y position.
- **drawSingle(i)**: Redraws a specific servo row if visible.

### **Demo Mode**

- **enterDemoMode()**: Enables demo mode if handshake fails, disables actual servo commands, marks all servos as present.

### **Input Handling**

- **handleUsbCommands()**: Handles USB serial commands for LED/servo control and forwarding.
- **handleLink()**: Handles UART messages from OpenRB-150 (handshake, calibration, LED commands).

---

## **Notable Algorithms and Logic**

### **1. Handshake and Demo Mode**

- On startup, repeatedly sends "ESP32" handshake to OpenRB-150.
- If no handshake is received within 10 seconds, enters demo mode (simulates servo presence, disables real commands).

### **2. Servo Idle Jitter**

- For each active, present servo, if idle jitter is enabled, randomly moves servo within a small range around its initial angle at random intervals (to simulate life/realism).

### **3. LED Command Parsing**

- Parses commands of the form "SET_LED;R=...;G=...;B=..." and "SET_MIC_LED;IDX=...;R=...;G=...;B=..." to control the LED strip and microphone LED independently.

### **4. UI Navigation**

- Uses M5Stack buttons to increment/decrement servo angles or cycle through servos.
- Only allows interaction with servos that are present (as determined by calibration or demo mode).

---

## **Configuration and Environment Requirements**

- **Hardware**: M5Stack Core2, OpenRB-150, NeoPixel strip (17 LEDs), USB for debugging/config.
- **Libraries**: M5Unified, Adafruit_NeoPixel, HardwareSerial.
- **Pin Assignments**:  
  - UART2 RX: GPIO 13  
  - UART2 TX: GPIO 14  
  - NeoPixel: GPIO 27

---

## **Summary Table of Key Functions**

| Function                  | Responsibility                                            |
|---------------------------|----------------------------------------------------------|
| `setup()`                 | Initialize hardware, perform LED test, start handshake   |
| `loop()`                  | Main event loop: handle comms, UI, idle jitter, buttons  |
| `handleLink()`            | Process UART2 messages from OpenRB-150                   |
| `handleUsbCommands()`     | Process commands from USB serial                         |
| `processLedCommand()`     | Parse and execute LED strip color commands               |
| `processMicLedCommand()`  | Parse and execute mic LED color commands                 |
| `sendMoveServoCommand()`  | Send servo movement command to OpenRB-150                |
| `handleCalibrationData()` | Parse servo calibration data and update state            |
| `drawWindow()`, `drawLine()` | Draw UI to LCD display                              |
| `enterDemoMode()`         | Enter fallback mode if handshake fails                   |

---

## **How Components Interact**

- **User** interacts with the device via touch buttons and USB serial.
- **UI** displays servo info and allows angle adjustment.
- **M5Stack** sends/receives commands to/from OpenRB-150 over UART2.
- **LED strip** is controlled by both the UI and incoming commands (with mic LED handled separately).
- **Servo state** is synchronized with OpenRB-150 via handshake and calibration messages.

---

## **Special Notes**

- **SET_LED** commands skip the mic LED; **SET_MIC_LED** only affects the mic LED.
- **Demo mode** allows UI operation even if OpenRB-150 is not present.
- **Idle jitter** adds realism by randomly moving servos when idle.
- **Efficient UI updates**: Only redraws changed rows, not the whole screen.

---

## **In Summary**

This sketch is a robust, interactive controller for a 7-servo robotic head, providing both a local UI and remote command/control via serial and UART. It manages servo state, LED feedback, and communication with a dedicated servo controller, with fallback demo capabilities and a user-friendly interface.
