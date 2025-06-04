/******************************************************************************
 *  Core-2 touch UI for 7-servo head • talks to OpenRB-150 on UART2
 *  fixed: 2025-05-21  (early “ESP32” handshake)
 ******************************************************************************/

#include <M5Unified.h>
#include <HardwareSerial.h>
#include <Adafruit_NeoPixel.h>

HardwareSerial OpenRB(2);                  // use ESP32 UART2

// UART2 pin assignments for Grove Port-C
constexpr int RX2_PIN = 13;                // Grove Port-C white
constexpr int TX2_PIN = 14;                // Grove Port-C yellow
constexpr uint32_t LINK_BAUD = 115200;     // UART2 baud rate (must match OpenRB)

/* --- NeoPixel LED setup --- */
#define LED_PIN 21           // GPIO pin for WS2812B data line
#define NUM_LEDS 8           // Number of LEDs in the strip (adjust as needed)
Adafruit_NeoPixel leds(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

/* ──────────────────────────────────────────────────────────────────────────
 *  VARIABLE & CONSTANT REFERENCE
 *  (reflects only how the sketch itself uses each symbol)
 *  ------------------------------------------------------------------------
 *  Communication
 *      OpenRB(2)            – HardwareSerial bound to UART2.
 *      RX2_PIN, TX2_PIN     – GPIOs for UART2 RX/TX.
 *      LINK_BAUD            – Baud rate used in OpenRB.begin().
 *
 *  Servo bookkeeping
 *      totalServos          – Upper bound of the scroll list.
 *      activeServos         – Highest servo index that can be commanded
 *                              (0‥activeServos-1).
 *
 *      struct ServoState
 *          angle               Current target angle (deg).
 *          initial_angle       Angle used as center for idle jitter.
 *          velocity            Value forwarded in MOVE_SERVO ;VELOCITY=.
 *          min_angle,max_angle Safety limits; overwritten by calibration.
 *          idle_range          ±amplitude allowed during idle jitter (deg).
 *          lastIdleUpdate      millis() timestamp of last idle move.
 *          idleUpdateInterval  Base delay (ms) between idle moves; a random
 *                              0‥1000 ms is added each cycle.
 *
 *      servos[]             – Startup defaults for each controllable servo.
 *      SERVO_NAMES[]        – Labels printed in the UI.
 *
 *  UI layout
 *      lineHeight, yOffset, visibleRows  – Geometry of the scrolling list.
 *      GREY                – 16-bit colour for disabled rows.
 *      selected            – Index of highlighted row.
 *      scrollOffset        – First row index currently visible.
 *
 *  Runtime flags
 *      dryRun              – Starts true; no servo commands are sent until
 *                             a successful handshake + calibration.
 *      servoPingResult[]   – One bool per servo; filled by calibration.
 *      calibrationReceived – Blocks UI interaction until first calibration.
 * ──────────────────────────────────────────────────────────────────────────*/

/* ---------------- Servo State ---------------- */
constexpr int totalServos  = 11;           // Number of lines in UI
constexpr int activeServos = 7;            // 0…6 controllable servos

// Structure to hold servo state and config
struct ServoState {
  int angle, initial_angle, velocity;
  int min_angle, max_angle, idle_range;
  unsigned long lastIdleUpdate, idleUpdateInterval;
};

// Initial values for each servo
// - angle: Current target angle (deg)
// - initial_angle: Angle used as center for idle jitter
// - velocity: Value forwarded in MOVE_SERVO ;VELOCITY=
// - min_angle, max_angle: Safety limits; overwritten by calibration
// - idle_range: ±amplitude allowed during idle jitter (deg)
// - lastIdleUpdate: millis() timestamp of last idle move
// - idleUpdateInterval: Base delay (ms) between idle moves; a random 0‥1000 ms is added each cycle
ServoState servos[activeServos] = {
  {  0,  0, 5,   0,   0,700,0,2000},   // lens
  {200,200, 5,  30,  60,40,0,2000},   // eyelid1
  {200,200, 5,  30,  60,40,0,2000},   // eyelid2
  {130,220, 5,  45, 135,90,0,2000},   // eyeX
  {120,120, 5,  40, 140,80,0,2000},   // eyeY
  {150,150, 5,   0, 170,10,0,2000},   // handle1
  {170,170, 5,   0, 170,10,0,2000}    // handle2
};

const char* SERVO_NAMES[activeServos] = {
  "lens","eyelid1","eyelid2","eyeX","eyeY","handle1","handle2"
};

/* ---------------- UI Layout ---------------- */
constexpr int lineHeight  = 30;            // Height of each row in UI
constexpr int yOffset     = 20;            // Top margin
constexpr int visibleRows = 7;             // Number of rows visible at once
constexpr uint16_t GREY = 0x7BEF;          // Color for disabled servos

int selected     = 0;                      // Currently selected servo
int scrollOffset = 0;                      // Scroll position in UI

// dryRun: If true, disables all servo actions and UI (set if handshake/calibration fails)
bool dryRun = true; 
// servoPingResult: For each servo, true if OpenRB found it, false if not
bool servoPingResult[activeServos] = {false}; 
// calibrationReceived: Only allow UI and servo commands after calibration is received
bool calibrationReceived = false; 

/* ---------------- UI Drawing Helpers ---------------- */
// Draw a single line (servo row) in the UI
// - If servo is dead (not found by OpenRB), draw in red
// - If selected, highlight background
void drawLine(int i, int y)
{
  bool isSel = (i == selected);
  bool isDead = (i < activeServos && !servoPingResult[i]);
  uint16_t bg = isSel ? BLUE : BLACK;
  uint16_t fg = isDead ? RED : (isSel ? WHITE : WHITE);
  M5.Lcd.fillRect(0, y, M5.Lcd.width(), lineHeight, bg);
  M5.Lcd.setCursor(10, y + 4);
  if (i < activeServos) {
    M5.Lcd.setTextColor(fg, bg);
    M5.Lcd.printf("%d: %3d V:%d I:%d F:%lu",
                  i, servos[i].angle, servos[i].velocity,
                  servos[i].idle_range, servos[i].idleUpdateInterval);
  } else {
    M5.Lcd.setTextColor(GREY, BLACK);
    M5.Lcd.printf("Servo %d: disabled", i);
  }
}

// Draw the entire visible window of servo rows
void drawWindow()
{
  M5.Lcd.fillScreen(BLACK);
  for (int row = 0; row < visibleRows; ++row) {
    int i = scrollOffset + row;
    if (i >= totalServos) break;
    drawLine(i, yOffset + row * lineHeight);
  }
}

// Redraw a single servo row (if visible)
void drawSingle(int i)
{
  int row = i - scrollOffset;
  if (row < 0 || row >= visibleRows) return;
  drawLine(i, yOffset + row * lineHeight);
}

// Blink the screen background and LEDs a given number of times (handshake feedback)
void blinkScreen(int times) {
  for (int i = 0; i < times; ++i) {
    // Blink screen to RED and LEDs to RED
    M5.Lcd.fillScreen(RED);
    for (int j = 0; j < NUM_LEDS; ++j) {
      leds.setPixelColor(j, leds.Color(255, 0, 0));
    }
    leds.show();
    delay(150);
    
    // Turn off screen and LEDs
    M5.Lcd.fillScreen(BLACK);
    for (int j = 0; j < NUM_LEDS; ++j) {
      leds.setPixelColor(j, 0);
    }
    leds.show();
    delay(150);
  }
  drawWindow();
}

/* ---------------- UART Helpers ---------------- */
// Send a MOVE_SERVO command to OpenRB
void sendMoveServoCommand(int id, int tgt, int vel)
{
  String cmd = "MOVE_SERVO;ID=" + String(id) +
               ";TARGET="  + String(tgt) +
               ";VELOCITY="+ String(vel) + ";\n";
  OpenRB.print(cmd);
  Serial.printf("[→RB] %s", cmd.c_str());
}

// Parse calibration data from OpenRB and update servo limits and ping
// Format: id,min,max,ping;id,min,max,ping;...
//   id   = servo ID
//   min  = min angle (deg)
//   max  = max angle (deg)
//   ping = 1 if found, 0 if not found
void handleCalibrationData(const String& line)
{
  int last = 0;
  int servoIndex = 0;
  while (last < line.length() && servoIndex < activeServos) {
    int semicolonIndex = line.indexOf(';', last);
    String servoConfigChunk = (semicolonIndex == -1) ? line.substring(last)
                                                    : line.substring(last, semicolonIndex);
    int idComma = servoConfigChunk.indexOf(',');
    int minComma = servoConfigChunk.indexOf(',', idComma + 1);
    int maxComma = servoConfigChunk.indexOf(',', minComma + 1);
    if (idComma > 0 && minComma > idComma && maxComma > minComma) {
      int servoId = servoConfigChunk.substring(0, idComma).toInt();
      float minAngle = servoConfigChunk.substring(idComma + 1, minComma).toFloat();
      float maxAngle = servoConfigChunk.substring(minComma + 1, maxComma).toFloat();
      int pingStatus = servoConfigChunk.substring(maxComma + 1).toInt();
      if (servoId >= 0 && servoId < activeServos) {
        servos[servoId].min_angle = round(minAngle);
        servos[servoId].max_angle = round(maxAngle);
        servos[servoId].angle     = constrain(servos[servoId].angle, servos[servoId].min_angle, servos[servoId].max_angle);
        servos[servoId].initial_angle = servos[servoId].angle;
        servoPingResult[servoId] = (pingStatus == 1);
      }
    }
    if (semicolonIndex == -1) break;
    last = semicolonIndex + 1;
    servoIndex++;
  }
  calibrationReceived = true;
  dryRun = false;
  drawWindow();
  Serial.println("[OK] Calibration table updated");
  // --- NEW: Forward calibration data to USB serial for Python ---
  Serial.print("SERVO_CONFIG:");
  Serial.println(line); // Send the raw calibration string prefixed for Python to parse
}

// Print any other command received from OpenRB
void handleSerialCommand(const String& cmd)
{
  Serial.printf("[RB>] %s\n", cmd.c_str());
}

/* ─── NEW: helper that emits current table exactly like the
 *          one we forward after a fresh calibration ─── */
void sendServoConfig()
{
  Serial.print("SERVO_CONFIG:");
  for (int i = 0; i < activeServos; ++i) {
    Serial.print(i);                       // id
    Serial.print(',');  Serial.print(servos[i].min_angle);
    Serial.print(',');  Serial.print(servos[i].max_angle);
    Serial.print(',');  Serial.print(servoPingResult[i] ? 1 : 0); // ping
    if (i < activeServos - 1) Serial.print(';');
  }
  Serial.println();
}


// handleLink: Poll robot UART for messages and handle handshake, calibration, or commands
// - On HELLO: respond, blink screen
// - On calibration: update state, enable UI
// - On other: print debug
void handleLink()
{
  while (OpenRB.available()) {
    String msg = OpenRB.readStringUntil('\n');
    msg.trim();

    if (msg.startsWith("HELLO")) {
      OpenRB.println("ESP32");
      Serial.printf("[<RB] %s\n", msg.c_str());
      blinkScreen(3); // Blink screen 3 times on handshake
    } else if (msg.indexOf(',') > 0 && msg.indexOf(';') > 0) {
      handleCalibrationData(msg); // Servo calibration data
    } else if (msg.length()) {
      handleSerialCommand(msg);   // Other commands
    }
  }
}

/* ===================================================================== */
/*                               SETUP                                   */
/* ===================================================================== */
// setup: Main setup sequence
// 1. Start M5Stack and UART
// 2. Draw initial UI
// 3. Attempt handshake (send ESP32)
// 4. Wait for calibration before enabling UI
void setup()
{
  auto cfg = M5.config();
  M5.begin(cfg);                        // Initialize M5Stack Core2

  Serial.begin(115200);                 // USB debug
  OpenRB.begin(LINK_BAUD, SERIAL_8N1, RX2_PIN, TX2_PIN); // UART2

  // --- Initialize NeoPixel LEDs ---
  leds.begin();
  // Set all LEDs to white at startup
  for (int i = 0; i < NUM_LEDS; ++i) {
    leds.setPixelColor(i, leds.Color(255, 255, 255));
  }
  leds.show();

  M5.Lcd.setTextSize(2);
  drawWindow();                         // Draw initial UI

  /* ───── proactive handshake (in case we boot first) ───── */
  OpenRB.println("ESP32");
}

/* ===================================================================== */
/*                                LOOP                                   */
/* ===================================================================== */
// loop: Main loop
// - Only allow UI and servo commands after calibration is received
// - Skip dead servos in idle animation and button logic
void loop()
{
  M5.update();         // Update button and touch state
  handleLink();        // Handle UART messages

  // --- Forward commands from USB Serial to OpenRB UART2 and handle config commands ---
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      // Handle direct LED color command from Python
      if (cmd.startsWith("SET_LED;")) {
        int r = 0, g = 0, b = 0;
        int rIdx = cmd.indexOf("R=");
        int gIdx = cmd.indexOf("G=");
        int bIdx = cmd.indexOf("B=");
        if (rIdx >= 0) r = cmd.substring(rIdx + 2, cmd.indexOf(';', rIdx + 2)).toInt();
        if (gIdx >= 0) g = cmd.substring(gIdx + 2, cmd.indexOf(';', gIdx + 2)).toInt();
        if (bIdx >= 0) {
          int bEnd = cmd.indexOf(';', bIdx + 2);
          if (bEnd == -1) bEnd = cmd.length();
          b = cmd.substring(bIdx + 2, bEnd).toInt();
        }
        uint32_t color = leds.Color(r, g, b);
        for (int i = 0; i < NUM_LEDS; ++i) {
          leds.setPixelColor(i, color);
        }
        leds.show();
        Serial.printf("[LED] Set color to R=%d G=%d B=%d\n", r, g, b);
      }
      // Check for configuration command
      else if (cmd.startsWith("SET_SERVO_CONFIG:")) {
        // Format: SET_SERVO_CONFIG:id,target,vel,idle_range,interval;id,target,vel,idle_range,interval;...
        int configStartIndex = String("SET_SERVO_CONFIG:").length();
        int servoIndex = 0;
        while (configStartIndex < cmd.length() && servoIndex < activeServos) {
          int semicolonIndex = cmd.indexOf(';', configStartIndex);
          String servoConfigChunk = (semicolonIndex == -1) ? cmd.substring(configStartIndex) : cmd.substring(configStartIndex, semicolonIndex);
          // Parse comma-separated fields for servo config (id,target,vel,idle_range,interval)
          int idComma = servoConfigChunk.indexOf(',');
          int tgtComma = servoConfigChunk.indexOf(',', idComma + 1);
          int velComma = servoConfigChunk.indexOf(',', tgtComma + 1);
          int idleComma = servoConfigChunk.indexOf(',', velComma + 1);
          if (idComma > 0 && tgtComma > idComma && velComma > tgtComma && idleComma > velComma) {
            int servoId = servoConfigChunk.substring(0, idComma).toInt();
            int target = servoConfigChunk.substring(idComma + 1, tgtComma).toInt();
            int velocity = servoConfigChunk.substring(tgtComma + 1, velComma).toInt();
            int idleRange = servoConfigChunk.substring(velComma + 1, idleComma).toInt();
            unsigned long interval = servoConfigChunk.substring(idleComma + 1).toInt();
            if (servoId >= 0 && servoId < activeServos) {
              servos[servoId].angle = constrain(target, servos[servoId].min_angle, servos[servoId].max_angle);
              servos[servoId].initial_angle = servos[servoId].angle;
              servos[servoId].velocity = velocity;
              servos[servoId].idle_range = idleRange;
              servos[servoId].idleUpdateInterval = interval;
            }
          }
          if (semicolonIndex == -1) break;
          configStartIndex = semicolonIndex + 1;
          servoIndex++;
        }
        Serial.println("[OK] Servo config updated from USB");
        drawWindow();
      } else if (cmd == "GET_SERVO_CONFIG") {      // ← NEW
        sendServoConfig();                       // answer Python
      } else {
        // Forward any other command to OpenRB
        OpenRB.println(cmd);
        Serial.printf("[→RB] (from USB) %s\n", cmd.c_str());
      }
    }
  }

  // Only allow UI and servo commands after calibration is received
  if (!calibrationReceived) {
    delay(33);
    return;
  }

  /* --- idle animation: random servo movement when idle --- */
  for (int i = 0; i < activeServos; ++i) {
    if (!servoPingResult[i]) continue;           // Skip dead servos

    ServoState& s = servos[i];
    unsigned long now = millis();

    if (s.idle_range > 0 &&
        now - s.lastIdleUpdate >
            s.idleUpdateInterval + random(0, 1000)) {

      // Compute legal idle window
      int minIdle = max(s.min_angle, s.initial_angle - s.idle_range);
      int maxIdle = min(s.max_angle, s.initial_angle + s.idle_range);

      if (minIdle < maxIdle) {                   // Valid window exists
        int newAngle;

        /* -------- NEW LOGIC --------
         * Always pick a value inside [minIdle,maxIdle] that
         * differs from the current angle.  Up to 10 attempts,
         * then fall back to current angle if window is a single step.
         */
        for (int tries = 0; tries < 10; ++tries) {
          newAngle = random(minIdle, maxIdle + 1);   // inclusive range
          if (newAngle != s.angle) break;
        }

        if (newAngle != s.angle) {               // Move only if changed
          s.angle = newAngle;
          drawSingle(i);
          sendMoveServoCommand(i, s.angle, s.velocity);
        }
      }
      s.lastIdleUpdate = now;
    }
  }

  /* --- buttons: left (A) / centre (B) / right (C) --- */
  if (M5.BtnA.isPressed() && selected < activeServos && servoPingResult[selected]) {
    if (servos[selected].angle > servos[selected].min_angle) {
      --servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle,
                                          servos[selected].velocity);
    }
  }
  if (M5.BtnB.isPressed() && selected < activeServos && servoPingResult[selected]) {
    if (servos[selected].angle < servos[selected].max_angle) {
      ++servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle,
                                          servos[selected].velocity);
    }
  }
  if (M5.BtnC.wasPressed()) {
    int old = selected;
    // Only select next working servo
    int next = selected;
    for (int tries = 0; tries < activeServos; ++tries) {
      next = (next + 1) % activeServos;
      if (servoPingResult[next]) {
        selected = next;
        drawSingle(selected);
        break;
      }
      // Wrap around: If all servos are dead, just reset selection
      if (tries == activeServos - 1) {
        selected = 0;
        drawSingle(selected);
      }
    }
  }

  delay(33); // Prevent watchdog reset; tune based on button debounce and UI refresh needs
}
