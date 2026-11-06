#include "LocalConnection.h"
#include "secrets.h"
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <math.h>

namespace {
  void (*pumpCommand)(int) = nullptr;
  bool pumpRequested = false;
  bool serverConnected = false;
  unsigned long lastCommandPoll = 0;
  unsigned long lastServerContact = 0;

  void prepare(HTTPClient& http, const char* endpoint) {
    http.setConnectTimeout(1000);
    http.setTimeout(1000);
    http.begin(String(LOCAL_SERVER_URL) + endpoint);
    http.addHeader("X-Device-Key", LOCAL_DEVICE_KEY);
  }
  void recordContact() {
    serverConnected = true;
    lastServerContact = millis();
  }
}

void localBegin(const char* ssid, const char* password, void (*onPumpCommand)(int)) {
  pumpCommand = onPumpCommand;
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid, password);
  Serial.println("Local connection started. Waiting for Wi-Fi and the computer server.");
}

bool localConnected() {
  return WiFi.status() == WL_CONNECTED && serverConnected &&
         (unsigned long)(millis() - lastServerContact) <= 15000;
}

void localRun() {
  if (WiFi.status() != WL_CONNECTED) {
    serverConnected = false;
    return;
  }
  if ((unsigned long)(millis() - lastCommandPoll) < 2000) return;
  lastCommandPoll = millis();
  HTTPClient http;
  prepare(http, "/api/command");
  const int code = http.GET();
  if (code == 200) {
    JsonDocument response;
    if (!deserializeJson(response, http.getString()) && response["pump"].is<bool>()) {
      recordContact();
      const bool next = response["pump"].as<bool>();
      if (next != pumpRequested && pumpCommand) {
        pumpCommand(next ? 1 : 0); // Your existing LED and LoRa command handler.
        pumpRequested = next;
      }
    }
  } else {
    serverConnected = false;
    Serial.printf("Local command HTTP status: %d\n", code);
  }
  http.end();
}

bool localPublish(float airTemperature, float humidity, int soilMoisture) {
  // Forward the parsed LoRa measurements without changing their conversions.
  // Do not replay cached packets: dashboard freshness tracks actual new LoRa data.
  if (!isfinite(airTemperature) || !isfinite(humidity)) return false;
  if (WiFi.status() != WL_CONNECTED) return false;
  JsonDocument payload;
  payload["air_temperature"] = airTemperature;
  payload["humidity"] = humidity;
  payload["soil_moisture"] = soilMoisture;
  payload["soil_temperature"] = nullptr; // Not present in T/H/S LoRa packets.
  payload["pump"] = pumpRequested; // Gateway command state; no remote-node ACK.
  payload["pump_available"] = true;
  payload["uptime_ms"] = millis();
  String body;
  serializeJson(payload, body);
  HTTPClient http;
  prepare(http, "/api/telemetry");
  http.addHeader("Content-Type", "application/json");
  const int code = http.POST(body);
  if (code == 200) recordContact();
  else Serial.printf("Local telemetry HTTP status: %d (200 required)\n", code);
  http.end();
  return code == 200;
}
