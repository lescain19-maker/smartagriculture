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

Install **LoRa by Sandeep Mistry**, **ArduinoJson 7**, and **WiFiManager by tzapu (2.0.17+)**. WiFi, HTTPClient and SPI come with Espressif's ESP32 board package. No DHT, DS18B20, or Blynk libraries are needed for this gateway.

### One-time setup: no fixed computer IP

Set `LOCAL_DEVICE_KEY` in secrets.h to your private key (at least 16 characters). Leave `LOCAL_SERVER_URL` empty. Upload this discovery-enabled firmware **once**. Use the same key in start.bat and the dashboard. Do not push your filled secrets.h; it is tracked as a template.

Connect a phone to **SmartAgric-Setup**, password **smartagricsetup**, and open **http://192.168.4.1**. Choose your home Wi-Fi and enter its password. The gateway remembers it in ESP32 flash. Reconnect your phone to the home Wi-Fi afterward.

**After computer IP changes:** the gateway finds the server automatically; no code edit or upload. The server advertises its current LAN addresses using mDNS (`_smartagric._tcp.local.`), refreshes addresses every five seconds, and the gateway rediscovers after connection failures.

**After Wi-Fi name/password changes:** if the saved network is unavailable, use SmartAgric-Setup again to enter the new credentials. It starts after failed startup connection, or about 30 seconds after a later disconnection. No firmware upload needed. Both devices must be on the same LAN.

The old WIFI_SSID/WIFI_PASSWORD macros are retained only for the existing sketch interface. WiFiManager handles saved credentials; a fixed server IP is no longer required. LOCAL_SERVER_URL can optionally be set as a manual fallback for networks that block multicast.

## Start the local server

1. Install **Python 3.10+**, download the full repository ZIP, and extract it.
2. Double-click **start.bat** on Windows. It checks for Python, installs the discovery library in a local .venv on first use (internet required once), asks for your key with hidden input, advertises the server automatically, and opens **http://localhost:8000**. The key is not saved. Leave the terminal open.
3. If asked by Windows Firewall, allow Python on private networks. TCP 8000 and mDNS UDP 5353 must be available. Keep the ESP32 and computer on the same LAN; no IP editing is needed.
4. Upload the gateway sketch and open Serial Monitor at **115200 baud**.
5. In the dashboard, select **Connect ESP32** and enter the same device key. New LoRa packets will populate gauges and graphs. HTTP status 200 means a packet was accepted.

For manual startup, first install discovery with `python -m pip install -r requirements.txt`. Then, in Windows PowerShell:

```powershell
$env:ESP32_DEVICE_KEY = "YOUR_PRIVATE_KEY_AT_LEAST_16_CHARACTERS"
python server.py --host 0.0.0.0 --port 8000
```

macOS/Linux:

```sh
export ESP32_DEVICE_KEY='YOUR_PRIVATE_KEY_AT_LEAST_16_CHARACTERS'
python3 server.py --host 0.0.0.0 --port 8000
```

The server uses HTTP on a trusted LAN. Do not port-forward it to the internet. GitHub Pages cannot run the Python server; use its local URL. Prevent the computer from sleeping. Guest Wi-Fi, AP isolation and some hotspots block mDNS; use a LAN that permits multicast or the optional manual URL fallback.

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
| Waiting for ESP32 | Radio node transmitting T/H/S format; gateway Wi-Fi; start.bat running; same LAN and firewall. |
| HTTP 401 | Identical device key in all three places. |
| HTTP 400 | Sensor values within ranges; S must be a percentage. |
| Negative HTTP code | Computer reachable, discovery allowed (UDP 5353), port 8000, server running, no guest-Wi-Fi isolation. |
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

Run `python -m unittest discover -s tests` and `node tests/history.test.cjs`. Server ingestion and optional soil temperature, graph gaps, statistics, CSV, and command gating are covered. Actual ESP32 compilation, Wi-Fi portal, multicast discovery, LoRa hardware and browser rendering must still be verified on your equipment.
