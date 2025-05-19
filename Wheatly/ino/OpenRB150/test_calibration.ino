/******************************************************************************
 *  OpenRB-150  ⇄  Core-2 UART bridge + multi-servo range-calibration demo
 *  – 2025-05-19
 *  • Uses Serial2 (TX=D14 PB22  RX=D13 PB23) at 115 200 baud to talk to an
 *    M5Stack Core2.  Falls back to “dry-run” if the Core2 does not reply.
 *  • Calibrates seven Dynamixel servos (IDs 0-6) or assigns manual limits.
 *  • After calibration it sweeps the first servo twice, then idles.
 ******************************************************************************/

#include <Dynamixel2Arduino.h>

/* ————— DYNAMIXEL BUS ————— */
#define DXL_SERIAL   Serial1          // UART wired to the JST-PX connector
const int DXL_DIR_PIN = -1;           // direction pin not used on OpenRB-150
const int DXL_PWR_EN  = BDPIN_DXL_PWR_EN;
const uint32_t DXL_BAUD     = 57600;
const float    DXL_PROTOCOL = 2.0;

/* ————— CORE-2 LINK ————— */
#define DEBUG_SERIAL Serial
const uint32_t LINK_BAUD    = 115200; // must match Core-2

/* ————— CALIBRATION BEHAVIOUR ————— */
const float STEP_DEG        = 15.0f;
const int   WAIT_MS         = 500;
const float STALL_THRESHOLD = 0.20f;
const float VELOCITY_DEG_S  = 10.0f;
const int   SWEEP_DELAY_MS  = 5000;

/* ————— ANGLE ↔︎ TICK helpers ————— */
constexpr float DEG_PER_TICK = 360.0f / 4096.0f;
inline int32_t deg2t(float d)  { return int32_t(d / DEG_PER_TICK + 0.5f); }
inline float   t2deg(int32_t t){ return t * DEG_PER_TICK; }

Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);
using namespace ControlTableItem;

/* ========================================================================== */
/*                                SERVO TABLE                                 */
/* ========================================================================== */
#define NUM_SERVOS 7
const uint8_t SERVOS[NUM_SERVOS] = {0, 1, 2, 3, 4, 5, 6};
const char* SERVO_NAMES[NUM_SERVOS] = {
  "lens", "eyelid1", "eyelid2", "eyeX", "eyeY", "handle1", "handle2"
};

/* If true → fixed limits from table, otherwise auto-calibrate */
const bool  USE_MANUAL_LIMITS[NUM_SERVOS] = {true, false, true, false, false, true, false};
const float MANUAL_MIN[NUM_SERVOS]        = {-90, 0, -45, 0, 0, -60, 0};
const float MANUAL_MAX[NUM_SERVOS]        = { 90, 0,  45, 0, 0,  60, 0};

int32_t minPosArr[NUM_SERVOS];      // filled at run-time
int32_t maxPosArr[NUM_SERVOS];

/* ========================================================================== */
/*                         CALIBRATION + HELPER ROUTINES                      */
/* ========================================================================== */

int32_t findLimit(uint8_t id, int dir)
{
  const int32_t step = deg2t(STEP_DEG) * dir;
  int32_t lastPos = dxl.getPresentPosition(id);

  while (true) {
    dxl.setGoalPosition(id, lastPos + step);
    while (dxl.readControlTableItem(MOVING, id));   // wait
    delay(WAIT_MS);

    int32_t nowPos = dxl.getPresentPosition(id);
    if (abs(nowPos - lastPos) < abs(step) * STALL_THRESHOLD)
      return lastPos;                               // limit reached
    lastPos = nowPos;
  }
}

void printAllServoStatus()
{
  DEBUG_SERIAL.println(F("\nID\tName\t\tMin°\tMax°\tCurrent°"));
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    float cur = dxl.ping(SERVOS[i]) ? t2deg(dxl.getPresentPosition(SERVOS[i])) : 0;
    DEBUG_SERIAL.printf("%d\t%-8s\t%5.1f\t%5.1f\t%5.1f\n",
                        SERVOS[i], SERVO_NAMES[i],
                        t2deg(minPosArr[i]), t2deg(maxPosArr[i]), cur);
  }
}

void calibrateOrAssignLimits(uint8_t idx)
{
  const uint8_t id = SERVOS[idx];
  if (USE_MANUAL_LIMITS[idx]) {
    minPosArr[idx] = deg2t(MANUAL_MIN[idx]);
    maxPosArr[idx] = deg2t(MANUAL_MAX[idx]);
    DEBUG_SERIAL.printf("[INFO] Servo %d (%s) manual min=%.1f max=%.1f\n",
                        id, SERVO_NAMES[idx], MANUAL_MIN[idx], MANUAL_MAX[idx]);
  } else {
    DEBUG_SERIAL.printf("[CAL]  Servo %d (%s) auto-calibrating…\n",
                        id, SERVO_NAMES[idx]);
    dxl.torqueOff(id);
    dxl.setOperatingMode(id, OP_EXTENDED_POSITION);
    dxl.writeControlTableItem(PROFILE_VELOCITY, id, deg2t(VELOCITY_DEG_S));
    dxl.torqueOn(id);

    const int32_t center = dxl.getPresentPosition(id);
    minPosArr[idx] = findLimit(id, -1);
    maxPosArr[idx] = findLimit(id,  1);

    DEBUG_SERIAL.printf("[CAL]  min=%.1f°, max=%.1f°\n",
                        t2deg(minPosArr[idx]), t2deg(maxPosArr[idx]));

    dxl.setGoalPosition(id, center);                // return to centre
    while (dxl.readControlTableItem(MOVING, id));
  }
}

bool dryRun = true;      // becomes false after successful handshake

void sendLimitsToCore2()
{
  DEBUG_SERIAL.println(F("[INFO] Sending min/max table"));
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    const float mn = t2deg(minPosArr[i]);
    const float mx = t2deg(maxPosArr[i]);

    /* CSV chunk:  id,min,max; */
    Serial2.print(SERVOS[i]); Serial2.print(",");
    Serial2.print(mn, 1);     Serial2.print(",");
    Serial2.print(mx, 1);
    if (i < NUM_SERVOS - 1) Serial2.print(";");
  }
  Serial2.println();
}

/* ————— command from Core-2: MOVE_SERVO;ID=3;TARGET=45;VELOCITY=5; ————— */
void handleMoveServoCommand(const String& cmd)
{
  int id = cmd.substring(cmd.indexOf("ID=") + 3,
                         cmd.indexOf(';', cmd.indexOf("ID="))).toInt();
  float tgt = cmd.substring(cmd.indexOf("TARGET=") + 7,
                            cmd.indexOf(';', cmd.indexOf("TARGET="))).toFloat();
  float vel = cmd.substring(cmd.indexOf("VELOCITY=") + 9,
                            cmd.lastIndexOf(';')).toFloat();

  if (id < 0 || id >= NUM_SERVOS) {
    DEBUG_SERIAL.println(F("[ERR] Bad ID"));
    return;
  }
  tgt = constrain(tgt, t2deg(minPosArr[id]), t2deg(maxPosArr[id]));
  dxl.writeControlTableItem(PROFILE_VELOCITY, id, deg2t(vel));
  dxl.setGoalPosition(id, deg2t(tgt));

  DEBUG_SERIAL.printf("[ACT] Servo %d → %.1f° @ %.1f deg/s\n", id, tgt, vel);
}

/* ========================================================================== */
/*                                   SETUP                                    */
/* ========================================================================== */
void setup()
{
  DEBUG_SERIAL.begin(115200);
  DEBUG_SERIAL.println(F("\n[BOOT] OpenRB-150"));

  /* power up Dynamixel bus */
  pinMode(DXL_PWR_EN, OUTPUT);
  digitalWrite(DXL_PWR_EN, HIGH);

  dxl.begin(DXL_BAUD);
  dxl.setPortProtocolVersion(DXL_PROTOCOL);

  /* link to Core-2 */
  Serial2.begin(LINK_BAUD);

  /* handshake */
  Serial2.println("HELLO");
  unsigned long t0 = millis();
  while (millis() - t0 < 500) {
    if (Serial2.available() && Serial2.find("ESP32")) {
      dryRun = false;
      DEBUG_SERIAL.println(F("[INFO] Core-2 detected"));
      break;
    }
  }
  if (dryRun) DEBUG_SERIAL.println(F("[WARN] No Core-2 response → dry-run"));

  /* servo discovery + calibration */
  for (uint8_t i = 0; i < NUM_SERVOS; ++i) {
    const uint8_t id = SERVOS[i];
    DEBUG_SERIAL.printf("[PING] ID %d (%s)… ", id, SERVO_NAMES[i]);
    if (!dxl.ping(id)) {
      DEBUG_SERIAL.println("❌ not found, limits = 0");
      minPosArr[i] = maxPosArr[i] = 0;
      continue;
    }
    DEBUG_SERIAL.println("✅");
    calibrateOrAssignLimits(i);
  }
  printAllServoStatus();
  if (!dryRun) sendLimitsToCore2();
  DEBUG_SERIAL.println(F("[INFO] Calibration complete"));
}

/* ========================================================================== */
/*                                    LOOP                                    */
/* ========================================================================== */
void loop()
{
  /* listen for commands */
  if (!dryRun && Serial2.available()) {
    String msg = Serial2.readStringUntil('\n');
    msg.trim();
    if (msg.startsWith("MOVE_SERVO")) handleMoveServoCommand(msg);
  }

  /* demo sweep on servo 0 — two cycles then idle */
  static int cycles = 0;
  static bool sweeping = true;
  const uint8_t demoIdx = 0, demoID = SERVOS[demoIdx];

  if (sweeping && cycles < 2) {
    dxl.setGoalPosition(demoID, minPosArr[demoIdx]);
    while (dxl.readControlTableItem(MOVING, demoID));
    delay(SWEEP_DELAY_MS);

    dxl.setGoalPosition(demoID, maxPosArr[demoIdx]);
    while (dxl.readControlTableItem(MOVING, demoID));
    delay(SWEEP_DELAY_MS);

    cycles++;
  } else if (sweeping) {
    dxl.writeControlTableItem(LED, demoID, 1);     // red LED
    dxl.torqueOff(demoID);
    DEBUG_SERIAL.println(F("[DONE] Demo sweep finished"));
    sweeping = false;
  }
}
