// ESP32 -> your local Python server. No Blynk dependency.
// Libraries: DHT sensor library + Adafruit Unified Sensor, OneWire,
// DallasTemperature, ArduinoJson 7. Select your exact ESP32 board.
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include "config.h"

DHT airSensor(DHT_PIN, DHT_MODEL);
OneWire oneWire(SOIL_TEMP_PIN);
DallasTemperature soilSensor(&oneWire);
bool pumpOn = false;
unsigned long lastTelemetry = 0, lastCommand = 0, lastCommandOK = 0;
bool commandSeen = false;

void setPump(bool on) {
  pumpOn = RELAY_CONFIGURED && on;
  if (RELAY_CONFIGURED) digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? !pumpOn : pumpOn);
}

void getCommand() {
  HTTPClient http;
  http.setConnectTimeout(1500);
  http.setTimeout(1500);
  http.begin(String(SERVER_URL) + "/api/command");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  int code = http.GET();
  if (code == 200) {
    JsonDocument doc;
    if (!deserializeJson(doc, http.getString()) && doc["pump"].is<bool>()) {
      setPump(doc["pump"].as<bool>());
      lastCommandOK = millis();
      commandSeen = true;
    }
  }
  http.end();
}

void sendTelemetry() {
  const int raw = analogRead(SOIL_MOISTURE_PIN);
  const float temperature = airSensor.readTemperature();
  const float humidity = airSensor.readHumidity();
  soilSensor.requestTemperatures();
  const float soilTemperature = soilSensor.getTempCByIndex(0);
  Serial.printf("Raw moisture=%d | Air=%.2f C | Humidity=%.2f %% | Soil=%.2f C\n", raw, temperature, humidity, soilTemperature);
  if (!MOISTURE_CALIBRATED || MOISTURE_DRY_RAW == MOISTURE_WET_RAW) {
    Serial.println("Calibrate moisture endpoints in config.h. Telemetry withheld; no invented percentages.");
    return;
  }
  if (!isfinite(temperature) || !isfinite(humidity) || !isfinite(soilTemperature) ||
      humidity < 0 || humidity > 100 || temperature < -40 || temperature > 125 ||
      soilTemperature == DEVICE_DISCONNECTED_C || soilTemperature < -40 || soilTemperature > 125) {
    Serial.println("Invalid sensor reading. Check wiring, supply, sensor model and pull-ups. Packet withheld.");
    return;
  }
  float moisture = 100.0f * (raw - MOISTURE_DRY_RAW) / (MOISTURE_WET_RAW - MOISTURE_DRY_RAW);
  if (moisture < 0 || moisture > 100) Serial.println("Moisture raw reading outside calibration endpoints; percentage clamped.");
  moisture = constrain(moisture, 0.0f, 100.0f);
  JsonDocument doc;
  doc["soil_moisture"] = moisture;
  doc["soil_temperature"] = soilTemperature;
  doc["air_temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["pump"] = pumpOn;
  doc["pump_available"] = bool(RELAY_CONFIGURED);
  doc["uptime_ms"] = millis();
  String payload;
  serializeJson(doc, payload);
  HTTPClient http;
  http.setConnectTimeout(1500);
  http.setTimeout(1500);
  http.begin(String(SERVER_URL) + "/api/telemetry");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  int code = http.POST(payload);
  Serial.printf("Telemetry HTTP status: %d (200 = accepted)\n", code);
  http.end();
}

void setup() {
  Serial.begin(115200);
  if (RELAY_CONFIGURED) {
    digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
    pinMode(RELAY_PIN, OUTPUT);
    setPump(false);
  }
  analogReadResolution(12);
  airSensor.begin();
  soilSensor.begin();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Connecting to Wi-Fi. Sensor pins and calibration must match your hardware.");
}

void loop() {
  if (pumpOn && (!commandSeen || (unsigned long)(millis()-lastCommandOK) > 15000)) setPump(false);
  if (WiFi.status() != WL_CONNECTED) { setPump(false); delay(20); return; }
  unsigned long now = millis();
  if ((unsigned long)(now-lastCommand) >= 2000) { lastCommand = now; getCommand(); }
  if ((unsigned long)(now-lastTelemetry) >= 5000) { lastTelemetry = now; sendTelemetry(); }
  delay(10);
}
