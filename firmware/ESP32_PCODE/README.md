# Your existing LoRa gateway + local connection

Keep all four code files together in this folder:

```
ESP32_PCODE/
  ESP32_PCODE.ino
  LocalConnection.h
  LocalConnection.cpp
  secrets.h
```

Open **ESP32_PCODE.ino** in Arduino IDE. Arduino compiles the .cpp and includes the headers automatically; upload the sketch once, not each file separately.

## Changes made

The uploaded sketch's LoRa pins, 433 MHz frequency, SPI setup, LEDs, packet parsing (`T:%f,H:%f,S:%d`), 50 ms delay, and `PUMP:1` / `PUMP:0` command strings are retained. Only the Blynk connection is replaced with local HTTP connection calls, and Wi-Fi values are moved into secrets.h. The callback gets its pump state from the local server instead of Blynk V5. LED_WIFI indicates recent server connectivity over Wi-Fi.

Your uploaded original is not overwritten. This is a connection-only adaptation, not a byte-identical copy of the original: some connection calls must change to remove Blynk. Your remote LoRa sensor node does not need a packet-format change.

## Fill secrets.h locally

- WIFI_SSID / WIFI_PASSWORD: your Wi-Fi details.
- LOCAL_SERVER_URL: your computer's LAN IP and port, e.g. http://192.168.1.100:8000.
- LOCAL_DEVICE_KEY: the same private key entered in start.bat and the dashboard.

The committed secrets.h is a placeholder template, not your uploaded credentials. **Do not push your filled secrets.h to GitHub.** It is tracked as a template, so .gitignore does not hide edits to it.

## Upload

1. Select your existing ESP32 board and USB port.
2. Install **LoRa by Sandeep Mistry** and **ArduinoJson 7**. WiFi, HTTPClient, and SPI come with Espressif ESP32 board support. No Blynk library is needed.
3. Fill secrets.h and upload ESP32_PCODE.ino.
4. Run start.bat on your computer. Enter the same key and allow private-network access in the firewall.
5. Connect in the dashboard using that key. Open Serial Monitor at 115200 baud for HTTP error codes (200 means accepted).

## Exact telemetry mapping

- T -> air_temperature (degrees C)
- H -> humidity (percent)
- S -> soil_moisture (percent; must already be 0-100 in the LoRa node)
- soil_temperature -> null because your packet does not contain this measurement. The gauge/graph stays empty instead of inventing a reading.

The adapter does not recalibrate or reinterpret your node's values. If S is raw ADC instead of a percentage, calibrate/convert it at the sensor node before sending it, or explicitly change the protocol later. The server rejects out-of-range sensor packets.

Telemetry is sent only when a new valid LoRa packet is received; HTTP failures are logged and that packet is not retried. The dashboard marks telemetry stale after 15 seconds without accepted data. HTTP requests can briefly block the existing Arduino loop (up to configured timeouts); this is not a lossless radio queue.

Pump state means the gateway's requested state, not confirmation from the remote LoRa node. No acknowledgment or new timeout logic has been added to your radio control code. Turning off the server does not guarantee the remote pump switches off. The existing server returns an off command when telemetry is stale, but the gateway must be connected to receive and forward it.

Firmware must still be compiled and verified with your board and LoRa hardware.
