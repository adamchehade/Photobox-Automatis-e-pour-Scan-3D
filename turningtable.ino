#include <WiFi.h>
#include <WebServer.h>
#include <Stepper.h>

// --- Wi-Fi Settings ---
const char* ssid = "GalaxyA15";     // <--- CHANGE THIS
const char* password = "aaa77hot"; // <--- CHANGE THIS

// --- HARDWARE CONFIGURATION ---
// Steps per revolution for 28BYJ-48 is 2048
const int stepsPerRevolution = 2048; 
#define IN1 14
#define IN2 27
#define IN3 26
#define IN4 25

Stepper myStepper(stepsPerRevolution, IN1, IN3, IN2, IN4);
WebServer server(80);

// --- VARIABLES ---
int currentMode = 0; 
int direction = 1;   
int stepsToMove = 0; // Counts steps for precise movement

void handleControl() {
  // Example: http://IP/control?mode=4&steps=100&dir=cw
  
  if (server.hasArg("mode")) {
    currentMode = server.arg("mode").toInt();
  }
  
  if (server.hasArg("dir")) {
    String d = server.arg("dir");
    direction = (d == "ccw") ? -1 : 1;
  }

  // PRECISE MODE: Read how many steps to take
  if (server.hasArg("steps")) {
    stepsToMove = server.arg("steps").toInt();
  }

  server.send(200, "text/plain", "OK");
}

void setup() {
  Serial.begin(115200);
  myStepper.setSpeed(10); // 10 RPM (Slow & Safe)

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected.");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP()); // <--- COPY THIS IP

  server.on("/control", handleControl);
  server.begin();
}

void loop() {
  server.handleClient();

  switch (currentMode) {
    case 0: // STOP
      break;

    case 1: // CONTINUOUS
      myStepper.step(direction);
      break;

    case 4: // PRECISE STEP MODE
      if (stepsToMove > 0) {
        myStepper.step(direction);
        stepsToMove--;
      } else {
        // Automatically stop when steps are done
        currentMode = 0; 
      }
      break;
  }
}