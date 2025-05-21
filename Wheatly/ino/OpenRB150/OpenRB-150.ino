/******************************************************************************
 *  OpenRB-150  ⇄  Core-2 UART bridge + multi-servo calibration demo
 *  fixed: 2025-05-21  (10 s handshake & servo-torque tweak)
 ******************************************************************************/

#include <Arduino.h>
#include <Dynamixel2Arduino.h>
#include <stdarg.h>               // for vsnprintf

/* --------------------------------------------------------------------------
 *  Serial alias (define this *first* so helpers can use it)
 * --------------------------------------------------------------------------*/
#define DEBUG_SERIAL  Serial

/* --------------------------------------------------------------------------
 *  printf-compat layer – works on every core
 * --------------------------------------------------------------------------*/
#ifndef PRINT_HAS_PRINTF
  #if defined(ARDUINO_ARCH_ESP32) || defined(ARDUINO_ARCH_STM32)
    #define PRINT_HAS_PRINTF  1
  #else
    #define PRINT_HAS_PRINTF  0
  #endif
#endif

#if PRINT_HAS_PRINTF
  #define DBG_PRINTF(...)  DEBUG_SERIAL.printf(__VA_ARGS__)
#else
  inline void dbgPrintf(const char *fmt, ...)
  {
    char buf[128];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    DEBUG_SERIAL.print(buf);
  }
  #define DBG_PRINTF(...)  dbgPrintf(__VA_ARGS__)
#endif

/* ————— DYNAMIXEL BUS ————— */
#define DXL_SERIAL   Serial1
const int  DXL_DIR_PIN  = -1;
const int  DXL_PWR_EN   = BDPIN_DXL_PWR_EN;
const uint32_t DXL_BAUD = 57600;
const float     DXL_PROTOCOL = 2.0;

/* ————— CORE-2 LINK ————— */
const uint32_t LINK_BAUD = 115200;
#define HANDSHAKE_TIMEOUT_MS 10000        // keep trying for 10 s

/* ————— CALIBRATION SETTINGS ————— */
const float STEP_DEG        = 15.0f;
const int   WAIT_MS         = 500;
const float STALL_THRESHOLD = 0.20f;
const float VELOCITY_DEG_S  = 10.0f;
const int   SWEEP_DELAY_MS  = 5000;

/* ————— Angle ↔︎ Tick helpers ————— */
constexpr float DEG_PER_TICK = 360.0f / 4096.0f;
inline int32_t deg2t(float d)  { return int32_t(d / DEG_PER_TICK + 0.5f); }
inline float   t2deg(int32_t t){ return t * DEG_PER_TICK; }

Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);
using namespace ControlTableItem;

/* -------------------- SERVO TABLE -------------------- */
#define NUM_SERVOS 7
const uint8_t SERVOS[NUM_SERVOS] = {0,1,2,3,4,5,6};
const char* SERVO_NAMES[NUM_SERVOS] = {
  "lens","eyelid1","eyelid2","eyeX","eyeY","handle1","handle2"
};
const bool  USE_MANUAL_LIMITS[NUM_SERVOS] = {true,false,true,false,false,true,false};
const float MANUAL_MIN[NUM_SERVOS]        = {-90,0,-45,0,0,-60,0};
const float MANUAL_MAX[NUM_SERVOS]        = { 90,0, 45,0,0, 60,0};

int32_t minPosArr[NUM_SERVOS];
int32_t maxPosArr[NUM_SERVOS];

/* ------------- helper routines ------------- */
int32_t findLimit(uint8_t id,int dir)
{
  const int32_t step = deg2t(STEP_DEG)*dir;
  int32_t last = dxl.getPresentPosition(id);
  while (true) {
    dxl.setGoalPosition(id,last+step);
    while (dxl.readControlTableItem(MOVING,id));
    delay(WAIT_MS);
    int32_t now = dxl.getPresentPosition(id);
    if (abs(now-last) < abs(step)*STALL_THRESHOLD) return last;
    last = now;
  }
}

void printAllServoStatus()
{
  DEBUG_SERIAL.println(F("\nID\tName\t\tMin°\tMax°\tCurrent°"));
  for (uint8_t i=0;i<NUM_SERVOS;++i) {
    float cur = dxl.ping(SERVOS[i])? t2deg(dxl.getPresentPosition(SERVOS[i])):0;
    DBG_PRINTF("%d\t%-8s\t%5.1f\t%5.1f\t%5.1f\n",
               SERVOS[i],SERVO_NAMES[i],
               t2deg(minPosArr[i]),t2deg(maxPosArr[i]),cur);
  }
}

void calibrateOrAssignLimits(uint8_t idx)
{
  uint8_t id = SERVOS[idx];
  if (USE_MANUAL_LIMITS[idx]) {
    minPosArr[idx]=deg2t(MANUAL_MIN[idx]);
    maxPosArr[idx]=deg2t(MANUAL_MAX[idx]);
    DBG_PRINTF("[INFO] Servo %d (%s) manual min=%.1f max=%.1f\n",
               id,SERVO_NAMES[idx],MANUAL_MIN[idx],MANUAL_MAX[idx]);
  } else {
    DBG_PRINTF("[CAL]  Servo %d (%s) auto-calibrating…\n",id,SERVO_NAMES[idx]);
    dxl.torqueOff(id);
    dxl.setOperatingMode(id,OP_EXTENDED_POSITION);
    dxl.writeControlTableItem(PROFILE_VELOCITY,id,deg2t(VELOCITY_DEG_S));
    dxl.torqueOn(id);
    int32_t centre = dxl.getPresentPosition(id);
    minPosArr[idx] = findLimit(id,-1);
    maxPosArr[idx] = findLimit(id, 1);
    DBG_PRINTF("[CAL]  min=%.1f°, max=%.1f°\n",
               t2deg(minPosArr[idx]),t2deg(maxPosArr[idx]));
    dxl.setGoalPosition(id,centre);
    while (dxl.readControlTableItem(MOVING,id));
  }
}

/* ---------------- UART helpers ---------------- */
bool dryRun = true;

void sendLimitsToCore2()
{
  for (uint8_t i=0;i<NUM_SERVOS;++i){
    Serial2.print(SERVOS[i]); Serial2.print(',');
    Serial2.print(t2deg(minPosArr[i]),1); Serial2.print(',');
    Serial2.print(t2deg(maxPosArr[i]),1);
    if (i<NUM_SERVOS-1) Serial2.print(';');
  }
  Serial2.println();
}

void handleMoveServoCommand(const String& cmd)
{
  int id = cmd.substring(cmd.indexOf("ID=")+3,
                         cmd.indexOf(';',cmd.indexOf("ID="))).toInt();
  float tgt = cmd.substring(cmd.indexOf("TARGET=")+7,
                            cmd.indexOf(';',cmd.indexOf("TARGET="))).toFloat();
  float vel = cmd.substring(cmd.indexOf("VELOCITY=")+9,
                            cmd.lastIndexOf(';')).toFloat();
  if (id<0||id>=NUM_SERVOS){ DEBUG_SERIAL.println(F("[ERR] Bad ID")); return; }
  tgt = constrain(tgt,t2deg(minPosArr[id]),t2deg(maxPosArr[id]));
  dxl.writeControlTableItem(PROFILE_VELOCITY,id,deg2t(vel));
  dxl.setGoalPosition(id,deg2t(tgt));
  DBG_PRINTF("[ACT] Servo %d → %.1f° @ %.1f deg/s\n",id,tgt,vel);
}

void blinkOnboardLED(int times) {
  pinMode(LED_BUILTIN, OUTPUT);
  for (int i = 0; i < times; ++i) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(200);
    digitalWrite(LED_BUILTIN, LOW);
    delay(200);
  }
}

/* -------------------- SETUP -------------------- */
void setup()
{
  DEBUG_SERIAL.begin(115200);
  DEBUG_SERIAL.println(F("\n[BOOT] OpenRB-150"));

  pinMode(DXL_PWR_EN,OUTPUT);
  digitalWrite(DXL_PWR_EN,HIGH);

  dxl.begin(DXL_BAUD);
  dxl.setPortProtocolVersion(DXL_PROTOCOL);

  Serial2.begin(LINK_BAUD);

  /* ───── 10 s bidirectional handshake ───── */
  unsigned long start = millis();
  while (millis() - start < HANDSHAKE_TIMEOUT_MS) {
    Serial2.println("HELLO");                     // announce ourselves

    unsigned long sliceEnd = millis() + 300;      // short listen window
    while (millis() < sliceEnd) {
      if (Serial2.available() && Serial2.find("ESP32")) {
        dryRun = false;
        DEBUG_SERIAL.println(F("[INFO] Core-2 detected"));
        blinkOnboardLED(3); // Blink onboard LED 3 times on handshake
        break;
      }
    }
    if (!dryRun) break;                           // success
  }
  if (dryRun) DEBUG_SERIAL.println(F("[WARN] No Core-2 response after 10 s ⇒ dry-run"));

  /* ───── probe & calibrate servos ───── */
  for (uint8_t i=0;i<NUM_SERVOS;++i){
    uint8_t id = SERVOS[i];
    DBG_PRINTF("[PING] ID %d (%s)… ",id,SERVO_NAMES[i]);
    if (!dxl.ping(id)){
      DEBUG_SERIAL.println("❌ not found, limits = 0");
      minPosArr[i]=maxPosArr[i]=0; continue;
    }
    DEBUG_SERIAL.println("✅");
    calibrateOrAssignLimits(i);
    dxl.torqueOn(id);            // ensure torque for demo
  }

  printAllServoStatus();
  if (!dryRun) sendLimitsToCore2();
}

/* --------------------- LOOP --------------------- */
void loop()
{
  if (!dryRun && Serial2.available()){
    String msg = Serial2.readStringUntil('\n'); msg.trim();
    if (msg.startsWith("MOVE_SERVO")) handleMoveServoCommand(msg);
  }

  static int cycles=0; static bool sweeping=true;
  const uint8_t demoIdx=0, demoID=SERVOS[demoIdx];

  if (sweeping) dxl.torqueOn(demoID);   // keep powered

  if (sweeping && cycles<2){
    dxl.setGoalPosition(demoID,minPosArr[demoIdx]);
    while (dxl.readControlTableItem(MOVING,demoID)); delay(SWEEP_DELAY_MS);
    dxl.setGoalPosition(demoID,maxPosArr[demoIdx]);
    while (dxl.readControlTableItem(MOVING,demoID)); delay(SWEEP_DELAY_MS);
    cycles++;
  } else if (sweeping){
    dxl.writeControlTableItem(LED,demoID,1);
    dxl.torqueOff(demoID);
    DEBUG_SERIAL.println(F("[DONE] Demo sweep finished"));
    sweeping=false;
  }
}
