// plan_executor.ino — receives single-char movement commands over HC-05
// and drives a 4-direction L298N robot car. No precise angle support: only
// 90° in-place turns and one-cell forward/backward steps.
//
// Hardware:
//   Arduino Mega 2560
//   HC-05  TXD -> pin 19 (RX1) direct
//          RXD -> pin 18 (TX1) via 1k+2k voltage divider
//          VCC -> 5V, GND -> GND
//   L298N  IN1 -> pin 22, IN2 -> pin 23  (motor A)
//          IN3 -> pin 24, IN4 -> pin 25  (motor B)
//
// Protocol (single-char, '\n'/'\r' ignored):
//   F   forward one cell                -> "OK\n"
//   B   backward one cell               -> "OK\n"
//   L   turn left  90° in place         -> "OK\n"
//   R   turn right 90° in place         -> "OK\n"
//   G   grab  (placeholder, 2 s pause)  -> "OK\n"
//   P   place (placeholder, 2 s pause)  -> "OK\n"
//   S   emergency stop                  -> "OK\n"
//   ?   ping                            -> "PONG\n"
//
// All movements block until complete, then send "OK". The PC waits for OK
// before sending the next char, so commands never queue inside the Mega.
//
// TUNING: adjust CELL_FORWARD_MS and TURN_90_MS for your motors. There is
// no encoder, so distance/angle accuracy depends entirely on these constants
// and a flat, consistent floor.

const unsigned long CELL_FORWARD_MS = 1500;  // time to drive one 0.25 m cell
const unsigned long TURN_90_MS      = 600;   // time to rotate 90° in place
const unsigned long GRAB_PLACE_MS   = 2000;  // placeholder grab/place pause

const int IN1 = 22;
const int IN2 = 23;
const int IN3 = 24;
const int IN4 = 25;

void stopCar() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

void driveForward() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void driveBackward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void spinRight() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void spinLeft() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void timedMove(void (*motion)(), unsigned long ms) {
  motion();
  delay(ms);
  stopCar();
}

void handle(char cmd) {
  Serial.print("Received: "); Serial.println(cmd);

  switch (cmd) {
    case 'F': timedMove(driveForward,  CELL_FORWARD_MS); break;
    case 'B': timedMove(driveBackward, CELL_FORWARD_MS); break;
    case 'L': timedMove(spinLeft,      TURN_90_MS);      break;
    case 'R': timedMove(spinRight,     TURN_90_MS);      break;
    case 'G': stopCar(); delay(GRAB_PLACE_MS);           break;
    case 'P': stopCar(); delay(GRAB_PLACE_MS);           break;
    case 'S': stopCar();                                 break;
    case '?': Serial1.println("PONG");                   return;
    default:  Serial1.print("ERR "); Serial1.println(cmd); return;
  }
  Serial1.println("OK");
}

void setup() {
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopCar();

  Serial.begin(9600);   // USB debug
  Serial1.begin(9600);  // HC-05
  Serial.println("ready");
}

void loop() {
  if (Serial1.available()) {
    char c = Serial1.read();
    if (c == '\n' || c == '\r' || c == ' ') return;
    handle(c);
  }
}
