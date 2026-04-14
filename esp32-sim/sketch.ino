#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Wokwi-GUEST";
const char* password = "";

const char* serverName = "https://accompany-jokingly-grant.ngrok-free.dev/detect";

const int pirPin = 13;

void setup() {
  Serial.begin(115200);
  pinMode(pirPin, INPUT);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ Connected to WiFi");
}

void loop() {
  int motion = digitalRead(pirPin);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    String json = "{\"motion\": " + String(motion == HIGH ? "true" : "false") + "}";

    int httpResponseCode = http.POST(json);

    Serial.println("📡 Sending Data...");
    Serial.println(json);

    Serial.print("Response Code: ");
    Serial.println(httpResponseCode);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Response: " + response);
    }

    http.end();
  }

  delay(3000);
}