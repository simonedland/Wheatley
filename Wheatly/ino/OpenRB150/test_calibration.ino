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
const uint8_t SERVOS[] = {1};          // List of Dynamixel IDs to calibrate
const uint8_t NUM      = sizeof(SERVOS)/sizeof(SERVOS[0]); // Number of servos
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

// Calibrate a single servo: find min/max, print results, park at center
void calibrate(uint8_t id) {
  DEBUG_SERIAL.print("\nCalibrating ID ");
  DEBUG_SERIAL.println(id);

  dxl.torqueOff(id); // Ensure torque is off before changing mode
  dxl.setOperatingMode(id, OP_EXTENDED_POSITION); // Use extended position mode
  // Set a gentle speed profile for safe movement
  dxl.writeControlTableItem(PROFILE_VELOCITY, id, deg2t(VELOCITY_DEG_S));
  dxl.torqueOn(id); // Enable torque

  int32_t center = dxl.getPresentPosition(id); // Save current position as center
  minPos = findLimit(id, -1); // Find minimum position (creep left)
  maxPos = findLimit(id, +1); // Find maximum position (creep right)

  DEBUG_SERIAL.print("→ min = ");
  DEBUG_SERIAL.print(t2deg(minPos), 1);
  DEBUG_SERIAL.print("°, max = ");
  DEBUG_SERIAL.print(t2deg(maxPos), 1);
  DEBUG_SERIAL.println("°");

  // Park at center, leave torque ON until after sweeps
  dxl.setGoalPosition(id, center);
  while (dxl.readControlTableItem(MOVING, id)); // Wait for movement to finish
}

// Arduino setup: initialize serial, Dynamixel, power, and calibrate all servos
void setup() {
  DEBUG_SERIAL.begin(115200); // Start debug serial
  dxl.begin(BAUD);            // Start Dynamixel bus
  dxl.setPortProtocolVersion(PROTO); // Set protocol version

  pinMode(DXL_PWR_EN, OUTPUT);        // Set power enable pin as output
  digitalWrite(DXL_PWR_EN, HIGH);     // Turn on Dynamixel bus power

  for (uint8_t i = 0; i < NUM; ++i) {
    uint8_t id = SERVOS[i];
    if (!dxl.ping(id)) {
      DEBUG_SERIAL.print("❌ ID ");
      DEBUG_SERIAL.print(id);
      DEBUG_SERIAL.println(" not responding.");
      continue;
    }
    calibrate(id); // Calibrate this servo
  }
  DEBUG_SERIAL.println("\n--- calibration complete ---");
}

// Arduino loop: sweep back and forth twice, then stop and indicate done
void loop() {
  uint8_t id = SERVOS[0]; // Only using first servo in list
  static int cycles = 0;  // Track number of sweep cycles

  if (cycles < 2) {
    // Sweep to minimum position
    dxl.setGoalPosition(id, minPos);
    while (dxl.readControlTableItem(MOVING, id));
    delay(SWEEP_DELAY_MS); // Wait at end

    // Sweep to maximum position
    dxl.setGoalPosition(id, maxPos);
    while (dxl.readControlTableItem(MOVING, id));
    delay(SWEEP_DELAY_MS); // Wait at end

    cycles++;
  }
  else {
    // After two full sweeps: turn LED red and disable torque
    dxl.writeControlTableItem(LED, id, 1);   // Turn on red LED
    dxl.torqueOff(id);                       // Disable motor torque
    while (true) { /* halt further actions */ }
  }
}