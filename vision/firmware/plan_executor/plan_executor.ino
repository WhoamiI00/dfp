#include <EEPROM.h>

#define IN1 22
#define IN2 23
#define IN3 24
#define IN4 25

// Defaults — may be overridden at boot by EEPROM-persisted values or at any
// time over the USB Serial Monitor (see handleUsbLine below).
unsigned long CELL_FORWARD_MS = 450;    // time for one 0.25 m cell
unsigned long TURN_90_MS      = 2000;   // time for 90° spin
unsigned long GRAB_PLACE_MS   = 2000;   // placeholder grab/place pause

// ============== Runtime-tunable config (USB Serial Monitor, COM7) ==========
//
// No more re-flashing to tweak timing. Open the Arduino IDE's Serial Monitor
// on COM7 (9600 baud, line ending: "Newline") and type:
//
//   F<ms>   set CELL_FORWARD_MS, e.g.  F500
//   T<ms>   set TURN_90_MS,     e.g.  T1800
//   G<ms>   set GRAB_PLACE_MS,  e.g.  G2000
//   ?       print current values
//   reset   restore compiled defaults
//
// Values are written to EEPROM so they survive power cycles. The single-char
// Bluetooth movement protocol on Serial1 is unchanged.

const uint16_t EEPROM_MAGIC = 0xA55A;
const int EEPROM_BASE = 0;

struct PersistedConfig {
  uint16_t magic;
  unsigned long cell_forward_ms;
  unsigned long turn_90_ms;
  unsigned long grab_place_ms;
};

void loadConfig() {
  PersistedConfig cfg;
  EEPROM.get(EEPROM_BASE, cfg);
  if (cfg.magic == EEPROM_MAGIC) {
    CELL_FORWARD_MS = cfg.cell_forward_ms;
    TURN_90_MS      = cfg.turn_90_ms;
    GRAB_PLACE_MS   = cfg.grab_place_ms;
  }
}

void saveConfig() {
  PersistedConfig cfg = {EEPROM_MAGIC, CELL_FORWARD_MS, TURN_90_MS, GRAB_PLACE_MS};
  EEPROM.put(EEPROM_BASE, cfg);
}

void printConfig() {
  Serial.print("F="); Serial.print(CELL_FORWARD_MS);
  Serial.print(" T="); Serial.print(TURN_90_MS);
  Serial.print(" G="); Serial.println(GRAB_PLACE_MS);
}

String usbBuf;

void handleUsbLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  if (line == "?") {
    printConfig();
    return;
  }
  if (line.equalsIgnoreCase("reset")) {
    CELL_FORWARD_MS = 450;
    TURN_90_MS      = 2000;
    GRAB_PLACE_MS   = 2000;
    saveConfig();
    Serial.print("reset -> "); printConfig();
    return;
  }

  char key = line.charAt(0);
  unsigned long val = line.substring(1).toInt();
  if (val == 0) {
    Serial.print("?? "); Serial.println(line);
    return;
  }
  switch (key) {
    case 'F': case 'f': CELL_FORWARD_MS = val; break;
    case 'T': case 't': TURN_90_MS      = val; break;
    case 'G': case 'g': GRAB_PLACE_MS   = val; break;
    default:
      Serial.print("?? "); Serial.println(line);
      return;
  }
  saveConfig();
  printConfig();
}

// ============== Movement protocol on Serial1 (HC-05) ======================

void setup() {
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopCar();

  Serial.begin(9600);
  Serial1.begin(9600);

  loadConfig();
  Serial.print("ready "); printConfig();
}

void loop() {
  // --- USB config channel (non-blocking) ---
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (usbBuf.length() > 0) {
        handleUsbLine(usbBuf);
        usbBuf = "";
      }
    } else {
      usbBuf += c;
      if (usbBuf.length() > 32) usbBuf = "";  // overflow guard
    }
  }

  // --- BT movement channel (single-char, same protocol as before) ---
  if (Serial1.available()) {
    char cmd = Serial1.read();
    if (cmd == '\n' || cmd == '\r' || cmd == ' ') return;
    Serial.print("Received: "); Serial.println(cmd);

    switch (cmd) {
      // Double-swap preserved (wiring correction).
      case 'F': moveBackward(); delay(CELL_FORWARD_MS); stopCar(); Serial1.println("OK"); break;
      case 'B': moveForward();  delay(CELL_FORWARD_MS); stopCar(); Serial1.println("OK"); break;
      case 'L': turnRight();    delay(TURN_90_MS);      stopCar(); Serial1.println("OK"); break;
      case 'R': turnLeft();     delay(TURN_90_MS);      stopCar(); Serial1.println("OK"); break;

      case 'G': stopCar(); delay(GRAB_PLACE_MS); Serial1.println("OK"); break;
      case 'P': stopCar(); delay(GRAB_PLACE_MS); Serial1.println("OK"); break;
      case 'S': stopCar();                       Serial1.println("OK"); break;
      case '?':                                  Serial1.println("PONG"); break;

      default:  Serial1.print("ERR "); Serial1.println(cmd); break;
    }
  }
}

// ================= MOVEMENTS =================

void moveForward()  { digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  }
void moveBackward() { digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); }
void turnRight()    { digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH); digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);  }
void turnLeft()     { digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH); }
void stopCar()      { digitalWrite(IN1, LOW);  digitalWrite(IN2, LOW);  digitalWrite(IN3, LOW);  digitalWrite(IN4, LOW);  }
