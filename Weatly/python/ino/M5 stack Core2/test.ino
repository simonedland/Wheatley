#include <M5Unified.h>
#include <Arduino.h>

constexpr int totalServos  = 11;   // total lines
constexpr int activeServos = 7;    // only 0…6 adjustable

// Servo state and config
struct ServoState {
  int angle;
  int initial_angle; // NEW: store initial angle
  int velocity;
  int min_angle;
  int max_angle;
  int idle_range;
  unsigned long lastIdleUpdate;
  unsigned long idleUpdateInterval; // NEW: per-servo idle interval
};
ServoState servos[activeServos] = {
  {0, 0, 5, -720, 720, 10, 0, 2000},    // lens
  {30, 30, 5, 30, 60, 10, 0, 2000},     // eyelid1
  {60, 60, 5, 30, 60, 10, 0, 2000},     // eyelid2
  {90, 90, 5, 45, 135, 10, 0, 2000},    // eyeX
  {120, 120, 5, 40, 140, 10, 0, 2000},  // eyeY
  {150, 150, 5, 0, 170, 10, 0, 2000},   // handle1
  {170, 170, 5, 0, 170, 10, 0, 2000}    // handle2
};

int selected      = 0;
int scrollOffset  = 0;

// layout
constexpr int lineHeight  = 30;
constexpr int yOffset     = 20;
constexpr int visibleRows = 7;     // (240 – yOffset)/lineHeight ≈ 7
constexpr uint16_t GREY = 0x7BEF;

void drawLine(int i, int y) {
  bool isSel = (i == selected);
  M5.Lcd.fillRect(0, y, M5.Lcd.width(), lineHeight, isSel ? BLUE : BLACK);
  M5.Lcd.setCursor(10, y + 4);
  if (i < activeServos) {
    M5.Lcd.setTextColor(WHITE, isSel ? BLUE : BLACK);
    M5.Lcd.printf("%d: %3d V:%d I:%d F:%lu", i, servos[i].angle, servos[i].velocity, servos[i].idle_range, servos[i].idleUpdateInterval);
  } else {
    M5.Lcd.setTextColor(GREY, BLACK);
    M5.Lcd.printf("Servo %d: disabled", i);
  }
}

void drawWindow() {
  M5.Lcd.fillScreen(BLACK);
  for (int row = 0; row < visibleRows; ++row) {
    int i = scrollOffset + row;
    if (i >= totalServos) break;
    int y = yOffset + row * lineHeight;
    drawLine(i, y);
  }
}

void drawSingle(int i) {
  int row = i - scrollOffset;
  if (row < 0 || row >= visibleRows) return;
  int y = yOffset + row * lineHeight;
  drawLine(i, y);
}

// --- Serial Command Parsing ---
void handleSerialCommand(const String& cmd) {
  // Example: MOVE_SERVO;ID=2;TARGET=45;VELOCITY=5;IDLE=10;INTERVAL=1500
  if (cmd.startsWith("MOVE_SERVO")) {
    int id = -1, target = 0, velocity = 5, idle = 10;
    unsigned long interval = 2000;
    int idIdx = cmd.indexOf("ID=");
    int targetIdx = cmd.indexOf("TARGET=");
    int velIdx = cmd.indexOf("VELOCITY=");
    int idleIdx = cmd.indexOf("IDLE=");
    int intervalIdx = cmd.indexOf("INTERVAL=");
    if (idIdx >= 0) {
      id = cmd.substring(idIdx + 3, cmd.indexOf(';', idIdx)).toInt();
    }
    if (targetIdx >= 0) {
      target = cmd.substring(targetIdx + 7, cmd.indexOf(';', targetIdx)).toInt();
    }
    if (velIdx >= 0) {
      velocity = cmd.substring(velIdx + 9, cmd.indexOf(';', velIdx) > 0 ? cmd.indexOf(';', velIdx) : cmd.length()).toInt();
    }
    if (idleIdx >= 0) {
      idle = cmd.substring(idleIdx + 5, cmd.indexOf(';', idleIdx) > 0 ? cmd.indexOf(';', idleIdx) : cmd.length()).toInt();
    }
    if (intervalIdx >= 0) {
      interval = cmd.substring(intervalIdx + 9).toInt();
      if (interval < 250) interval = 250;
    }
    if (id >= 0 && id < activeServos) {
      int minA = servos[id].min_angle;
      int maxA = servos[id].max_angle;
      int clamped = constrain(target, minA, maxA);
      servos[id].angle = clamped;
      servos[id].initial_angle = clamped; // Update initial_angle as well!
      servos[id].velocity = velocity;
      servos[id].idle_range = idle;
      servos[id].idleUpdateInterval = interval;
      servos[id].lastIdleUpdate = millis();
      drawWindow();
      Serial.println("OK");
    } else {
      Serial.println("ERR: Invalid servo ID");
    }
    return;
  }
  Serial.println("ERR: Unknown command");
}

void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Lcd.setTextSize(2);
  drawWindow();
  Serial.begin(9600);
}

void loop() {
  M5.update();

  // Serial command handler
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      handleSerialCommand(cmd);
    }
  }

  // Random idle movement for each servo
  for (int i = 0; i < activeServos; ++i) {
    unsigned long now = millis();
    if (servos[i].idle_range > 0 && now - servos[i].lastIdleUpdate > servos[i].idleUpdateInterval + random(0, 1000)) {
      int minIdle = max(servos[i].min_angle, servos[i].initial_angle - servos[i].idle_range);
      int maxIdle = min(servos[i].max_angle, servos[i].initial_angle + servos[i].idle_range);
      int delta = random(-servos[i].idle_range, servos[i].idle_range + 1);
      int newAngle = constrain(servos[i].angle + delta, minIdle, maxIdle);
      if (newAngle != servos[i].angle) {
        servos[i].angle = newAngle;
        drawSingle(i);
      }
      servos[i].lastIdleUpdate = now;
    }
  }

  if (M5.BtnA.isPressed() && selected < activeServos) {
    if (servos[selected].angle > servos[selected].min_angle) {
      --servos[selected].angle;
      drawSingle(selected);
    }
  }
  if (M5.BtnB.isPressed() && selected < activeServos) {
    if (servos[selected].angle < servos[selected].max_angle) {
      ++servos[selected].angle;
      drawSingle(selected);
    }
  }
  if (M5.BtnC.wasPressed()) {
    int oldSel = selected;
    selected = (selected + 1) % activeServos;
    if (selected < scrollOffset) {
      scrollOffset = selected;
    } else if (selected >= scrollOffset + visibleRows) {
      scrollOffset = selected - visibleRows + 1;
    }
    if (scrollOffset == 0 || selected == scrollOffset || selected == scrollOffset + visibleRows - 1) {
      drawWindow();
    } else {
      drawSingle(oldSel);
      drawSingle(selected);
    }
  }
  delay(33);
}
