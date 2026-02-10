#include <WiFi.h>
#include <WebServer.h>
#include <Stepper.h>

// ---------------- WIFI SETTINGS ----------------
// Replace with your actual WiFi credentials
const char* ssid = "GalaxyA15";
const char* password = "aaa77hot";

// ---------------- MOTOR SETTINGS ----------------
// 28BYJ-48
const int stepsPerRevolution = 2048;

// ESP32 pins to ULN2003
#define IN1 14
#define IN2 27
#define IN3 26
#define IN4 25

// Note: Pin order IN1, IN3, IN2, IN4 is specific to the Stepper lib + 28BYJ-48
Stepper myStepper(stepsPerRevolution, IN1, IN3, IN2, IN4);

// ---------------- STATE VARIABLES ----------------
bool isRunning = false;      // Is the motor currently turning?
bool isClockwise = true;     // Direction
int motorSpeed = 10;         // RPM (Range usually 5-15 for this motor)

// Web Server on port 80
WebServer server(80);

// ---------------- HTML PAGE ----------------
// This defines the webpage layout and styling
const char* htmlPage = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ESP32 Stepper Control</title>
  <style>
    body { font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f4; margin: 0; padding: 20px; }
    h1 { color: #333; }
    .card { background: white; max-width: 400px; margin: auto; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    button { border: none; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 5px; width: 100%; }
    .btn-on { background-color: #4CAF50; }
    .btn-off { background-color: #f44336; }
    .btn-cw { background-color: #008CBA; }
    .btn-ccw { background-color: #ff9800; }
    input[type=range] { width: 100%; margin: 20px 0; }
    label { font-size: 18px; font-weight: bold; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Stepper Control</h1>
    
    <button class="btn-on" onclick="fetch('/start')">START</button>
    <button class="btn-off" onclick="fetch('/stop')">STOP</button>
    <br><br>
    <button class="btn-cw" onclick="fetch('/cw')">CLOCKWISE</button>
    <button class="btn-ccw" onclick="fetch('/ccw')">ANTI-CLOCKWISE</button>
    
    <br><br>
    <label for="speed">Speed (RPM): <span id="speedVal">10</span></label>
    <input type="range" id="speed" name="speed" min="1" max="25" value="10" onchange="updateSpeed(this.value)" oninput="document.getElementById('speedVal').innerText = this.value">
  </div>

  <script>
    function updateSpeed(val) {
      fetch('/setSpeed?value=' + val);
    }
  </script>
</body>
</html>
)rawliteral";

// ---------------- SERVER HANDLERS ----------------

void handleRoot() {
  server.send(200, "text/html", htmlPage);
}

void handleStart() {
  isRunning = true;
  server.send(200, "text/plain", "Started");
  Serial.println("Motor Started");
}

void handleStop() {
  isRunning = false;
  // Turn off coils to save power and reduce heat when stopped
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  server.send(200, "text/plain", "Stopped");
  Serial.println("Motor Stopped");
}

void handleCW() {
  isClockwise = true;
  server.send(200, "text/plain", "Direction: CW");
  Serial.println("Direction: Clockwise");
}

void handleCCW() {
  isClockwise = false;
  server.send(200, "text/plain", "Direction: CCW");
  Serial.println("Direction: Anti-Clockwise");
}

void handleSpeed() {
  if (server.hasArg("value")) {
    String speedVal = server.arg("value");
    motorSpeed = speedVal.toInt();
    myStepper.setSpeed(motorSpeed);
    server.send(200, "text/plain", "Speed Set");
    Serial.print("Speed set to: ");
    Serial.println(motorSpeed);
  }
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected! IP Address: ");
  Serial.println(WiFi.localIP());

  // Setup Stepper
  myStepper.setSpeed(motorSpeed);

  // Define Server Routes
  server.on("/", handleRoot);
  server.on("/start", handleStart);
  server.on("/stop", handleStop);
  server.on("/cw", handleCW);
  server.on("/ccw", handleCCW);
  server.on("/setSpeed", handleSpeed);

  server.begin();
  Serial.println("HTTP server started");
}

// ---------------- LOOP ----------------
void loop() {
  // 1. Handle incoming web requests
  server.handleClient();

  // 2. Handle Motor Movement
  if (isRunning) {
    // We only step a small amount per loop. 
    // If we step 2048 at once, the web server will "freeze" until the motor finishes.
    int stepChunk = 20; 

    if (isClockwise) {
      myStepper.step(stepChunk);
    } else {
      myStepper.step(-stepChunk);
    }
  }
}