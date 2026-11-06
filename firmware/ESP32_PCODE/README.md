# Your LoRa gateway — automatic local connection

Keep ESP32_PCODE.ino, LocalConnection.h, LocalConnection.cpp, and secrets.h together in this folder. Open ESP32_PCODE.ino and upload once; Arduino compiles all four files together.

## One-time setup

1. Install **LoRa by Sandeep Mistry**, **ArduinoJson 7**, and **WiFiManager by tzapu** (2.0.17 or newer) in Arduino IDE. ESPmDNS, WiFi, HTTPClient, and SPI come with Espressif's ESP32 board package.
2. In secrets.h set LOCAL_DEVICE_KEY to your private key (at least 16 characters). Use the same key in start.bat and the dashboard. Keep LOCAL_SERVER_URL empty for automatic discovery.
3. Upload ESP32_PCODE.ino once with your existing board and GPIO wiring. No radio sensor-node changes are required.
4. Connect a phone/laptop to **SmartAgric-Setup**. The setup Wi-Fi password is **smartagricsetup** (WIFI_SETUP_PASSWORD in secrets.h).
5. Open **http://192.168.4.1**, choose your home Wi-Fi, and enter its password. The ESP32 stores credentials in its own flash. Reconnect your phone/laptop to the home Wi-Fi afterward.
6. Start **start.bat** on your computer. It installs its local mDNS dependency on first use, advertises the server, and opens the dashboard. Enter your unchanged private key.
7. Serial Monitor at 115200 baud should show `Local server discovered: http://...`.

## When Wi-Fi or IP changes

- **Computer IP changes:** no upload or secrets.h edit. The gateway drops failed connections and discovers the server again. The server refreshes its advertised interfaces every five seconds. Restart start.bat if the network adapter/firewall has changed and discovery is blocked.
- **New Wi-Fi name/password:** let the ESP32 try the saved network. On startup it opens SmartAgric-Setup if connection fails; after a later disconnection it opens the portal after about 30 seconds. Join that setup Wi-Fi, open 192.168.4.1, and enter the new network. Keep computer and ESP32 on the same LAN. No firmware upload needed.
- The old WIFI_SSID/WIFI_PASSWORD macros are retained only for your existing sketch interface; WiFiManager manages the saved credentials.

The computer advertises `_smartagric._tcp.local.` over mDNS. The gateway tests discovered servers with its device key before selecting one. No key/password is broadcast. Windows Firewall must allow Python on the private network, including UDP 5353 for mDNS and TCP 8000 for the server. Guest Wi-Fi, AP isolation, and some mobile hotspots block discovery. For networks that block multicast, LOCAL_SERVER_URL can hold an optional manual fallback URL; automatic discovery requires multicast support.

## What remains unchanged

Your ESP32_PCODE.ino is unchanged from the prior local-connection version: LoRa pins, 433 MHz frequency, SPI setup, LEDs, parser T:%f,H:%f,S:%d, 50 ms delay, and PUMP:1 / PUMP:0 commands are retained. This update changes connection helper files only.

T is air temperature, H humidity, S soil moisture already expressed as percent. Soil temperature is unavailable and is sent as null. Values are not recalibrated/reinterpreted by this adapter. Telemetry is sent only for a new LoRa packet; no cached replay is used. HTTP and mDNS discovery can block the Arduino loop briefly, so this is not a lossless radio queue.

Pump status is the gateway's command, not acknowledgment from the radio node. No new pump failsafe was added. Server/network loss cannot guarantee a remote pump switches off.

The committed secrets.h is a template. Do not push your filled credentials to GitHub; tracked template edits are not hidden by .gitignore. Firmware compilation, portal behavior, mDNS and LoRa still need testing with your actual hardware/router.
