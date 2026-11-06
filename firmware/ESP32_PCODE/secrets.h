#pragma once
// Connection settings only. No computer IP is needed in automatic mode.
// Optional legacy Wi-Fi values are retained for the sketch interface; WiFiManager
// stores/provisions the actual Wi-Fi credentials through its local setup portal.
#define WIFI_SSID ""
#define WIFI_PASSWORD ""
// Leave empty for automatic discovery. Optional manual fallback if mDNS is blocked.
#define LOCAL_SERVER_URL ""
// Match the key entered in start.bat and the dashboard. Keep it private.
#define LOCAL_DEVICE_KEY "REPLACE_WITH_YOUR_PRIVATE_DEVICE_KEY"
// Temporary Wi-Fi setup access point. At least eight characters for WPA2.
#define WIFI_SETUP_PASSWORD "smartagricsetup"
