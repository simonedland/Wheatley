/******************************************************************************
 *  Core-2 touch UI for 7-servo head • talks to OpenRB-150 on UART2
 *  fixed: 2025-05-21  (early “ESP32” handshake)
 ******************************************************************************/

#include <M5Unified.h>
#include <HardwareSerial.h>
HardwareSerial OpenRB(2);                  // use ESP32 UART2

// UART2 pin assignments for Grove Port-C
constexpr int RX2_PIN = 13;                // Grove Port-C white
constexpr int TX2_PIN = 14;                // Grove Port-C yellow
constexpr uint32_t LINK_BAUD = 115200;     // UART2 baud rate (must match OpenRB)

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
ServoState servos[activeServos] = {
  {  0,  0, 5,-720, 720,10,0,2000},   // lens
  {200,200, 5,  30,  60,40,0,2000},   // eyelid1
  {200,200, 5,  30,  60,40,0,2000},   // eyelid2
  { 90, 90, 5,  45, 135,10,0,2000},   // eyeX
  {120,120, 5,  40, 140,10,0,2000},   // eyeY
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

// Blink the screen background a given number of times (handshake feedback)
void blinkScreen(int times) {
  for (int i = 0; i < times; ++i) {
    M5.Lcd.fillScreen(RED);
    delay(150);
    M5.Lcd.fillScreen(BLACK);
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
  int idx = 0;
  while (last < line.length() && idx < activeServos) {
    int next = line.indexOf(';', last);
    String chunk = (next == -1) ? line.substring(last)
                                : line.substring(last, next);
    int c1 = chunk.indexOf(',');
    int c2 = chunk.indexOf(',', c1 + 1);
    int c3 = chunk.indexOf(',', c2 + 1);
    if (c1 > 0 && c2 > c1 && c3 > c2) {
      int id = chunk.substring(0, c1).toInt();
      float mn = chunk.substring(c1 + 1, c2).toFloat();
      float mx = chunk.substring(c2 + 1, c3).toFloat();
      int ping = chunk.substring(c3 + 1).toInt();
      if (id >= 0 && id < activeServos) {
        servos[id].min_angle = round(mn);
        servos[id].max_angle = round(mx);
        servos[id].angle     = constrain(servos[id].angle, servos[id].min_angle,
                                                       servos[id].max_angle);
        servos[id].initial_angle = servos[id].angle;
        servoPingResult[id] = (ping == 1);
      }
    }
    if (next == -1) break;
    last = next + 1;
    idx++;
  }
  calibrationReceived = true;
  dryRun = false;
  drawWindow();
  Serial.println("[OK] Calibration table updated");
}

// Print any other command received from OpenRB
void handleSerialCommand(const String& cmd)
{
  Serial.printf("[RB>] %s\n", cmd.c_str());
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
      if (servoPingResult[next]) break;
    }
    selected = next;
    if (selected < scrollOffset)                scrollOffset = selected;
    else if (selected >= scrollOffset + visibleRows)
                                                scrollOffset = selected - visibleRows + 1;

    if (scrollOffset == 0 ||
        selected == scrollOffset ||
        selected == scrollOffset + visibleRows - 1)
      drawWindow();
    else {
      drawSingle(old);
      drawSingle(selected);
    }
  }

  delay(33);          // ~30 FPS UI refresh
}
