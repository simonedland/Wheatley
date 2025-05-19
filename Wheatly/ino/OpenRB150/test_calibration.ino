/******************************************************************************
 *  OpenRB-150 • DYNAMIXEL range-calibration demo (2-cycle slow sweep, then stop)
 *  ───────────────────────────────────────────────────────────────────────────
 *  • Calibrates min/max by creeping until first under-threshold step (no jam).
 *  • Sweeps back and forth twice at a gentle speed, with ample dwell time.
 *  • Then lights the LED solid red and disables torque, holding position.
 ******************************************************************************/

#include <Dynamixel2Arduino.h>

/* ──────────────────────────  PORT MAP  ────────────────────────── */
#define DXL_SERIAL   Serial1
#define DEBUG_SERIAL Serial
const int DXL_DIR_PIN = -1;
const int DXL_PWR_EN  = BDPIN_DXL_PWR_EN;

/* ───── USER SETTINGS ─────*/
const uint8_t SERVOS[] = {1};
const uint8_t NUM      = sizeof(SERVOS)/sizeof(SERVOS[0]);
const uint32_t BAUD    = 57600;
const float    PROTO   = 2.0;

/* ───── CALIBRATION CONSTANTS ─────*/
const float STEP_DEG        = 15.0f;  // creep step (deg)
const int   WAIT_MS         = 500;    // settle delay after each creep (ms)
const float STALL_THRESHOLD = 0.20f;  // <20% of step → limit

/* ───── SPEED & TIMING SETTINGS ─────*/
const float VELOCITY_DEG_S = 10.0f;   // max sweep speed (deg/s)
const int   SWEEP_DELAY_MS = 5000;    // dwell at each end (ms)

/* ───── MODEL-SPECIFIC RESOLUTION ─────*/
const float DEG_PER_TICK = 360.0f/4096.0f;

Dynamixel2Arduino dxl( DXL_SERIAL, DXL_DIR_PIN );
using namespace ControlTableItem;

inline int32_t deg2t(float d)  { return int32_t(d/DEG_PER_TICK + 0.5f); }
inline float   t2deg(int32_t t){ return t*DEG_PER_TICK; }

/* ─── globals to hold the measured limits ──────────────────────── */
int32_t minPos, maxPos;

int32_t findLimit(uint8_t id, int dir) {
  const int32_t step    = deg2t(STEP_DEG)*dir;
  int32_t       lastPos = dxl.getPresentPosition(id);

  while (true) {
    dxl.setGoalPosition(id, lastPos + step);
    while (dxl.readControlTableItem(MOVING, id));
    delay(WAIT_MS);

    int32_t nowPos    = dxl.getPresentPosition(id);
    float    movement = abs(nowPos - lastPos);
    float    threshold= abs(step)*STALL_THRESHOLD;

    if (movement < threshold) {
      // limit reached: return last valid position
      return lastPos;
    }
    lastPos = nowPos;
  }
}

void calibrate(uint8_t id) {
  DEBUG_SERIAL.print("\nCalibrating ID ");
  DEBUG_SERIAL.println(id);

  dxl.torqueOff(id);
  dxl.setOperatingMode(id, OP_EXTENDED_POSITION);
  // set a gentle speed profile
  dxl.writeControlTableItem(PROFILE_VELOCITY, id, deg2t(VELOCITY_DEG_S));
  dxl.torqueOn(id);

  int32_t center = dxl.getPresentPosition(id);
  minPos = findLimit(id, -1);
  maxPos = findLimit(id, +1);

  DEBUG_SERIAL.print("→ min = ");
  DEBUG_SERIAL.print(t2deg(minPos), 1);
  DEBUG_SERIAL.print("°, max = ");
  DEBUG_SERIAL.print(t2deg(maxPos), 1);
  DEBUG_SERIAL.println("°");

  // park at center, leave torque ON until after sweeps
  dxl.setGoalPosition(id, center);
  while (dxl.readControlTableItem(MOVING, id));
}

void setup() {
  DEBUG_SERIAL.begin(115200);
  dxl.begin(BAUD);
  dxl.setPortProtocolVersion(PROTO);

  pinMode(DXL_PWR_EN, OUTPUT);
  digitalWrite(DXL_PWR_EN, HIGH);

  for (uint8_t i = 0; i < NUM; ++i) {
    uint8_t id = SERVOS[i];
    if (!dxl.ping(id)) {
      DEBUG_SERIAL.print("❌ ID ");
      DEBUG_SERIAL.print(id);
      DEBUG_SERIAL.println(" not responding.");
      continue;
    }
    calibrate(id);
  }
  DEBUG_SERIAL.println("\n--- calibration complete ---");
}

void loop() {
  uint8_t id = SERVOS[0];
  static int cycles = 0;

  if (cycles < 2) {
    // sweep to min
    dxl.setGoalPosition(id, minPos);
    while (dxl.readControlTableItem(MOVING, id));
    delay(SWEEP_DELAY_MS);

    // sweep to max
    dxl.setGoalPosition(id, maxPos);
    while (dxl.readControlTableItem(MOVING, id));
    delay(SWEEP_DELAY_MS);

    cycles++;
  }
  else {
    // after two full back-and-forths: indicate done and stop moving
    dxl.writeControlTableItem(LED, id, 1);   // red LED on
    dxl.torqueOff(id);                       // disable motor
    while (true) { /* halt further actions */ }
  }
}