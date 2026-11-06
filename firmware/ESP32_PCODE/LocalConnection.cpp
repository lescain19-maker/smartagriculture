#include "LocalConnection.h"
#include "secrets.h"
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <math.h>

#ifndef WIFI_SETUP_PASSWORD
#define WIFI_SETUP_PASSWORD "smartagricsetup"
#endif

namespace {
  WiFiManager wifiManager;
  void (*pumpCommand)(int) = nullptr;
  bool pumpRequested = false;
  bool serverConnected = false;
  bool mdnsStarted = false;
  unsigned long lastCommandPoll = 0;
  unsigned long lastServerContact = 0;
  unsigned long lastDiscovery = 0;
  unsigned long disconnectedSince = 0;
  String serverUrl;
  IPAddress networkAddress;

  void prepare(HTTPClient& http, const String& base, const char* endpoint) {
    http.setConnectTimeout(1000);
    http.setTimeout(1000);
    http.begin(base + endpoint);
    http.addHeader("X-Device-Key", LOCAL_DEVICE_KEY);
  }
  void recordContact() {
    serverConnected = true;
    lastServerContact = millis();
  }
  bool requestCommand(const String& base, bool& requested) {
    HTTPClient http;
    prepare(http, base, "/api/command");
    int code = http.GET();
    bool valid = false;
    if (code == 200) {
      JsonDocument response;
      if (!deserializeJson(response, http.getString()) && response["pump"].is<bool>()) {
        requested = response["pump"].as<bool>();
        valid = true;
      }
    }
    http.end();
    return valid;
  }
  void applyCommand(bool next) {
    if (next != pumpRequested && pumpCommand) {
      pumpCommand(next ? 1 : 0); // Existing LoRa handler: unchanged.
      pumpRequested = next;
    }
  }
  bool discoverServer() {
    const int count = mdnsStarted ? MDNS.queryService("smartagric", "tcp") : 0;
    for (int i = 0; i < count; ++i) {
      const String candidate = String("http://") + MDNS.IP(i).toString() + ":" + String(MDNS.port(i));
      bool command;
      // Only accept a server that authenticates with our device key.
      if (requestCommand(candidate, command)) {
        serverUrl = candidate;
        recordContact();
        applyCommand(command);
        Serial.println("Local server discovered: " + serverUrl);
        return true;
      }
    }
    const String fallback = LOCAL_SERVER_URL;
    if (fallback.length()) {
      bool command;
      if (requestCommand(fallback, command)) {
        serverUrl = fallback;
        recordContact();
        applyCommand(command);
        return true;
      }
    }
    return false;
  }
  void setupPortal() {
    Serial.println("Connect your phone to Wi-Fi SmartAgric-Setup, then open http://192.168.4.1 to select the new Wi-Fi.");
    wifiManager.startConfigPortal("SmartAgric-Setup", WIFI_SETUP_PASSWORD);
  }
}

void localBegin(const char* ssid, const char* password, void (*onPumpCommand)(int)) {
  // Keep the original sketch's interface; credentials are provisioned over Wi-Fi.
  (void)ssid;
  (void)password;
  pumpCommand = onPumpCommand;
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  wifiManager.setDebugOutput(false); // Do not log saved Wi-Fi details.
  wifiManager.setConfigPortalBlocking(false);
  wifiManager.setConnectTimeout(10);
  wifiManager.setConfigPortalTimeout(0);
  Serial.println("Trying saved Wi-Fi. If unavailable, use SmartAgric-Setup at http://192.168.4.1.");
  wifiManager.autoConnect("SmartAgric-Setup", WIFI_SETUP_PASSWORD);
}

bool localConnected() {
  return WiFi.status() == WL_CONNECTED && serverConnected &&
         (unsigned long)(millis() - lastServerContact) <= 15000;
}

void localRun() {
  wifiManager.process();
  if (WiFi.status() != WL_CONNECTED) {
    serverConnected = false;
    serverUrl = "";
    if (mdnsStarted) { MDNS.end(); mdnsStarted = false; }
    if (!disconnectedSince) disconnectedSince = millis();
    if ((unsigned long)(millis() - disconnectedSince) > 30000 && !wifiManager.getConfigPortalActive()) setupPortal();
    return;
  }
  disconnectedSince = 0;
  if (wifiManager.getConfigPortalActive()) wifiManager.stopConfigPortal();
  if (!mdnsStarted || networkAddress != WiFi.localIP()) {
    if (mdnsStarted) MDNS.end();
    networkAddress = WiFi.localIP();
    serverUrl = "";
    serverConnected = false;
    // A unique gateway hostname avoids collisions with another ESP32.
    String host = "smartagric-" + String((uint32_t)(ESP.getEfuseMac() & 0xFFFFFF), HEX);
    mdnsStarted = MDNS.begin(host.c_str());
    lastDiscovery = millis() - 5000;
  }
  if (!serverUrl.length()) {
    if ((unsigned long)(millis() - lastDiscovery) >= 5000) {
      lastDiscovery = millis();
      if (!discoverServer()) Serial.println("Waiting for start.bat / local server discovery. Check same LAN, device key and firewall.");
    }
    return;
  }
  if ((unsigned long)(millis() - lastCommandPoll) < 2000) return;
  lastCommandPoll = millis();
  bool next;
  if (requestCommand(serverUrl, next)) {
    recordContact();
    applyCommand(next);
  } else {
    serverConnected = false;
    serverUrl = ""; // Discover again when computer IP or network changes.
    lastDiscovery = millis() - 5000;
  }
}

bool localPublish(float airTemperature, float humidity, int soilMoisture) {
  // Forward only new LoRa packets, without changing sensor conversions.
  if (!isfinite(airTemperature) || !isfinite(humidity)) return false;
  if (WiFi.status() != WL_CONNECTED || !serverUrl.length()) return false;
  JsonDocument payload;
  payload["air_temperature"] = airTemperature;
  payload["humidity"] = humidity;
  payload["soil_moisture"] = soilMoisture;
  payload["soil_temperature"] = nullptr;
  payload["pump"] = pumpRequested; // Gateway command state; no remote-node ACK.
  payload["pump_available"] = true;
  payload["uptime_ms"] = millis();
  String body;
  serializeJson(payload, body);
  HTTPClient http;
  prepare(http, serverUrl, "/api/telemetry");
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  if (code == 200) recordContact();
  else {
    Serial.printf("Local telemetry HTTP status: %d (200 required)\n", code);
    if (code < 0) { serverConnected = false; serverUrl = ""; }
  }
  http.end();
  return code == 200;
}
