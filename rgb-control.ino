#include <SPI.h>
#include <WiFiNINA.h>

// ---------------------------------------------------------------- //
//                       SETTINGS                                   //
// ---------------------------------------------------------------- //

char ssid[] = "GalaxyA15";      // your network SSID
char pass[] = "aaa77hot";       // your network password

// LED CONFIGURATION
const int redPin = 10;
const int greenPin = 11;
const int bluePin = 9; // Pin 9 is best for PWM on Nano 33 IoT

// *** IMPORTANT: CHANGE THIS IF COLORS ARE INVERTED ***
// Set to 'true' if you have a Common Anode LED.
// Set to 'false' if you have a Common Cathode LED (Standard).
bool isCommonAnode = false; 

// ---------------------------------------------------------------- //

int status = WL_IDLE_STATUS;
WiFiServer server(80);

void setup() {
  Serial.begin(9600);
  
  pinMode(redPin, OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin, OUTPUT);

  // ------------------------------------------------------------
  // STARTUP BRIGHTNESS CHECK
  // Flash White at 100% power to show max physical brightness
  // ------------------------------------------------------------
  Serial.println("Testing Max Brightness...");
  setColor(255, 255, 255); // Turn ON full white
  delay(2000);             // Keep it on for 2 seconds
  setColor(0, 0, 0);       // Turn OFF
  // ------------------------------------------------------------

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    while (true);
  }

  while (status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    delay(10000); 
  }

  server.begin();
  printWifiStatus();
}

void loop() {
  WiFiClient client = server.available();

  if (client) {
    String currentLine = "";
    String request = "";

    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        request += c;
        
        if (c == '\n') {
          if (currentLine.length() == 0) {
            
            client.println("HTTP/1.1 200 OK");
            client.println("Content-type:text/html");
            client.println("Connection: close");
            client.println();

            if (request.indexOf("GET /set?") >= 0) {
              handleColorChange(request);
            }

            sendWebPage(client);
            break;
          } else {
            currentLine = "";
          }
        } else if (c != '\r') {
          currentLine += c;
        }
      }
    }
    client.stop();
  }
}

// Helper function to handle the Common Anode logic automatically
void setColor(int r, int g, int b) {
  if (isCommonAnode) {
    // Invert values for Common Anode (0 is ON, 255 is OFF)
    analogWrite(redPin, 255 - r);
    analogWrite(greenPin, 255 - g);
    analogWrite(bluePin, 255 - b);
  } else {
    // Standard Common Cathode (0 is OFF, 255 is ON)
    analogWrite(redPin, r);
    analogWrite(greenPin, g);
    analogWrite(bluePin, b);
  }
}

void handleColorChange(String req) {
  int rIndex = req.indexOf("r=");
  int gIndex = req.indexOf("g=");
  int bIndex = req.indexOf("b=");
  
  if (rIndex > 0 && gIndex > 0 && bIndex > 0) {
    String rStr = req.substring(rIndex + 2, gIndex - 1);
    String gStr = req.substring(gIndex + 2, bIndex - 1);
    int bEnd = req.indexOf(" ", bIndex);
    String bStr = req.substring(bIndex + 2, bEnd);

    int rVal = rStr.toInt();
    int gVal = gStr.toInt();
    int bVal = bStr.toInt();

    Serial.print("Setting Color -> R:"); Serial.print(rVal);
    Serial.print(" G:"); Serial.print(gVal);
    Serial.print(" B:"); Serial.println(bVal);

    setColor(rVal, gVal, bVal);
  }
}

void sendWebPage(WiFiClient client) {
  client.println("<!DOCTYPE HTML>");
  client.println("<html>");
  client.println("<head>");
  client.println("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">");
  client.println("<style>");
  client.println("body { font-family: sans-serif; text-align: center; background-color: #222; color: white; padding-top: 50px; }");
  client.println("input[type=color] { border: none; width: 150px; height: 150px; cursor: pointer; background: none; }");
  client.println("</style>");
  client.println("</head>");
  client.println("<body>");
  client.println("<h1>WiFi Color Control</h1>");
  client.println("<p>Tap to pick color:</p>");
  
  // Default value set to #FFFFFF (White/Max Brightness)
  client.println("<input type=\"color\" id=\"colorPicker\" value=\"#FFFFFF\" oninput=\"sendColor(this.value)\">");

  client.println("<script>");
  client.println("let lastSend = 0;");
  client.println("function sendColor(hex) {");
  client.println("  const now = Date.now();");
  client.println("  if (now - lastSend < 50) return;"); // Reduced delay for faster response
  client.println("  lastSend = now;");
  client.println("  const r = parseInt(hex.substr(1,2), 16);");
  client.println("  const g = parseInt(hex.substr(3,2), 16);");
  client.println("  const b = parseInt(hex.substr(5,2), 16);");
  client.println("  fetch('/set?r=' + r + '&g=' + g + '&b=' + b);");
  client.println("}");
  client.println("</script>");
  client.println("</body>");
  client.println("</html>");
}

void printWifiStatus() {
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());
  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);
  Serial.println("Open in browser: http://" + String(ip));
}