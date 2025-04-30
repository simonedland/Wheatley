#include <M5Unified.h>

constexpr int totalServos  = 11;   // total lines
constexpr int activeServos = 7;    // only 0…6 adjustable

int servoAngles[activeServos] = { 0, 30, 60, 90, 120, 150, 180 };
int selected      = 0;
int scrollOffset  = 0;

// layout
constexpr int lineHeight  = 30;
constexpr int yOffset     = 20;
constexpr int visibleRows = 7;     // (240 – yOffset)/lineHeight ≈ 7
// grey text for disabled servos
constexpr uint16_t GREY = 0x7BEF;

void drawLine(int i, int y) {
  bool isSel = (i == selected);
  // background
  M5.Lcd.fillRect(0, y, M5.Lcd.width(), lineHeight,
                  isSel ? BLUE : BLACK);
  // text
  M5.Lcd.setCursor(10, y + 4);
  if (i < activeServos) {
    M5.Lcd.setTextColor(WHITE, isSel ? BLUE : BLACK);
    M5.Lcd.printf("Servo %d: %3d", i, servoAngles[i]);
  } else {
    M5.Lcd.setTextColor(GREY, BLACK);
    M5.Lcd.printf("Servo %d: disabled", i);
  }
}

// redraw the visible “page” of servos
void drawWindow() {
  M5.Lcd.fillScreen(BLACK);
  for (int row = 0; row < visibleRows; ++row) {
    int i = scrollOffset + row;
    if (i >= totalServos) break;
    int y = yOffset + row * lineHeight;
    drawLine(i, y);
  }
}

// redraw just one servo line if it’s on-screen
void drawSingle(int i) {
  int row = i - scrollOffset;
  if (row < 0 || row >= visibleRows) return;
  int y = yOffset + row * lineHeight;
  drawLine(i, y);
}

void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Lcd.setTextSize(2);
  drawWindow();
}

void loop() {
  M5.update();

  // A held → decrease (only if in active range)
  if (M5.BtnA.isPressed() && selected < activeServos) {
    if (servoAngles[selected] > 0) {
      --servoAngles[selected];
      drawSingle(selected);
    }
  }
  // B held → increase
  if (M5.BtnB.isPressed() && selected < activeServos) {
    if (servoAngles[selected] < 360) {
      ++servoAngles[selected];
      drawSingle(selected);
    }
  }
  // C pressed → advance selection within activeServos,
  // and scroll window if needed
  if (M5.BtnC.wasPressed()) {
    int oldSel = selected;
    selected = (selected + 1) % activeServos;

    // scroll so selection stays in view
    if (selected < scrollOffset) {
      scrollOffset = selected;
    } else if (selected >= scrollOffset + visibleRows) {
      scrollOffset = selected - visibleRows + 1;
    }

    // redraw changed lines
    if (scrollOffset == 0 ||                 // full window shift
        selected == scrollOffset ||          // scrolled up
        selected == scrollOffset + visibleRows - 1) {
      drawWindow();
    } else {
      drawSingle(oldSel);
      drawSingle(selected);
    }
  }

  delay(33);
}
