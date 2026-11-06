# Smart Agric — local LoRa gateway dashboard

ESP32 LoRa gateway → your computer's Python server → dashboard. No Blynk connection. Graphs and SQLite telemetry stay on your computer.

## Use your existing gateway sketch

**Use [firmware/ESP32_PCODE](firmware/ESP32_PCODE)**, based on your uploaded ESP32_PCODE.ino. Keep these files in one Arduino folder:

```
ESP32_PCODE/
  ESP32_PCODE.ino
  LocalConnection.h
  LocalConnection.cpp
  secrets.h
```

A ready-to-extract folder is also available in **[ESP32_PCODE_upload.zip](ESP32_PCODE_upload.zip)**. Extract it first, then open ESP32_PCODE.ino in Arduino IDE. Arduino automatically compiles all four files; select your board/port and upload once.

The LoRa GPIOs, SPI configuration, 433 MHz frequency, LEDs, T/H/S parsing, 50 ms delay, and PUMP:1 / PUMP:0 radio commands are retained. Only Blynk connectivity is replaced and Wi-Fi credentials are moved to secrets.h. The uploaded original file is not overwritten.

Install **LoRa by Sandeep Mistry** and **ArduinoJson 7**. WiFi, HTTPClient and SPI come with Espressif's ESP32 board package. No DHT, DS18B20, or Blynk libraries are needed for this gateway.

### Fill secrets.h locally

```cpp
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define LOCAL_SERVER_URL "http://192.168.1.100:8000"
#define LOCAL_DEVICE_KEY "YOUR_PRIVATE_KEY_AT_LEAST_16_CHARACTERS"
```

Use your computer's actual LAN IPv4 address. The ESP32 must not use localhost or 0.0.0.0. Use the same private key in secrets.h, start.bat, and the dashboard connection panel. The published secrets.h contains placeholders only; **do not push your filled secrets.h**. It is a tracked template, so .gitignore does not hide edits to it.

## Start the local server

1. Install **Python 3.10+**, download the full repository ZIP, and extract it.
2. Double-click **start.bat** on Windows. It checks for Python, asks for your key with hidden input, starts the server, and opens **http://localhost:8000**. The key is not saved. Leave the terminal open.
3. If asked by Windows Firewall, allow Python on private networks. Keep the ESP32 and computer on the same LAN. Find the computer's IPv4 address with `ipconfig`; use that IP in secrets.h.
4. Upload the gateway sketch and open Serial Monitor at **115200 baud**.
5. In the dashboard, select **Connect ESP32** and enter the same device key. New LoRa packets will populate gauges and graphs. HTTP status 200 means a packet was accepted.

For manual Windows PowerShell startup:

```powershell
$env:ESP32_DEVICE_KEY = "YOUR_PRIVATE_KEY_AT_LEAST_16_CHARACTERS"
python server.py --host 0.0.0.0 --port 8000
```

macOS/Linux:

```sh
export ESP32_DEVICE_KEY='YOUR_PRIVATE_KEY_AT_LEAST_16_CHARACTERS'
python3 server.py --host 0.0.0.0 --port 8000
```

The server uses HTTP on a trusted LAN. Do not port-forward it to the internet. GitHub Pages cannot run the Python server; use its local URL. Reserve the computer's IP in the router if possible and prevent the computer from sleeping.

## What your LoRa packet supplies

Your original format is `T:27.5,H:60.2,S:43`:

| Packet field | Dashboard | Meaning |
| --- | --- | --- |
| T | Air temperature | Degrees C |
| H | Humidity | Percent |
| S | Soil moisture | Percent, already converted by your LoRa node |
| No field | Soil temperature | Unavailable: shown empty, never copied from T or set to zero |

The connection layer forwards values without recalibrating them. If S is a raw ADC value, the node must convert it to a calibrated percentage. The server validates moisture/humidity 0–100 and temperatures −40–125 C. Plausible but inaccurate values require checking the node's sensors/calibration. No automatic pump rules or sensor processing were added.

New telemetry is sent only on a newly parsed LoRa packet. Cached data is not replayed as fresh. If no accepted packet arrives for 15 seconds, the dashboard marks it stale. HTTP can block the Arduino loop briefly up to configured timeouts; failed packets are logged rather than queued for lossless delivery.

## Graphs and storage

The dashboard provides gauges, four graph panels, min/average/max, 15-minute/hour/all-loaded views, missing-data gaps, and CSV export. The soil-temperature panel remains empty for T/H/S packets.

SQLite data stays in `data/telemetry.sqlite3` for seven days (pruned on ingestion). On connect, the dashboard loads the latest 720 records from the last hour, then appends incoming measurements, retaining up to 720 points. CSV exports loaded readings. Times are server receive times, not sensor measurement timestamps.

## Pump command meaning

The local server replaces the Blynk V5 callback as the command source. Your existing gateway still toggles LED_PUMP and sends exactly PUMP:1 or PUMP:0 over LoRa. The adapter polls commands every two seconds and calls your handler when the requested state changes.

The gateway has no acknowledgment from the remote node. The dashboard's pump state is the **gateway command state**, not proof that the remote pump is on/off. Your original radio control logic has no newly added failsafe; loss of Wi-Fi/server connection does not guarantee the remote pump turns off. The existing server returns an off request when telemetry is stale, but the gateway needs connectivity to receive and forward it.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| LoRa init failed | Original radio wiring, pins and module; these were not changed. |
| Waiting for ESP32 | Radio node transmitting T/H/S format; gateway Wi-Fi; server IP and firewall. |
| HTTP 401 | Identical device key in all three places. |
| HTTP 400 | Sensor values within ranges; S must be a percentage. |
| Negative HTTP code | Computer reachable, correct LAN IP, port 8000, server running, no guest-Wi-Fi isolation. |
| Soil-temperature gauge empty | Expected: your packet has no soil-temperature field. |
| Strange values | Diagnose sensor/node conversion and calibration; values are forwarded unchanged. |

See [gateway notes](firmware/ESP32_PCODE/README.md) for details. The older `firmware/SmartAgric` direct-sensor example is separate; **do not combine it with your gateway sketch**.

## API for existing firmware

All API calls require `X-Device-Key`. POST bodies are JSON.

- POST `/api/telemetry`: soil_moisture, air_temperature, humidity (finite numbers), optional soil_temperature (number or null), pump/pump_available (booleans), uptime_ms (nonnegative integer).
- GET `/api/command`: returns a pump boolean for the gateway to forward.
- GET `/api/status`: latest packet, age, online status, requested pump state.
- GET `/api/history?minutes=60`: up to 720 readings from the requested interval (1–10080 minutes).
- POST `/api/pump` with a pump boolean: queue a command. On is rejected for stale/unavailable telemetry.

One gateway per server instance. Dashboard credentials remain in tab memory; telemetry/database and filled credentials should stay private.

## Verification

Run `python -m unittest discover -s tests` and `node tests/history.test.cjs`. Server ingestion and optional soil temperature, graph gaps, statistics, CSV, and command gating are covered. Actual ESP32 compilation, LoRa hardware and browser rendering must still be verified on your equipment.
