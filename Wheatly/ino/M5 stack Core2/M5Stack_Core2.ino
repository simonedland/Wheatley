/****************************************************************************** 
 *  Core-2 touch UI for 7-servo head  ·  talks to OpenRB-150 on UART2
 *  rev 2025-06-11  –  full code with LED logging & blue blink in demo-mode
 ******************************************************************************/

#include <M5Unified.h>
#include <HardwareSerial.h>
#include <Adafruit_NeoPixel.h>

/* ---------- UART link to the OpenRB-150 ---------- */
HardwareSerial OpenRB(2);
constexpr int RX2_PIN      = 13;
constexpr int TX2_PIN      = 14;
constexpr uint32_t LINK_BAUD = 115200;

/* ---------- NeoPixel strip ---------- */
#define LED_PIN   27
#define NUM_LEDS   16
Adafruit_NeoPixel leds(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

/* ———— Global state ———— */
uint32_t lastColor = 0;

/* Servo bookkeeping */
constexpr int totalServos  = 11;
constexpr int activeServos = 7;
struct ServoState {
  int angle, initial_angle, velocity;
  int min_angle, max_angle, idle_range;
  unsigned long lastIdleUpdate, idleUpdateInterval;
};
ServoState servos[activeServos] = {
  {  0,  0, 5,    0,   0,700,0,2000},
  {180,180, 5,  180, 220,40,0,2000},
  {180,180, 5,  140, 180,40,0,2000},
  {130,130, 5,  130, 220,90,0,2000},
  {140,140, 5,  140, 210,80,0,2000},
  {  0,  0, 5,   -60,  60,10,0,2000},
  {  0,  0, 5,   -60,  60,10,0,2000}
};
const char* SERVO_NAMES[activeServos] = {
  "lens","eyelid1","eyelid2","eyeX","eyeY","handle1","handle2"
};

/* UI layout */
constexpr int lineHeight  = 30;
constexpr int yOffset     = 20;
constexpr int visibleRows = 7;
constexpr uint16_t GREY   = 0x7BEF;
int selected     = 0;
int scrollOffset = 0;

/* Runtime flags */
bool handshakeReceived   = false;
bool demoMode            = false;
unsigned long handshakeStart = 0;
bool dryRun              = true;
bool servoPingResult[activeServos] = {false};
bool calibrationReceived = false;

/* ———— Forward declarations ———— */
void drawWindow();
void drawLine(int i,int y);
void drawSingle(int i);
void processLedCommand(const String &cmd);
void handleCalibrationData(const String &line);
void sendServoConfig();
void handleUsbCommands();
void handleLink();
void sendMoveServoCommand(int id,int tgt,int vel);
void enterDemoMode();

/* ===================================================================== */
/*                             LED & Blink Helpers                       */
/* ===================================================================== */

/// Paint the strip, remember the color, log each LED.
void setAll(uint32_t col) {
  lastColor = col;
  Serial.printf("[LED] setAll → 0x%06X\n", col);
  for (int i = 0; i < NUM_LEDS; ++i) {
    leds.setPixelColor(i, col);
  }
  leds.show();
}

/// Simple red/black blink used on HELLO handshake.
void blinkScreen(int times) {
  uint32_t prev = lastColor;
  for (int i = 0; i < times; ++i) {
    setAll(leds.Color(255, 0, 0));
    delay(150);
    setAll(0);
    delay(150);
  }
  setAll(prev);
  drawWindow();
}

/// Blink an arbitrary color `times` times.
void blinkColor(uint32_t col, int times, int onMs=250, int offMs=250) {
  uint32_t prev = lastColor;
  for (int i = 0; i < times; ++i) {
    setAll(col);
    delay(onMs);
    setAll(0);
    delay(offMs);
  }
  setAll(prev);
  drawWindow();
}

/* ===================================================================== */
/*                           LED Command Parser                          */
/* ===================================================================== */

void processLedCommand(const String &cmd) {
  Serial.printf("[CMD] \"%s\"\n", cmd.c_str());
  if (!cmd.startsWith("SET_LED;")) return;

  int r = 0, g = 0, b = 0;
  auto parse = [&](char k, int &v) {
    int ix = cmd.indexOf(String(k) + "=");
    if (ix >= 0) {
      int e = cmd.indexOf(';', ix);
      v = cmd.substring(ix+2, e < 0 ? cmd.length() : e).toInt();
      v = constrain(v, 0, 255);
    }
  };
  parse('R', r);
  parse('G', g);
  parse('B', b);

  uint32_t col = leds.Color(r, g, b);
  Serial.printf("[LED] parsed → R=%d G=%d B=%d → 0x%06X\n", r, g, b, col);
  setAll(col);
}

/* ===================================================================== */
/*                          Demo-mode entry                              */
/* ===================================================================== */

void enterDemoMode() {
  demoMode            = true;
  dryRun              = true;
  calibrationReceived = true;
  for (int i = 0; i < activeServos; ++i) {
    servoPingResult[i] = true;
  }
  Serial.println("[WARN] Handshake timeout – entering DEMO MODE");
  blinkColor(leds.Color(0,0,255), 3);
}

/* ===================================================================== */
/*                          Drawing Helpers                              */
/* ===================================================================== */

void drawLine(int i, int y) {
  bool sel  = (i == selected);
  bool dead = (i < activeServos && !servoPingResult[i]);
  uint16_t bg = sel ? BLUE : BLACK;
  uint16_t fg = dead ? RED : WHITE;
  if (demoMode && !sel) fg = BLUE;

  M5.Lcd.fillRect(0, y, M5.Lcd.width(), lineHeight, bg);
  M5.Lcd.setTextColor(fg, bg);
  M5.Lcd.setCursor(10, y + 4);

  if (i < activeServos) {
    const ServoState &s = servos[i];
    M5.Lcd.printf("%d: %3d V:%d I:%d F:%lu",
                  i, s.angle, s.velocity,
                  s.idle_range, s.idleUpdateInterval);
  } else {
    M5.Lcd.setTextColor(GREY, bg);
    M5.Lcd.printf("Servo %d: disabled", i);
  }
}

void drawWindow() {
  M5.Lcd.fillScreen(BLACK);
  for (int row = 0; row < visibleRows; ++row) {
    int i = scrollOffset + row;
    if (i >= totalServos) break;
    drawLine(i, yOffset + row * lineHeight);
  }
}

void drawSingle(int i) {
  int row = i - scrollOffset;
  if (row < 0 || row >= visibleRows) return;
  drawLine(i, yOffset + row * lineHeight);
}

/* ===================================================================== */
/*                       Servo & Link Helpers                            */
/* ===================================================================== */

void sendMoveServoCommand(int id,int tgt,int vel) {
  String c = "MOVE_SERVO;ID="+String(id)
           +";TARGET="+String(tgt)
           +";VELOCITY="+String(vel)+";\n";
  OpenRB.print(c);
  Serial.printf("[→RB] %s", c.c_str());
}

void handleCalibrationData(const String &line) {
  int last = 0;
  while (last < line.length()) {
    int semi = line.indexOf(';', last);
    String chunk = (semi < 0) ? line.substring(last)
                             : line.substring(last, semi);

    int c1 = chunk.indexOf(','),
        c2 = chunk.indexOf(',', c1+1),
        c3 = chunk.indexOf(',', c2+1);
    if (c3>c2 && c2>c1 && c1>0) {
      int id   = chunk.substring(0,c1).toInt();
      int mn   = round(chunk.substring(c1+1,c2).toFloat());
      int mx   = round(chunk.substring(c2+1,c3).toFloat());
      int ping = chunk.substring(c3+1).toInt();
      if (id>=0 && id<activeServos) {
        auto &s = servos[id];
        s.min_angle     = mn;
        s.max_angle     = mx;
        s.angle         = constrain(s.angle, mn, mx);
        s.initial_angle = s.angle;
        servoPingResult[id] = (ping==1);
      }
    }
    if (semi<0) break;
    last = semi+1;
  }
  calibrationReceived = true;
  dryRun = false;
  drawWindow();
  Serial.println("[OK] Calibration table updated");
  Serial.print("SERVO_CONFIG:"); Serial.println(line);
}

void sendServoConfig() {
  Serial.print("SERVO_CONFIG:");
  for (int i=0; i<activeServos; ++i) {
    Serial.printf("%d,%d,%d,%d",
                  i, servos[i].min_angle, servos[i].max_angle,
                  servoPingResult[i]?1:0);
    if (i<activeServos-1) Serial.print(';');
  }
  Serial.println();
}

/* ===================================================================== */
/*                           USB-Serial Handler                          */
/* ===================================================================== */

void handleUsbCommands() {
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.isEmpty()) continue;

    // LED commands first
    processLedCommand(cmd);

    // Servo config from USB
    if (cmd.startsWith("SET_SERVO_CONFIG:")) {
      int pos = cmd.indexOf(':')+1;
      while (pos < cmd.length()) {
        int semi = cmd.indexOf(';', pos);
        String chunk = (semi<0)?cmd.substring(pos):cmd.substring(pos,semi);
        int c1=chunk.indexOf(','),
            c2=chunk.indexOf(',',c1+1),
            c3=chunk.indexOf(',',c2+1),
            c4=chunk.indexOf(',',c3+1);
        if(c4>c3&&c3>c2&&c2>c1&&c1>0){
          int id   = chunk.substring(0,c1).toInt();
          int tgt  = chunk.substring(c1+1,c2).toInt();
          int vel  = chunk.substring(c2+1,c3).toInt();
          int idle = chunk.substring(c3+1,c4).toInt();
          unsigned long ivl = chunk.substring(c4+1).toInt();
          if(id>=0 && id<activeServos){
            auto &s=servos[id];
            if(calibrationReceived)
              s.angle = constrain(tgt,s.min_angle,s.max_angle);
            else
              s.angle = tgt;
            s.initial_angle      = s.angle;
            s.velocity           = vel;
            s.idle_range         = idle;
            s.idleUpdateInterval = ivl;
          }
        }
        if(semi<0) break;
        pos=semi+1;
      }
      Serial.println("[OK] Servo config updated from USB");
      drawWindow();
      continue;
    }

    // Request config
    if (cmd=="GET_SERVO_CONFIG") {
      sendServoConfig();
      continue;
    }

    // Forward any other commands to OpenRB
    OpenRB.println(cmd);
    Serial.printf("[→RB] (USB fwd) %s\n", cmd.c_str());
  }
}

/* ===================================================================== */
/*                         OpenRB Link Handler                           */
/* ===================================================================== */

void handleLink() {
  while (OpenRB.available()) {
    String msg = OpenRB.readStringUntil('\n');
    msg.trim();
    if (msg.isEmpty()) continue;

    // LED commands first
    processLedCommand(msg);

    // HELLO handshake
    if (msg.startsWith("HELLO")) {
      handshakeReceived = true;
      OpenRB.println("ESP32");
      Serial.printf("[<RB] %s\n", msg.c_str());
      blinkScreen(3);
      continue;
    }

    // Calibration data
    if (msg.indexOf(',')>0 && msg.indexOf(';')>0) {
      handleCalibrationData(msg);
      continue;
    }

    // Anything else from RB
    Serial.printf("[RB>] %s\n", msg.c_str());
  }
}

/* ===================================================================== */
/*                                   setup                                */
/* ===================================================================== */

void setup(){
  auto cfg = M5.config();  
  M5.begin(cfg);

  Serial.begin(115200);
  OpenRB.begin(LINK_BAUD, SERIAL_8N1, RX2_PIN, TX2_PIN);

  leds.begin();
  setAll(0);
  delay(100);

  // Startup LED test
  Serial.println("[LED] Testing strip…");
  setAll(leds.Color(255,0,0)); delay(500);
  setAll(leds.Color(0,255,0)); delay(500);
  setAll(leds.Color(0,0,255)); delay(500);
  setAll(0);
  Serial.println("[LED] Test complete");

  M5.Lcd.setTextSize(2);
  drawWindow();

  // Kick off HELLO handshake
  OpenRB.println("ESP32");
  handshakeStart = millis();
}

/* ===================================================================== */
/*                                    loop                                */
/* ===================================================================== */

void loop(){
  M5.update();
  handleLink();
  handleUsbCommands();

  // If no handshake, enter demo mode
  if (!handshakeReceived && !demoMode &&
      millis() - handshakeStart > 10000) {
    enterDemoMode();
  }

  // Idle-jitter animation
  if (calibrationReceived) {
    unsigned long now = millis();
    for (int i = 0; i < activeServos; ++i) {
      if (!servoPingResult[i]) continue;
      auto &s = servos[i];
      if (s.idle_range>0 &&
          now - s.lastIdleUpdate >
            s.idleUpdateInterval + random(0,1000)) {
        int minI = max(s.min_angle, s.initial_angle - s.idle_range);
        int maxI = min(s.max_angle, s.initial_angle + s.idle_range);
        if (minI < maxI) {
          int newA = s.angle;
          for (int t = 0; t < 10; ++t) {
            newA = random(minI, maxI+1);
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

  // Button A: decrement selected servo
  if (M5.BtnA.isPressed() && selected<activeServos && servoPingResult[selected]) {
    if (servos[selected].angle>servos[selected].min_angle) {
      --servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle,
                           servos[selected].velocity);
    }
  }

  // Button B: increment selected servo
  if (M5.BtnB.isPressed() && selected<activeServos && servoPingResult[selected]) {
    if (servos[selected].angle<servos[selected].max_angle) {
      ++servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle,
                           servos[selected].velocity);
    }
  }

  // Button C: cycle selection
  if (M5.BtnC.wasPressed()) {
    int next = selected;
    for (int t = 0; t < activeServos; ++t) {
      next = (next+1)%activeServos;
      if (servoPingResult[next]) {
        selected = next;
        drawSingle(selected);
        break;
      }
      if (t == activeServos-1) {
        selected = 0;
        drawSingle(selected);
      }
    }
  }

  delay(33);
}