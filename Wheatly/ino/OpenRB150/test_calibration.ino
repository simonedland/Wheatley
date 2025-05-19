/******************************************************************************
 *  OpenRB-150 • DYNAMIXEL range-calibration demo (2-cycle slow sweep, then stop)
 *  ───────────────────────────────────────────────────────────────────────────
 *  • Calibrates min/max by creeping until first under-threshold step (no jam).
 *  • Sweeps back and forth twice at a gentle speed, with ample dwell time.
 *  • Then lights the LED solid red and disables torque, holding position.
 ******************************************************************************/

#include <Dynamixel2Arduino.h>

/* ──────────────────────────  PORT MAP  ────────────────────────── */
#define DXL_SERIAL   Serial1           // Serial port for Dynamixel bus
#define DEBUG_SERIAL Serial            // Serial port for debug output
const int DXL_DIR_PIN = -1;            // Direction pin (not used on OpenRB-150)
const int DXL_PWR_EN  = BDPIN_DXL_PWR_EN; // Power enable pin for Dynamixel bus

/* ───── USER SETTINGS ─────*/
const uint32_t BAUD    = 57600;        // Baud rate for Dynamixel bus
const float    PROTO   = 2.0;          // Protocol version

/* ───── CALIBRATION CONSTANTS ─────*/
const float STEP_DEG        = 15.0f;   // Angle to move per creep step (degrees)
const int   WAIT_MS         = 500;     // Wait time after each creep (ms)
const float STALL_THRESHOLD = 0.20f;   // If movement < 20% of step, assume limit

/* ───── SPEED & TIMING SETTINGS ─────*/
const float VELOCITY_DEG_S = 10.0f;    // Max sweep speed (degrees/second)
const int   SWEEP_DELAY_MS = 5000;     // Dwell time at each end of sweep (ms)

/* ───── MODEL-SPECIFIC RESOLUTION ─────*/
const float DEG_PER_TICK = 360.0f/4096.0f; // Degrees per encoder tick (for 12-bit Dynamixel)

Dynamixel2Arduino dxl( DXL_SERIAL, DXL_DIR_PIN );
using namespace ControlTableItem;

// Convert degrees to Dynamixel ticks
inline int32_t deg2t(float d)  { return int32_t(d/DEG_PER_TICK + 0.5f); }
// Convert Dynamixel ticks to degrees
inline float   t2deg(int32_t t){ return t*DEG_PER_TICK; }

/* ─── globals to hold the measured limits ──────────────────────── */
int32_t minPos, maxPos; // Will store the measured min/max positions

// === ADVANCED MULTI-SERVO CALIBRATION AND DATA REPORTING ===
//
// This version supports 7 servos (IDs 0-6). Some servos use hardcoded min/max values,
// others are calibrated. After calibration, all min/max data is sent to an ESP32 via Serial.

// Use a macro to auto-generate the servo ID array for 0..6
#define NUM_SERVOS 7
const uint8_t SERVOS[NUM_SERVOS] = {0, 1, 2, 3, 4, 5, 6}; // Servo IDs 0-6

// Specify which servos use manual min/max (true = manual, false = calibrate)
const bool USE_MANUAL_LIMITS[NUM_SERVOS] = {true, false, true, false, false, true, false};

// Manual min/max values (degrees) for servos that use manual limits
const float MANUAL_MIN[NUM_SERVOS] = {-90, 0, -45, 0, 0, -60, 0};
const float MANUAL_MAX[NUM_SERVOS] = {90, 0, 45, 0, 0, 60, 0};

// Store min/max positions (ticks) for all servos
int32_t minPosArr[NUM_SERVOS];
int32_t maxPosArr[NUM_SERVOS];

// Servo names for correlation with UI and Python config
const char* SERVO_NAMES[NUM_SERVOS] = {
  "lens",    // 0
  "eyelid1", // 1
  "eyelid2", // 2
  "eyeX",    // 3
  "eyeY",    // 4
  "handle1", // 5
  "handle2"  // 6
};

// Creep in one direction until the servo stops moving (hits limit)
// Returns the last valid position before the limit
int32_t findLimit(uint8_t id, int dir) {
  const int32_t step    = deg2t(STEP_DEG)*dir; // Step size in ticks, with direction
  int32_t       lastPos = dxl.getPresentPosition(id); // Start from current position

  while (true) {
    dxl.setGoalPosition(id, lastPos + step); // Command next step
    while (dxl.readControlTableItem(MOVING, id)); // Wait for movement to finish
    delay(WAIT_MS); // Allow time to settle

    int32_t nowPos    = dxl.getPresentPosition(id); // Read new position
    float    movement = abs(nowPos - lastPos);      // How far did it move?
    float    threshold= abs(step)*STALL_THRESHOLD;  // Minimum movement to count as not stalled

    if (movement < threshold) {
      // If movement is too small, we've hit the limit
      return lastPos;
    }
    lastPos = nowPos; // Otherwise, keep creeping
  }
}

// Helper: Print the status of all servos in a table
void printAllServoStatus() {
  DEBUG_SERIAL.println("\nServo Status Table:");
  DEBUG_SERIAL.println("ID\tName\t\tMin(deg)\tMax(deg)\tCurrent(deg)");
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    float minD = t2deg(minPosArr[i]);
    float maxD = t2deg(maxPosArr[i]);
    float curD = 0;
    if (dxl.ping(SERVOS[i])) {
      curD = t2deg(dxl.getPresentPosition(SERVOS[i]));
    }
    DEBUG_SERIAL.print(SERVOS[i]); DEBUG_SERIAL.print("\t");
    DEBUG_SERIAL.print(SERVO_NAMES[i]); DEBUG_SERIAL.print("\t");
    if (strlen(SERVO_NAMES[i]) < 7) DEBUG_SERIAL.print("\t"); // align
    DEBUG_SERIAL.print(minD, 1); DEBUG_SERIAL.print("\t\t");
    DEBUG_SERIAL.print(maxD, 1); DEBUG_SERIAL.print("\t\t");
    DEBUG_SERIAL.print(curD, 1);
    DEBUG_SERIAL.println();
  }
}

// Modified calibrate function to support per-servo calibration/manual
void calibrateOrAssignLimits(uint8_t idx) {
  uint8_t id = SERVOS[idx];
  const char* name = SERVO_NAMES[idx];
  DEBUG_SERIAL.print("[INFO] Preparing to calibrate/assign limits for servo ");
  DEBUG_SERIAL.print(id); DEBUG_SERIAL.print(" ("); DEBUG_SERIAL.print(name); DEBUG_SERIAL.println(")");
  if (USE_MANUAL_LIMITS[idx]) {
    minPosArr[idx] = deg2t(MANUAL_MIN[idx]);
    maxPosArr[idx] = deg2t(MANUAL_MAX[idx]);
    DEBUG_SERIAL.print("[INFO] Servo "); DEBUG_SERIAL.print(id);
    DEBUG_SERIAL.print(" (" ); DEBUG_SERIAL.print(name); DEBUG_SERIAL.print(") manual min = ");
    DEBUG_SERIAL.print(MANUAL_MIN[idx]);
    DEBUG_SERIAL.print("°, max = "); DEBUG_SERIAL.print(MANUAL_MAX[idx]);
    DEBUG_SERIAL.println("°");
  } else {
    DEBUG_SERIAL.print("[CALIBRATE] Servo "); DEBUG_SERIAL.print(id);
    DEBUG_SERIAL.print(" (" ); DEBUG_SERIAL.print(name); DEBUG_SERIAL.println(") starting calibration...");
    dxl.torqueOff(id);
    dxl.setOperatingMode(id, OP_EXTENDED_POSITION);
    dxl.writeControlTableItem(PROFILE_VELOCITY, id, deg2t(VELOCITY_DEG_S));
    dxl.torqueOn(id);
    int32_t center = dxl.getPresentPosition(id);
    minPosArr[idx] = findLimit(id, -1);
    maxPosArr[idx] = findLimit(id, +1);
    DEBUG_SERIAL.print("[INFO] Servo "); DEBUG_SERIAL.print(id);
    DEBUG_SERIAL.print(" (" ); DEBUG_SERIAL.print(name); DEBUG_SERIAL.print(") calibrated min = ");
    DEBUG_SERIAL.print(t2deg(minPosArr[idx]), 1);
    DEBUG_SERIAL.print("°, max = "); DEBUG_SERIAL.print(t2deg(maxPosArr[idx]), 1);
    DEBUG_SERIAL.println("°");
    dxl.setGoalPosition(id, center);
    while (dxl.readControlTableItem(MOVING, id));
  }
  printAllServoStatus();
}

// Add a flag to control dry run mode
bool dryrunn = DRYRUNN; // DRYRUNN is the default, but can be set at runtime if ESP32 is not detected

// Send all min/max data to ESP32 as CSV over Serial, or just print if dry run
void sendLimitsToESP32() {
  DEBUG_SERIAL.println("\n[INFO] Sending min/max data to ESP32:");
  // Format: id,min_deg,max_deg;id,min_deg,max_deg;...
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    float minD = t2deg(minPosArr[i]);
    float maxD = t2deg(maxPosArr[i]);
    if (dryrunn) {
      // Print to Serial only
      Serial.print(SERVOS[i]); Serial.print(",");
      Serial.print(minD, 1); Serial.print(",");
      Serial.print(maxD, 1);
      if (i < NUM_SERVOS - 1) Serial.print(";");
    } else {
      // Send to ESP32 via Serial2
      Serial2.print(SERVOS[i]); Serial2.print(",");
      Serial2.print(minD, 1); Serial2.print(",");
      Serial2.print(maxD, 1);
      if (i < NUM_SERVOS - 1) Serial2.print(";");
    }
    DEBUG_SERIAL.print("[ID "); DEBUG_SERIAL.print(SERVOS[i]);
    DEBUG_SERIAL.print(": min "); DEBUG_SERIAL.print(minD, 1);
    DEBUG_SERIAL.print(", max "); DEBUG_SERIAL.print(maxD, 1);
    DEBUG_SERIAL.println("]");
  }
  if (dryrunn) {
    Serial.println(); // End of message
  } else {
    Serial2.println(); // End of message
  }
}

// --- Serial Command Parsing from ESP32 ---
// Accepts: MOVE_SERVO;ID=2;TARGET=45;VELOCITY=5;IDLE=10;INTERVAL=1500\n
void handleMoveServoCommand(const String& cmd) {
  DEBUG_SERIAL.print("[CMD] Received: "); DEBUG_SERIAL.println(cmd);
  int id = -1;
  float target = 0;
  float velocity = VELOCITY_DEG_S;
  int idIdx = cmd.indexOf("ID=");
  int targetIdx = cmd.indexOf("TARGET=");
  int velIdx = cmd.indexOf("VELOCITY=");
  if (idIdx >= 0) {
    id = cmd.substring(idIdx + 3, cmd.indexOf(';', idIdx)).toInt();
  }
  if (targetIdx >= 0) {
    target = cmd.substring(targetIdx + 7, cmd.indexOf(';', targetIdx) > 0 ? cmd.indexOf(';', targetIdx) : cmd.length()).toFloat();
  }
  if (velIdx >= 0) {
    velocity = cmd.substring(velIdx + 9, cmd.indexOf(';', velIdx) > 0 ? cmd.indexOf(';', velIdx) : cmd.length()).toFloat();
  }
  if (id >= 0 && id < NUM_SERVOS) {
    // Clamp target to min/max
    float minD = t2deg(minPosArr[id]);
    float maxD = t2deg(maxPosArr[id]);
    float clamped = constrain(target, minD, maxD);
    DEBUG_SERIAL.print("[ACTION] Moving servo "); DEBUG_SERIAL.print(id);
    DEBUG_SERIAL.print(" (" ); DEBUG_SERIAL.print(SERVO_NAMES[id]); DEBUG_SERIAL.print(") to ");
    DEBUG_SERIAL.print(clamped); DEBUG_SERIAL.print(" deg at velocity "); DEBUG_SERIAL.println(velocity);
    dxl.writeControlTableItem(PROFILE_VELOCITY, id, deg2t(velocity));
    dxl.setGoalPosition(id, deg2t(clamped));
    printAllServoStatus();
  } else {
    DEBUG_SERIAL.println("[ERROR] Invalid servo ID in MOVE_SERVO command");
    if (!dryrunn) Serial2.println("ERR: Invalid servo ID");
  }
}

// Arduino setup: initialize serial, Dynamixel, power, and calibrate all servos
void setup() {
  DEBUG_SERIAL.begin(115200); // Start debug serial
  DEBUG_SERIAL.println("[BOOT] OpenRB-150 calibration firmware starting...");
  dxl.begin(BAUD);            // Start Dynamixel bus
  dxl.setPortProtocolVersion(PROTO); // Set protocol version

  pinMode(DXL_PWR_EN, OUTPUT);        // Set power enable pin as output
  digitalWrite(DXL_PWR_EN, HIGH);     // Turn on Dynamixel bus power

  Serial2.begin(115200); // Serial2 for ESP32 communication

  // Try to detect ESP32 by sending a handshake and waiting for a response
  if (!DRYRUNN) {
    DEBUG_SERIAL.println("[INFO] Attempting handshake with ESP32...");
    Serial2.print("HELLO\n");
    unsigned long start = millis();
    bool esp32_found = false;
    while (millis() - start < 500) { // Wait up to 500ms for a response
      if (Serial2.available()) {
        String resp = Serial2.readStringUntil('\n');
        if (resp.indexOf("ESP32") >= 0) {
          esp32_found = true;
          break;
        }
      }
    }
    if (!esp32_found) {
      dryrunn = true;
      DEBUG_SERIAL.println("[WARN] ESP32 not detected, switching to dry run mode.");
    } else {
      dryrunn = false;
      DEBUG_SERIAL.println("[INFO] ESP32 detected, sending data to ESP32.");
    }
  }
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    uint8_t id = SERVOS[i];
    DEBUG_SERIAL.print("[INFO] Pinging servo ID "); DEBUG_SERIAL.print(id); DEBUG_SERIAL.print(" ("); DEBUG_SERIAL.print(SERVO_NAMES[i]); DEBUG_SERIAL.println(")...");
    if (!dxl.ping(id)) {
      DEBUG_SERIAL.print("[ERROR] ❌ ID ");
      DEBUG_SERIAL.print(id);
      DEBUG_SERIAL.println(" not responding. Assigning default min/max = 0.");
      // Assign default min/max if not responding
      minPosArr[i] = deg2t(0);
      maxPosArr[i] = deg2t(0);
      continue;
    }
    calibrateOrAssignLimits(i);
  }
  sendLimitsToESP32();
  DEBUG_SERIAL.println("\n--- calibration complete ---");
  printAllServoStatus();
}

// Arduino loop: sweep back and forth twice, then stop and indicate done
void loop() {
  // Handle incoming commands from ESP32
  if (!dryrunn && Serial2.available()) {
    String cmd = Serial2.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("MOVE_SERVO")) {
      DEBUG_SERIAL.println("[INFO] Handling MOVE_SERVO command from ESP32...");
      handleMoveServoCommand(cmd);
    }
  }
  // Example: sweep only the first servo (ID 0) as before, or expand as needed
  uint8_t idx = 0;
  uint8_t id = SERVOS[idx];
  static int cycles = 0;

  if (cycles < 2) {
    DEBUG_SERIAL.println("[SWEEP] Moving to min position...");
    dxl.setGoalPosition(id, minPosArr[idx]);
    while (dxl.readControlTableItem(MOVING, id));
    printAllServoStatus();
    delay(SWEEP_DELAY_MS);
    DEBUG_SERIAL.println("[SWEEP] Moving to max position...");
    dxl.setGoalPosition(id, maxPosArr[idx]);
    while (dxl.readControlTableItem(MOVING, id));
    printAllServoStatus();
    delay(SWEEP_DELAY_MS);
    cycles++;
  } else {
    DEBUG_SERIAL.println("[DONE] Sweep complete. Disabling torque and lighting LED.");
    dxl.writeControlTableItem(LED, id, 1);
    dxl.torqueOff(id);
    printAllServoStatus();
    while (true) { /* halt further actions */ }
  }
}