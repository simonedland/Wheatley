/******************************************************************************
 *  Core-2 touch UI for 7-servo head  ·  talks to OpenRB-150 on UART2
 *  rev 2025-06-06  –  no clamping before calibration
 *
 *  ▸ Handshake timeout after 10 s enters demo-mode.
 *  ▸ “SERVO_CONFIG:id,min,max,ping;…” is forwarded to the USB host.
 *  ▸ Idle-jitter, scrolling list and RGB-LED demo exactly as before.
 ******************************************************************************/

#include <M5Unified.h>
#include <HardwareSerial.h>
#include <Adafruit_NeoPixel.h>

/* ---------- UART link to the OpenRB-150 ---------- */
HardwareSerial OpenRB(2);               // use ESP32 UART2
constexpr int RX2_PIN  = 13;            // Grove Port-C white
constexpr int TX2_PIN  = 14;            // Grove Port-C yellow
constexpr uint32_t LINK_BAUD = 115200;  // must match OpenRB

/* ---------- NeoPixel strip ---------- */
#define LED_PIN 21
#define NUM_LEDS 8
Adafruit_NeoPixel leds(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// LED index used to display microphone status
constexpr int MIC_LED_INDEX = 17;

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
  {  0,  0, 5,    0,   0,700,0,2000},   // lens
  {180,180, 5,  180, 220,40,0,2000},   // eyelid1
  {180,180, 5,  140, 180,40,0,2000},   // eyelid2
  {130,130, 5,  130, 220,90,0,2000},   // eyeX
  {140,140, 5,  140, 210,80,0,2000},   // eyeY
  {0  ,0  , 5,  -60,  60,10,0,2000},   // handle1
  {0  ,0  , 5,  -60,  60,10,0,2000}    // handle2
};


const char* SERVO_NAMES[activeServos] = {
  "lens","eyelid1","eyelid2","eyeX","eyeY","handle1","handle2"
};

/* ---------- UI layout constants ---------- */
constexpr int lineHeight  = 30;
constexpr int yOffset     = 20;
constexpr int visibleRows = 7;
constexpr uint16_t GREY = 0x7BEF;

int selected     = 0;   // highlighted row
int scrollOffset = 0;   // first visible row

/* ---------- handshake / flags ---------- */
bool handshakeReceived   = false;
bool demoMode            = false;
unsigned long handshakeStart = 0;

bool dryRun              = true;   // mute until calibration
bool servoPingResult[activeServos] = {false};
bool calibrationReceived = false;

/* ---------------- UI Drawing Helpers ---------------- */
// Draw a single line (servo row) in the UI
// - If servo is dead (not found by OpenRB), draw in red
// - If selected, highlight background
void drawLine(int i, int y)
{
  bool sel  = (i == selected);
  bool dead = (i < activeServos && !servoPingResult[i]);

  uint16_t bg = sel ? BLUE  : BLACK;
  uint16_t fg = dead ? RED  : WHITE;
  if (demoMode && !sel) fg = BLUE;

  M5.Lcd.fillRect(0, y, M5.Lcd.width(), lineHeight, bg);
  M5.Lcd.setTextColor(fg, bg);
  M5.Lcd.setCursor(10, y + 4);

  if (i < activeServos) {
    const ServoState& s = servos[i];
    M5.Lcd.printf("%d: %3d V:%d I:%d F:%lu",
                  i, s.angle, s.velocity,
                  s.idle_range, s.idleUpdateInterval);
  } else {
    M5.Lcd.setTextColor(GREY, bg);
    M5.Lcd.printf("Servo %d: disabled", i);
  }
}
void drawWindow()
{
  M5.Lcd.fillScreen(BLACK);
  for (int row = 0; row < visibleRows; ++row) {
    int i = scrollOffset + row;
    if (i >= totalServos) break;
    drawLine(i, yOffset + row * lineHeight);
  }
}
void drawSingle(int i)
{
  int row = i - scrollOffset;
  if (row < 0 || row >= visibleRows) return;
  drawLine(i, yOffset + row * lineHeight);
}
void blinkScreen(int times)
{
  for (int i = 0; i < times; ++i) {
    M5.Lcd.fillScreen(RED);
    for (int j = 0; j < NUM_LEDS; ++j) leds.setPixelColor(j, leds.Color(255,0,0));
    leds.show(); delay(150);
    M5.Lcd.fillScreen(BLACK);
    for (int j = 0; j < NUM_LEDS; ++j) leds.setPixelColor(j,0);
    leds.show(); delay(150);
  }
  drawWindow();
}
void enterDemoMode()
{
  demoMode  = true;
  dryRun    = true;
  calibrationReceived = true;
  for (int i = 0; i < activeServos; ++i) servoPingResult[i] = true;
  Serial.println("[WARN] Handshake timeout – entering DEMO MODE");
  drawWindow();
}
/* ---------- UART helpers ---------- */
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
  while (last < line.length()) {
    int semi = line.indexOf(';', last);
    String chunk = (semi == -1) ? line.substring(last)
                                : line.substring(last, semi);

    int c1 = chunk.indexOf(','), c2 = chunk.indexOf(',', c1+1),
        c3 = chunk.indexOf(',', c2+1);
    if (c3 > c2 && c2 > c1 && c1 > 0) {
      int id   = chunk.substring(0,  c1).toInt();
      int mn   = round(chunk.substring(c1+1, c2).toFloat());
      int mx   = round(chunk.substring(c2+1, c3).toFloat());
      int ping = chunk.substring(c3+1).toInt();

      if (id >= 0 && id < activeServos) {
        ServoState& s = servos[id];
        s.min_angle = mn;
        s.max_angle = mx;
        s.angle     = constrain(s.angle, mn, mx);
        s.initial_angle = s.angle;
        servoPingResult[id] = (ping == 1);
      }
    }
    if (semi == -1) break;
    last = semi + 1;
  }

  calibrationReceived = true;
  dryRun = false;
  drawWindow();
  Serial.println("[OK] Calibration table updated");

  Serial.print("SERVO_CONFIG:");
  Serial.println(line);   // forward to USB host
}

/* ---------- helpers ---------- */
void sendServoConfig()
{
  Serial.print("SERVO_CONFIG:");
  for (int i = 0; i < activeServos; ++i) {
    Serial.printf("%d,%d,%d,%d",
                  i, servos[i].min_angle, servos[i].max_angle,
                  servoPingResult[i] ? 1 : 0);
    if (i < activeServos-1) Serial.print(';');
  }
  Serial.println();
}

/* ---------- link handler ---------- */
void handleLink()
{
  while (OpenRB.available()) {
    String msg = OpenRB.readStringUntil('\n');
    msg.trim();

    if (msg.startsWith("HELLO")) {
      handshakeReceived = true;
      OpenRB.println("ESP32");
      Serial.printf("[<RB] %s\n", msg.c_str());
      blinkScreen(3);
    }
    else if (msg.indexOf(',') > 0 && msg.indexOf(';') > 0) {
      handleCalibrationData(msg);
    }
    else if (msg.length()) {
      Serial.printf("[RB>] %s\n", msg.c_str());
    }
  }
}

/* ===================================================================== */
/*                                 SETUP                                 */
/* ===================================================================== */
// setup: Main setup sequence
// 1. Start M5Stack and UART
// 2. Draw initial UI
// 3. Attempt handshake (send ESP32)
// 4. Wait for calibration before enabling UI
void setup()
{
  auto cfg = M5.config();
  M5.begin(cfg);

  Serial.begin(115200);
  OpenRB.begin(LINK_BAUD, SERIAL_8N1, RX2_PIN, TX2_PIN);

  leds.begin();
  for (int i = 0; i < NUM_LEDS; ++i) leds.setPixelColor(i, leds.Color(255,255,255));
  leds.show();

  M5.Lcd.setTextSize(2);
  drawWindow();

  OpenRB.println("ESP32");          // proactive handshake
  handshakeStart = millis();
}

/* ===================================================================== */
/*                                  LOOP                                 */
/* ===================================================================== */
// loop: Main loop
// - Only allow UI and servo commands after calibration is received
// - Skip dead servos in idle animation and button logic
void loop()
{
  M5.update();
  handleLink();

/* -------- handshake timeout → demo mode -------- */
  if (!handshakeReceived && !demoMode &&
      millis() - handshakeStart > 10'000) {
    enterDemoMode();
  }
/* ------------------------------------------------ */

/* ---------- USB-Serial pass-through & commands ---------- */
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (!cmd.length()) goto after_usb;

    /* --- RGB LED --- */
    if (cmd.startsWith("SET_LED;")) {
      int r=0,g=0,b=0;
      int rI=cmd.indexOf("R="), gI=cmd.indexOf("G="), bI=cmd.indexOf("B=");
      if (rI>=0) r = cmd.substring(rI+2, cmd.indexOf(';', rI+2)).toInt();
      if (gI>=0) g = cmd.substring(gI+2, cmd.indexOf(';', gI+2)).toInt();
      if (bI>=0) {
        int e = cmd.indexOf(';', bI+2); if (e==-1) e=cmd.length();
        b = cmd.substring(bI+2, e).toInt();
      }
      uint32_t col = leds.Color(r,g,b);
      for (int i=0;i<NUM_LEDS;++i) leds.setPixelColor(i,col);
      leds.show();
      Serial.printf("[LED] Set R=%d G=%d B=%d\n", r,g,b);
    }

    /* --- mic status LED --- */
    else if (cmd.startsWith("SET_MIC_LED;")) {
      int idx = MIC_LED_INDEX;
      int r=0,g=0,b=0;
      int iI=cmd.indexOf("IDX="), rI=cmd.indexOf("R="), gI=cmd.indexOf("G="), bI=cmd.indexOf("B=");
      if (iI>=0) idx = cmd.substring(iI+4, cmd.indexOf(';', iI+4)).toInt();
      if (rI>=0) r = cmd.substring(rI+2, cmd.indexOf(';', rI+2)).toInt();
      if (gI>=0) g = cmd.substring(gI+2, cmd.indexOf(';', gI+2)).toInt();
      if (bI>=0) {
        int e = cmd.indexOf(';', bI+2); if (e==-1) e=cmd.length();
        b = cmd.substring(bI+2, e).toInt();
      }
      if (idx >= 0 && idx < NUM_LEDS) {
        leds.setPixelColor(idx, leds.Color(r,g,b));
        leds.show();
      }
      Serial.printf("[MIC_LED] IDX=%d R=%d G=%d B=%d\n", idx, r, g, b);
    }

    /* --- SET_SERVO_CONFIG --- */
    else if (cmd.startsWith("SET_SERVO_CONFIG:")) {
      int pos = String("SET_SERVO_CONFIG:").length();
      while (pos < cmd.length()) {
        int semi = cmd.indexOf(';', pos);
        String chunk = (semi==-1) ? cmd.substring(pos)
                                  : cmd.substring(pos, semi);

        int c1=chunk.indexOf(','), c2=chunk.indexOf(',', c1+1),
            c3=chunk.indexOf(',', c2+1), c4=chunk.indexOf(',', c3+1);

        if (c4>c3 && c3>c2 && c2>c1 && c1>0) {
          int id  = chunk.substring(0,c1).toInt();
          int tgt = chunk.substring(c1+1,c2).toInt();
          int vel = chunk.substring(c2+1,c3).toInt();
          int idle = chunk.substring(c3+1,c4).toInt();
          unsigned long ivl = chunk.substring(c4+1).toInt();

          if (id>=0 && id<activeServos) {
            ServoState& s = servos[id];
            /* -------- NEW LOGIC --------
               Clamp only *after* we have a calibration table.           */
            if (calibrationReceived)
              s.angle = constrain(tgt, s.min_angle, s.max_angle);
            else
              s.angle = tgt;

            s.initial_angle      = s.angle;
            s.velocity           = vel;
            s.idle_range         = idle;
            s.idleUpdateInterval = ivl;
          }
        }
        if (semi==-1) break;
        pos = semi + 1;
      }

      Serial.println("[OK] Servo config updated from USB");
      for (int i=0;i<activeServos;++i) {
        ServoState& s = servos[i];
        Serial.printf("Servo %d: angle=%d, velocity=%d, idle_range=%d, "
                      "idleUpdateInterval=%lu\n",
                      i, s.angle, s.velocity,
                      s.idle_range, s.idleUpdateInterval);
      }
      drawWindow();
    }

    /* --- GET_SERVO_CONFIG --- */
    else if (cmd == "GET_SERVO_CONFIG") {
      sendServoConfig();
    }

    /* --- anything else: forward to OpenRB --- */
    else {
      OpenRB.println(cmd);
      Serial.printf("[→RB] (from USB) %s\n", cmd.c_str());
    }
  }
after_usb:

/* ---------- idle jitter ---------- */
  if (calibrationReceived) {
    unsigned long now = millis();
    for (int i=0;i<activeServos;++i) {
      if (!servoPingResult[i]) continue;
      ServoState& s = servos[i];

      if (s.idle_range>0 &&
          now - s.lastIdleUpdate >
              s.idleUpdateInterval + random(0,1000)) {

        int minIdle = max(s.min_angle, s.initial_angle - s.idle_range);
        int maxIdle = min(s.max_angle, s.initial_angle + s.idle_range);

        if (minIdle < maxIdle) {
          int newA;
          for (int t=0;t<10;++t) {        // avoid same position
            newA = random(minIdle, maxIdle+1);
            if (newA != s.angle) break;
          }
          if (newA != s.angle) {
            s.angle = newA;
            drawSingle(i);
            sendMoveServoCommand(i, s.angle, s.velocity);
          }
        }
        s.lastIdleUpdate = now;
      }
    }
  }

/* ---------- buttons ---------- */
  if (M5.BtnA.isPressed() && selected<activeServos && servoPingResult[selected]) {
    if (servos[selected].angle > servos[selected].min_angle) {
      --servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle, servos[selected].velocity);
    }
  }
  if (M5.BtnB.isPressed() && selected<activeServos && servoPingResult[selected]) {
    if (servos[selected].angle < servos[selected].max_angle) {
      ++servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle, servos[selected].velocity);
    }
  }
  if (M5.BtnC.wasPressed()) {
    int next = selected;
    for (int t=0;t<activeServos;++t) {
      next = (next+1) % activeServos;
      if (servoPingResult[next]) { selected=next; drawSingle(selected); break; }
      if (t==activeServos-1) { selected=0; drawSingle(selected); }
    }
  }

  delay(33);
}
