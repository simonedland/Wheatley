/******************************************************************************
 *  Core-2 touch UI for 7-servo head • talks to OpenRB-150 on UART2
 *  fixed: 2025-05-21  (early “ESP32” handshake)
 ******************************************************************************/

#include <M5Unified.h>
#include <HardwareSerial.h>
HardwareSerial OpenRB(2);                  // use ESP32 UART2

constexpr int RX2_PIN = 13;                // Grove Port-C white
constexpr int TX2_PIN = 14;                // Grove Port-C yellow
constexpr uint32_t LINK_BAUD = 115200;     // same as OpenRB

/* ---------------- servo state ---------------- */
constexpr int totalServos  = 11;           // lines in UI
constexpr int activeServos = 7;            // 0…6 controllable

struct ServoState {
  int angle, initial_angle, velocity;
  int min_angle, max_angle, idle_range;
  unsigned long lastIdleUpdate, idleUpdateInterval;
};

ServoState servos[activeServos] = {
  {  0,  0, 5,-720, 720,10,0,2000},   // lens
  { 30, 30, 5, 30, 60,10,0,2000},     // eyelid1
  { 60, 60, 5, 30, 60,10,0,2000},     // eyelid2
  { 90, 90, 5, 45,135,10,0,2000},     // eyeX
  {120,120, 5, 40,140,10,0,2000},     // eyeY
  {150,150, 5,  0,170,10,0,2000},     // handle1
  {170,170, 5,  0,170,10,0,2000}      // handle2
};

const char* SERVO_NAMES[activeServos] = {
  "lens","eyelid1","eyelid2","eyeX","eyeY","handle1","handle2"
};

/* ---------------- UI layout ---------------- */
constexpr int lineHeight  = 30;
constexpr int yOffset     = 20;
constexpr int visibleRows = 7;
constexpr uint16_t GREY = 0x7BEF;

int selected     = 0;
int scrollOffset = 0;

/* ---------------- helpers ---------------- */
void drawLine(int i, int y)
{
  bool isSel = (i == selected);
  M5.Lcd.fillRect(0, y, M5.Lcd.width(), lineHeight, isSel ? BLUE : BLACK);
  M5.Lcd.setCursor(10, y + 4);
  if (i < activeServos) {
    M5.Lcd.setTextColor(WHITE, isSel ? BLUE : BLACK);
    M5.Lcd.printf("%d: %3d V:%d I:%d F:%lu",
                  i, servos[i].angle, servos[i].velocity,
                  servos[i].idle_range, servos[i].idleUpdateInterval);
  } else {
    M5.Lcd.setTextColor(GREY, BLACK);
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

/* ---------------- UART helpers ---------------- */
void sendMoveServoCommand(int id, int tgt, int vel)
{
  String cmd = "MOVE_SERVO;ID=" + String(id) +
               ";TARGET="  + String(tgt) +
               ";VELOCITY="+ String(vel) + ";\n";
  OpenRB.print(cmd);
  Serial.printf("[→RB] %s", cmd.c_str());
}

/* parse: id,min,max;id,min,max;…  from OpenRB */
void handleCalibrationData(const String& line)
{
  int last = 0;
  while (last < line.length()) {
    int next = line.indexOf(';', last);
    String chunk = (next == -1) ? line.substring(last)
                                : line.substring(last, next);
    int c1 = chunk.indexOf(',');
    int c2 = chunk.indexOf(',', c1 + 1);
    if (c1 > 0 && c2 > c1) {
      int id = chunk.substring(0, c1).toInt();
      float mn = chunk.substring(c1 + 1, c2).toFloat();
      float mx = chunk.substring(c2 + 1).toFloat();
      if (id >= 0 && id < activeServos) {
        servos[id].min_angle = round(mn);
        servos[id].max_angle = round(mx);
        servos[id].angle     = constrain(servos[id].angle, servos[id].min_angle,
                                                       servos[id].max_angle);
        servos[id].initial_angle = servos[id].angle;
      }
    }
    if (next == -1) break;
    last = next + 1;
  }
  drawWindow();
  Serial.println("[OK] Calibration table updated");
}

/* plain MOVE_SERVO or other commands from OpenRB (not used here) */
void handleSerialCommand(const String& cmd)
{
  Serial.printf("[RB>] %s\n", cmd.c_str());
}

/* poll robot UART */
void handleLink()
{
  while (OpenRB.available()) {
    String msg = OpenRB.readStringUntil('\n');
    msg.trim();

    if (msg.startsWith("HELLO")) {
      Serial.println("[RB>] HELLO");
      OpenRB.println("ESP32");
      Serial.printf("[<RB] %s\n", msg.c_str());
    } else if (msg.indexOf(',') > 0 && msg.indexOf(';') > 0) {
      handleCalibrationData(msg);
    } else if (msg.length()) {
      handleSerialCommand(msg);
    }
  }
}

/* ===================================================================== */
/*                               SETUP                                   */
/* ===================================================================== */
void setup()
{
  auto cfg = M5.config();
  M5.begin(cfg);

  Serial.begin(115200);                   // USB debug
  OpenRB.begin(LINK_BAUD, SERIAL_8N1, RX2_PIN, TX2_PIN);

  M5.Lcd.setTextSize(2);
  drawWindow();

  /* ───── proactive handshake (in case we boot first) ───── */
  OpenRB.println("ESP32");
}

/* ===================================================================== */
/*                                LOOP                                   */
/* ===================================================================== */
void loop()
{
  M5.update();
  handleLink();

  /* --- idle animation --- */
  for (int i = 0; i < activeServos; ++i) {
    unsigned long now = millis();
    ServoState& s = servos[i];
    if (s.idle_range > 0 &&
        now - s.lastIdleUpdate >
            s.idleUpdateInterval + random(0, 1000)) {

      int minIdle = max(s.min_angle, s.initial_angle - s.idle_range);
      int maxIdle = min(s.max_angle, s.initial_angle + s.idle_range);
      int newAngle = constrain(s.angle + random(-s.idle_range, s.idle_range + 1),
                               minIdle, maxIdle);
      if (newAngle != s.angle) {
        s.angle = newAngle;
        drawSingle(i);
        sendMoveServoCommand(i, s.angle, s.velocity);
      }
      s.lastIdleUpdate = now;
    }
  }

  /* --- buttons: left / centre / right --- */
  if (M5.BtnA.isPressed() && selected < activeServos) {
    if (servos[selected].angle > servos[selected].min_angle) {
      --servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle,
                                          servos[selected].velocity);
    }
  }
  if (M5.BtnB.isPressed() && selected < activeServos) {
    if (servos[selected].angle < servos[selected].max_angle) {
      ++servos[selected].angle;
      drawSingle(selected);
      sendMoveServoCommand(selected, servos[selected].angle,
                                          servos[selected].velocity);
    }
  }
  if (M5.BtnC.wasPressed()) {
    int old = selected;
    selected = (selected + 1) % activeServos;
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
