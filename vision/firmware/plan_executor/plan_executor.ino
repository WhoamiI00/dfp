#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

// --- WiFi ---
const char* ssid = "Kurumi";
const char* password = "desuwa69";

WebServer server(80);

// --- Motor pins ---
#define IN1 33
#define IN2 32
#define IN3 14
#define IN4 27

#define LIFT1 26
#define LIFT2 25
#define SLIDER1 18
#define SLIDER2 19

#define SERVO_PIN 13
Servo gripperServo;

// --- Ultrasonic ---
#define US_TRIG 17
#define US_ECHO 16
const unsigned long US_TIMEOUT_US = 25000;
const unsigned long US_POLL_MS = 80;
float lastDistanceCm = -1.0;
unsigned long lastUsPoll = 0;

// --- Gripper ---
const int GRIPPER_OPEN_ANGLE  = 0;
const int GRIPPER_CLOSE_ANGLE = 0;

// --- Timeouts ---
const unsigned long DRIVE_TIMEOUT_MS  = 600; // slightly increased
const unsigned long LIFT_TIMEOUT_MS   = 400;

const unsigned long SLIDER_IN_TIME_MS  = 2100;
const unsigned long SLIDER_OUT_TIME_MS = 2000;

unsigned long lastDriveCmd  = 0;
unsigned long lastLiftCmd   = 0;
unsigned long lastSliderCmd = 0;

bool driveActive  = false;
bool liftActive   = false;
bool sliderActive = false;

char sliderDirection = 0;

// --- Forward declarations ---
void handleRoot();
void handleCommand();
void handleDistance();
void executeCommand(char cmd);
void panicStopAll();
void pollUltrasonic();

void addCorsHeaders();
void handleOptions();

void forward();
void backward();
void turnLeft();
void turnRight();
void stopDrive();

void liftUp();
void liftDown();
void stopLift();

void sliderIn();
void sliderOut();
void stopSlider();

void gripperOpen();
void gripperClose();
void gripperRelease();

void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(LIFT1, OUTPUT); pinMode(LIFT2, OUTPUT);
  pinMode(SLIDER1, OUTPUT); pinMode(SLIDER2, OUTPUT);

  pinMode(US_TRIG, OUTPUT);
  pinMode(US_ECHO, INPUT);
  digitalWrite(US_TRIG, LOW);

  // ✅ Attach ONLY ONCE
  gripperServo.attach(SERVO_PIN);
  gripperServo.write(GRIPPER_CLOSE_ANGLE);

  stopDrive();
  stopLift();
  stopSlider();

  WiFi.begin(ssid, password);
  Serial.print("Connecting...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.println(WiFi.localIP());

  server.on("/", HTTP_GET, handleRoot);
  server.on("/cmd", HTTP_GET, handleCommand);
  server.on("/distance", HTTP_GET, handleDistance);

  server.onNotFound([](){
    if (server.method() == HTTP_OPTIONS) handleOptions();
    else {
      addCorsHeaders();
      server.send(404, "text/plain", "Not found");
    }
  });

  server.begin();
}

// --- CORS ---
void addCorsHeaders() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

void handleOptions() {
  addCorsHeaders();
  server.send(204);
}

// --- UI ---
void handleRoot() {
  String page = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>ESP32 Robot</title>

<style>
  body {
    margin: 0;
    background: #0f1115;
    color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    text-align: center;
  }

  h2 {
    margin: 12px 0;
    font-weight: 600;
  }

  .container {
    padding: 12px;
  }

  .group {
    margin: 16px 0;
    padding: 12px;
    border-radius: 16px;
    background: #171a21;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  }

  .label {
    font-size: 12px;
    color: #888;
    margin-bottom: 8px;
    letter-spacing: 1px;
  }

  .row {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin: 6px 0;
  }

  .btn {
    width: 80px;
    height: 80px;
    border-radius: 14px;
    border: none;
    font-size: 14px;
    font-weight: 600;
    background: #232833;
    color: #fff;
    transition: all 0.1s ease;
  }

  .btn:active {
    transform: scale(0.95);
    background: #3a76d8;
  }

  .btn.stop {
    background: #5a1f1f;
  }

  .btn.stop:active {
    background: #d83a3a;
  }

  .btn.panic {
    width: 100%;
    height: 70px;
    font-size: 20px;
    background: #d80000;
    font-weight: bold;
    letter-spacing: 2px;
    margin-bottom: 12px;
  }

  .btn.panic:active {
    background: #ff0000;
  }

  .sensor {
    margin: 12px 0;
    padding: 14px;
    border-radius: 14px;
    background: #111a11;
    border: 1px solid #2a4a2a;
  }

  .sensor .value {
    font-size: 32px;
    font-weight: bold;
    color: #7be07b;
  }

  .status {
    font-size: 12px;
    color: #888;
    margin-top: 8px;
    font-family: monospace;
  }
</style>
</head>

<body>
<div class="container">

<h2>🤖 ESP32 Robot</h2>

<button class="btn panic" onclick="send('X')">STOP ALL</button>

<div class="sensor">
  <div>DISTANCE</div>
  <div class="value" id="dist">--</div>
</div>

<div class="group">
  <div class="label">DRIVE</div>
  <div class="row">
  <button class="btn" onmousedown="hold('F')" onmouseup="stopDrive()">FWD</button>
</div>

<div class="row">
  <button class="btn" onmousedown="hold('L')" onmouseup="stopDrive()">LEFT</button>
  <button class="btn stop" onclick="send('S')">STOP</button>
  <button class="btn" onmousedown="hold('R')" onmouseup="stopDrive()">RIGHT</button>
</div>

<div class="row">
  <button class="btn" onmousedown="hold('B')" onmouseup="stopDrive()">BACK</button>
</div>
</div>

<div class="group">
  <div class="label">LIFT</div>
  <div class="row">
    <button class="btn" onmousedown="hold('U')" onmouseup="stopLift()">UP</button>
    <button class="btn stop" onclick="send('u')">STOP</button>
    <button class="btn" onmousedown="hold('D')" onmouseup="stopLift()">DOWN</button>
  </div>
</div>

<div class="group">
  <div class="label">SLIDER</div>
  <div class="row">
    <button class="btn" onclick="send('I')">IN</button>
    <button class="btn stop" onclick="send('i')">STOP</button>
    <button class="btn" onclick="send('O')">OUT</button>
  </div>
</div>

<div class="group">
  <div class="label">GRIPPER</div>
  <div class="row">
    <button class="btn" onclick="send('G')">OPEN</button>
    <button class="btn stop" onclick="send('H')">HOLD</button>
    <button class="btn" onclick="send('N')">CLOSE</button>
  </div>
</div>

<div class="status" id="status">idle</div>

</div>

<script>
let interval;

function send(cmd){
  fetch('/cmd?val=' + cmd);
  document.getElementById('status').innerText = "CMD: " + cmd;
}

function hold(cmd){
  send(cmd);
  interval = setInterval(()=>send(cmd), 100);
}

function stopDrive(){
  clearInterval(interval);
  send('S');
}

function stopLift(){
  clearInterval(interval);
  send('u');
}

// Distance polling
async function pollDist(){
  try {
    let r = await fetch('/distance');
    let v = parseFloat(await r.text());
    document.getElementById('dist').innerText =
      (v < 0 || isNaN(v)) ? "--" : v.toFixed(1) + " cm";
  } catch {}
}

setInterval(pollDist, 300);
pollDist();
</script>

</body>
</html>
)rawliteral";

  addCorsHeaders();
  server.send(200, "text/html", page);
}

// --- Command handler ---
void handleCommand() {
  if (server.hasArg("val")) {
    executeCommand(server.arg("val")[0]);
  }
  addCorsHeaders();
  server.send(200, "text/plain", "OK");
}

// --- Command execution ---
void executeCommand(char cmd) {
  unsigned long now = millis();

  switch (cmd) {
    case 'F': forward(); driveActive = true; lastDriveCmd = now; break;
    case 'B': backward(); driveActive = true; lastDriveCmd = now; break;
    case 'L': turnLeft(); driveActive = true; lastDriveCmd = now; break;
    case 'R': turnRight(); driveActive = true; lastDriveCmd = now; break;
    case 'S': stopDrive(); driveActive = false; break;

    case 'U': liftUp(); liftActive = true; lastLiftCmd = now; break;
    case 'D': liftDown(); liftActive = true; lastLiftCmd = now; break;
    case 'u': stopLift(); liftActive = false; break;

    case 'I': sliderIn(); sliderActive = true; sliderDirection='I'; lastSliderCmd=now; break;
    case 'O': sliderOut(); sliderActive = true; sliderDirection='O'; lastSliderCmd=now; break;
    case 'i': stopSlider(); sliderActive=false; sliderDirection=0; break;

    case 'G': gripperOpen(); break;
    case 'N': gripperClose(); break;
    case 'H': gripperRelease(); break;

    case 'X': panicStopAll(); break;
  }
}

// --- Safety stop ---
void panicStopAll() {
  stopDrive();
  stopLift();
  stopSlider();
}

// --- Drive ---
void forward(){
  digitalWrite(IN1,LOW); 
  digitalWrite(IN2,HIGH);
  digitalWrite(IN3,LOW); 
  digitalWrite(IN4,HIGH);
}

void backward(){
  digitalWrite(IN1,HIGH); 
  digitalWrite(IN2,LOW);
  digitalWrite(IN3,HIGH); 
  digitalWrite(IN4,LOW);
}
void turnRight(){ digitalWrite(IN1,LOW); digitalWrite(IN2,HIGH); digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW); }
void turnLeft(){ digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW); digitalWrite(IN3,LOW); digitalWrite(IN4,HIGH); }
void stopDrive(){ digitalWrite(IN1,LOW); digitalWrite(IN2,LOW); digitalWrite(IN3,LOW); digitalWrite(IN4,LOW); }

// --- Lift ---
void liftUp(){ digitalWrite(LIFT1,HIGH); digitalWrite(LIFT2,LOW); }
void liftDown(){ digitalWrite(LIFT1,LOW); digitalWrite(LIFT2,HIGH); }
void stopLift(){ digitalWrite(LIFT1,LOW); digitalWrite(LIFT2,LOW); }

// --- Slider ---
void sliderIn(){ digitalWrite(SLIDER1,LOW); digitalWrite(SLIDER2,HIGH); }
void sliderOut(){ digitalWrite(SLIDER1,HIGH); digitalWrite(SLIDER2,LOW); }
void stopSlider(){ digitalWrite(SLIDER1,LOW); digitalWrite(SLIDER2,LOW); }

// --- Gripper (FIXED) ---
void gripperClose(){
  for (int pos = 80; pos >= 10; pos -= 5) {
    gripperServo.write(pos);
    delay(50);  // smooth delay
  }
}

void gripperOpen(){
  for (int pos = 10; pos <= 80; pos += 5) {
    gripperServo.write(pos);
    delay(50);  // smooth delay
  }
}

void gripperRelease(){
  // DO NOTHING → keeps stable signal
}

// --- Distance ---
void handleDistance(){
  addCorsHeaders();
  server.send(200, "text/plain", String(lastDistanceCm));
}

// --- Ultrasonic ---
// pulseIn() blocks for up to 25 ms waiting for the echo. During that block,
// the ESP32 can't service incoming /cmd HTTP requests, so motor heartbeats
// queue up and the watchdog can stutter the motor. Skip polling entirely
// while any motor is active — distance only matters at rest, anyway.
void pollUltrasonic(){
  if (driveActive || liftActive || sliderActive) return;
  if (millis() - lastUsPoll < US_POLL_MS) return;
  lastUsPoll = millis();

  digitalWrite(US_TRIG, LOW); delayMicroseconds(2);
  digitalWrite(US_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(US_TRIG, LOW);

  long duration = pulseIn(US_ECHO, HIGH, US_TIMEOUT_US);
  lastDistanceCm = (duration==0) ? -1 : duration * 0.0343 / 2;
}

// --- Loop ---
void loop() {
  server.handleClient();

  unsigned long now = millis();

  if (driveActive && now - lastDriveCmd > DRIVE_TIMEOUT_MS){
    stopDrive(); driveActive = false;
  }

  if (liftActive && now - lastLiftCmd > LIFT_TIMEOUT_MS){
    stopLift(); liftActive = false;
  }

  if (sliderActive) {
    unsigned long duration =
      (sliderDirection == 'I') ? SLIDER_IN_TIME_MS : SLIDER_OUT_TIME_MS;

    if (now - lastSliderCmd > duration) {
      stopSlider();
      sliderActive = false;
      sliderDirection = 0;
    }
  }

  pollUltrasonic();
}