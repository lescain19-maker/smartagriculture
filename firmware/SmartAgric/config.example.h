#pragma once
// Copy to config.h. config.h is ignored by Git.
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define SERVER_URL "http://192.168.1.100:8000" // Computer LAN IP; never localhost.
#define DEVICE_KEY "REPLACE_WITH_YOUR_LOCAL_SERVER_KEY"
// EXAMPLE pins for a classic ESP32: change these to match your board and wiring.
#define DHT_PIN 4
#define DHT_MODEL DHT22
#define SOIL_TEMP_PIN 18
#define SOIL_MOISTURE_PIN 34 // ADC1 on classic ESP32; verify your board.
#define RELAY_PIN 26
#define RELAY_ACTIVE_LOW true
#define RELAY_CONFIGURED false // Verify relay wiring/active level before enabling.
#define MOISTURE_DRY_RAW 3000 // Replace with your measured dry raw ADC value.
#define MOISTURE_WET_RAW 1200 // Replace with your measured wet raw ADC value.
#define MOISTURE_CALIBRATED false // Set true only after measuring both endpoints.
