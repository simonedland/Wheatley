# AI Summary

### C:\GIT\Wheatly\Wheatley\Wheatley\ino\M5 stack Core2\M5Stack_Core2.ino
Certainly! Here’s a **detailed plain-English summary** of the provided Arduino sketch, covering its purpose, structure, hardware use, main logic, and key components.

---

## **Overall Purpose**

This sketch implements a **touch-based user interface** (UI) for controlling a robotic head with **7 servos** and a **NeoPixel LED strip**. It runs on an M5Stack Core2 (or similar ESP32-based device), communicating with an **OpenRB-150 servo controller** via UART2. The UI allows users to view and adjust servo positions, see their status, and interact with the system via hardware buttons and USB serial commands. The LED strip provides visual feedback, including a dedicated LED for microphone status.

---

## **Hardware Peripherals Used**

- **M5Stack Core2**: Provides the LCD display, touch buttons (A, B, C), and runs the sketch.
- **UART2 (HardwareSerial)**: Used to communicate with the OpenRB-150 servo controller.
  - **RX2_PIN (GPIO 13)**: UART2 RX
  - **TX2_PIN (GPIO 14)**: UART2 TX
- **NeoPixel LED strip**: 17 LEDs on **GPIO 27** (LED_PIN), with LED 16 (MIC_LED_INDEX) reserved for microphone status.
- **USB Serial**: For debugging, configuration, and external control.

---

## **External Libraries / Dependencies**

- **M5Unified.h**: For M5Stack Core2 hardware abstraction (LCD, buttons, etc.).
- **HardwareSerial.h**: For UART communication.
- **Adafruit_NeoPixel.h**: For controlling the NeoPixel LED strip.

---

## **Key Classes, Functions, and Responsibilities**

### **Global State and Configuration**

- **ServoState struct**: Holds per-servo configuration and state (angle, velocity, limits, idle jitter, etc.).
- **servos[]**: Array of ServoState for each active servo (7 total).
- **SERVO_NAMES[]**: Human-readable names for each servo.
- **Various flags**: Track handshake status, demo mode, calibration, etc.

### **LED Control**

- **setAll(col)**: Sets all LEDs (except MIC_LED) to the specified color.
- **blinkScreen(times)**: Blinks the screen and LEDs red a number of times.
- **blinkColor(col, times, onMs, offMs)**: Blinks LEDs with a specific color.

- **processLedCommand(cmd)**: Parses and executes `SET_LED;R=...;G=...;B=...;` commands for the LED strip (excluding MIC_LED).
- **processMicLedCommand(cmd)**: Handles `SET_MIC_LED;IDX=...;R=...;G=...;B=...;` commands for the microphone status LED only.

### **Servo Control and Communication**

- **sendMoveServoCommand(id, tgt, vel)**: Sends a command to OpenRB-150 to move a servo.
- **handleCalibrationData(line)**: Parses calibration data from OpenRB-150 and updates servo limits/status.
- **sendServoConfig()**: Sends current servo configuration over USB serial.

### **UI Drawing**

- **drawWindow()**: Draws the entire servo status window on the LCD.
- **drawLine(i, y)**: Draws a single row (servo) in the UI.
- **drawSingle(i)**: Redraws a single servo row.

### **Command Handlers**

- **handleUsbCommands()**: Handles commands received over USB serial (LED, servo config, forwarding).
- **handleLink()**: Handles messages from OpenRB-150 over UART2 (handshake, calibration, LED, etc.).

### **Demo Mode**

- **enterDemoMode()**: Enters a fallback mode if no handshake is received from OpenRB-150.

---

## **Code Structure and Component Interaction**

### **Startup (`setup()`)**

1. **Initialize hardware**: M5Stack, UART2, NeoPixel strip.
2. **Test LEDs**: Red, green, blue, then off.
3. **Draw UI**: Initial servo window.
4. **Start handshake**: Send "ESP32" to OpenRB-150.

### **Main Loop (`loop()`)**

1. **Update M5Stack state**.
2. **Handle UART2 messages** (`handleLink()`):  
   - Process handshake, calibration, LED commands, and log others.
3. **Handle USB serial commands** (`handleUsbCommands()`):  
   - LED commands, servo config, config requests, and forward others to OpenRB-150.
4. **Handshake logic**:  
   - If handshake not received, retry every second.
   - If still no handshake after 10 seconds, enter demo mode.
5. **Idle Jitter**:  
   - If calibrated, periodically nudge servos within their idle range for realism.
6. **Button Handling**:
   - **Button A**: Decrement selected servo angle.
   - **Button B**: Increment selected servo angle.
   - **Button C**: Cycle to next available servo.
7. **UI Updates**:  
   - Redraw affected rows as needed.
8. **Delay**: 33 ms per loop iteration.

---

## **Notable Algorithms and Logic**

- **Servo Idle Jitter**:  
  Each servo (if enabled and with idle jitter configured) is randomly moved within a specified range and interval, simulating natural movement.

- **Handshake and Demo Mode**:  
  The sketch expects a "HELLO" from OpenRB-150. If not received within 10 seconds, it enters a demo mode where all servos are marked as available, but no real commands are sent.

- **LED Command Parsing**:  
  Robust parsing of LED commands, with separation between general LEDs and the dedicated microphone LED.

- **Scrolling UI**:  
  The UI supports scrolling and selection among servos, with visual feedback for disabled or dead servos.

---

## **Configuration and Environment Requirements**

- **Hardware**:  
  - M5Stack Core2 (or compatible ESP32 board with LCD and buttons)
  - OpenRB-150 servo controller (connected via UART2)
  - NeoPixel LED strip (17 LEDs, data on GPIO 27)
- **Libraries**:  
  - M5Unified
  - Adafruit_NeoPixel
- **Wiring**:  
  - UART2 RX/TX: GPIO 13/14
  - LED strip: GPIO 27

---

## **Summary Table of Key Functions**

| Function                   | Responsibility                                             |
|----------------------------|-----------------------------------------------------------|
| setup()                    | Initialize hardware, test LEDs, start handshake           |
| loop()                     | Main event loop: handle comms, UI, input, idle jitter     |
| setAll(), blinkScreen()    | Control NeoPixel strip (except MIC_LED)                   |
| processLedCommand()        | Parse and apply LED color commands                        |
| processMicLedCommand()     | Parse and apply mic-status LED command                    |
| handleLink()               | Process UART2 messages from OpenRB-150                    |
| handleUsbCommands()        | Process USB serial commands                               |
| sendMoveServoCommand()     | Send servo move command to OpenRB-150                     |
| handleCalibrationData()    | Parse and apply servo calibration data                    |
| drawWindow(), drawLine()   | Draw/refresh UI on LCD                                    |
| enterDemoMode()            | Fallback if OpenRB-150 is not detected                    |

---

## **In Summary**

This sketch is a robust, interactive UI and control hub for a 7-servo robotic head, providing real-time feedback, configuration, and control via touch buttons, a color LCD, and a NeoPixel strip. It communicates with an OpenRB-150 servo controller over UART2, supports fallback demo operation, and is designed for easy integration and debugging via USB serial. The code is modular, with clear separation of hardware abstraction, UI, communication, and logic.
