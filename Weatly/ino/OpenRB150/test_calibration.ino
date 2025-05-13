/******************************************************************************
 *  OpenRB-150 • DYNAMIXEL range-calibration demo
 *  ───────────────────────────────────────────────────────────────────────────
 *  Works on any Protocol-2.0 DYNAMIXEL that supports Extended-Position mode.
 *  Finds mechanical min / max by “creeping” until the shaft stalls.
 *  Falls back to ±30° if no stop is detected within one turn.
 ******************************************************************************/

 #include <Dynamixel2Arduino.h>

 /* ──────────────────────────  OPENRB-150 PORT MAP  ─────────────────────────
    • Serial1   → four on-board TTL DYNAMIXEL ports (half-duplex, 5 V / 12 V)
    • Serial    → USB-C console
    • BDPIN_DXL_PWR_EN (pin 31) controls the FET that *enables* DYNAMIXEL power.
      The FET is OFF at reset, so every sketch that wants to move a servo
      must turn it ON first. :contentReference[oaicite:1]{index=1}                                                   */
 #define DXL_SERIAL      Serial1      // hardware UART wired to the 3-pin ports
 #define DEBUG_SERIAL    Serial       // USB-C console
 const int DXL_DIR_PIN  = -1;         // no direction pin required on OpenRB-150
 const int DXL_PWR_EN   = BDPIN_DXL_PWR_EN;   // board-defined macro (31)
 
 /* ───── USER SETTINGS ─────*/
 const uint8_t SERVOS[] = {3, 4};           // change to match your IDs
 const uint8_t NUM      = sizeof(SERVOS) / sizeof(SERVOS[0]);
 
 const uint32_t BAUD  = 57600;              // must match the servo(s)
 const float    PROTO = 2.0;
 
 /* ───── CALIBRATION CONSTANTS ─────*/
 const float STEP_DEG      = 2.0f;          // creep step
 const int   MAX_SWEEP_DEG = 720;           // search span on each side
 const float FALLBACK_DEG  = 30.0f;         // default half-range
 const int   WAIT_MS       = 500;           // settle delay
 
 /* ───── MODEL-SPECIFIC RESOLUTION ─────*/
 const float DEG_PER_TICK  = 360.0f / 4096.0f;
 
 Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);
 using namespace ControlTableItem;          // pull in register symbols
 
 /* ───── helper: degrees ↔ ticks ─────*/
 inline int32_t deg2t(float d) { return int32_t(d / DEG_PER_TICK + 0.5f); }
 inline float   t2deg(int32_t t){ return t * DEG_PER_TICK; }
 
 /* ───── stall-detect scan (dir = ±1) ─────*/
 int32_t findLimit(uint8_t id, int dir)
 {
   const int32_t STEP = deg2t(STEP_DEG) * dir;
   const int     MAX  = MAX_SWEEP_DEG / STEP_DEG;
 
   int32_t last = dxl.getPresentPosition(id);
 
   for (int i = 0; i < MAX; ++i)
   {
     dxl.setGoalPosition(id, last + STEP);
     delay(WAIT_MS);
     int32_t now = dxl.getPresentPosition(id);
 
     if (abs(now - last) < abs(STEP) / 2)   // moved <½ step ⇒ hit stop
       return now;
 
     last = now;
   }
   return INT32_MIN;                        // stop not detected
 }
 
 /* ───── calibrate one servo ─────*/
 void calibrate(uint8_t id)
 {
   DEBUG_SERIAL.print("\nCalibrating ID "); DEBUG_SERIAL.println(id);
 
   dxl.torqueOff(id);                       // EEPROM writes need torque off
   dxl.setOperatingMode(id, OP_EXTENDED_POSITION);
   dxl.torqueOn(id);
 
   int32_t center = dxl.getPresentPosition(id);
   int32_t minPos = findLimit(id, -1);
   int32_t maxPos = findLimit(id,  1);
 
   if (minPos == INT32_MIN || maxPos == INT32_MIN)
   {
     int32_t half = deg2t(FALLBACK_DEG);
     minPos = center - half;
     maxPos = center + half;
     DEBUG_SERIAL.println("⚠️  stop not detected – using default ±30°");
   }
 
   DEBUG_SERIAL.print("→ min = ");
   DEBUG_SERIAL.print(t2deg(minPos), 1);
   DEBUG_SERIAL.print("°, max = ");
   DEBUG_SERIAL.print(t2deg(maxPos), 1);
   DEBUG_SERIAL.println("°");
 
   /* Park, relax, LED on */
   dxl.setGoalPosition(id, (minPos + maxPos) / 2);
   while (dxl.isMoving(id)) ;
   dxl.torqueOff(id);
   dxl.setLED(id, 1);
 }
 
 /* ───── Arduino life-cycle ─────*/
 void setup()
 {
   /* 1 – bring up serial ports */
   DEBUG_SERIAL.begin(115200);
   dxl.begin(BAUD);
   dxl.setPortProtocolVersion(PROTO);
 
   /* 2 – enable 5 V / 12 V to the servo ports */
   pinMode(DXL_PWR_EN, OUTPUT);
   digitalWrite(DXL_PWR_EN, HIGH);          // FET ON → “DXL” LED lights
 
   /* 3 – walk through every ID in the list */
   for (uint8_t i = 0; i < NUM; ++i)
   {
     uint8_t id = SERVOS[i];
     if (!dxl.ping(id))
     {
       DEBUG_SERIAL.print("❌  ID "); DEBUG_SERIAL.print(id);
       DEBUG_SERIAL.println(" not responding.");
       continue;
     }
     calibrate(id);
   }
 
   DEBUG_SERIAL.println("\n--- calibration pass complete ---");
 }
 
 void loop() { /* nothing to do */ }
 