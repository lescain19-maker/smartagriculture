# Smart Agric — local ESP32 dashboard

Your ESP32 sends real sensor readings directly to a Python server on your computer. The dashboard, database, graphs, and pump commands stay on your local network. **Blynk is not used.** No Python packages or JavaScript CDN dependencies are required.

## What is included

- Four live gauges and four trend graphs with minimum, average, and maximum values.
- 15-minute / one-hour / all-loaded graph views, missing-data gaps, and CSV export.
- SQLite telemetry storage on your computer with seven-day retention (pruned when new data arrives). The dashboard loads the latest 720 records from the last hour on connection, then collects new readings. CSV exports the currently loaded records.
- Device freshness status: telemetry older than 15 seconds is stale and pump-on is disabled.
- Pump commands with firmware feedback, a default-off startup, and a firmware connection timeout.
- Session-only dashboard key; no saved credentials in the browser.

## 1. Start the server on your computer

Install **Python 3.10+**, download/clone this repository, and open a terminal in its folder.

Create your own random key of at least 16 characters. You can generate one with `python -c "import secrets; print(secrets.token_hex(24))"`. Keep it private and reuse the same value in the server, firmware, and dashboard.

**Windows PowerShell** (use `py` instead of `python` if needed):

```powershell
$env:ESP32_DEVICE_KEY = "PASTE_YOUR_PRIVATE_RANDOM_KEY"
python server.py --host 0.0.0.0 --port 8000
```

**macOS / Linux:**

```sh
export ESP32_DEVICE_KEY='PASTE_YOUR_PRIVATE_RANDOM_KEY'
python3 server.py --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** on this computer. On another device on the same network, use **http://YOUR_COMPUTER_LAN_IP:8000**.

Find your computer's IPv4 address using `ipconfig` on Windows, or your network settings on macOS/Linux. For example, if it is `192.168.1.100`, the ESP32 server URL is `http://192.168.1.100:8000`. **Do not put localhost or 0.0.0.0 in the ESP32 config.**

Allow Python/inbound TCP port 8000 on your **private** network firewall. Keep the ESP32 and computer on the same network; guest Wi-Fi/client isolation can block access. Keep the computer awake and the server running. Reserve its IP in your router if possible.

This server uses HTTP for a trusted local network. Do not expose it through router port forwarding or on the public internet. GitHub Pages cannot run this Python server or accept your local ESP32 telemetry; open the Python server's URL instead.

## 2. Wire and configure your ESP32

The example firmware assumes a **DHT22** for air temperature/humidity, a **DS18B20** for soil temperature, and an **analog capacitive moisture sensor**. If your sensor models differ, adapt their drivers before uploading. Example GPIOs are for a classic ESP32 and must be checked against your actual board.

| Sensor | Example GPIO | Notes |
| --- | --- | --- |
| DHT22 data | 4 | Set DHT_MODEL to your actual model. Use the sensor's required data pull-up. |
| DS18B20 data | 18 | Normally needs a 4.7 kΩ pull-up to 3.3 V. |
| Moisture analog output | 34 | Use an ADC1 input compatible with Wi-Fi on your board. |
| Relay control | 26 | Verify active-high/active-low before enabling. |

Use suitable power, a common ground, and ESP32-compatible signal voltage (at most 3.3 V). Power the pump through a properly rated relay/driver and supply, never an ESP32 GPIO. Disconnect pump power while verifying relay behavior.

1. Install Arduino IDE and Espressif's ESP32 board support; select your exact board and USB port.
2. Install **DHT sensor library by Adafruit**, **Adafruit Unified Sensor**, **OneWire**, **DallasTemperature**, and **ArduinoJson 7**.
3. Open `firmware/SmartAgric/SmartAgric.ino`.
4. Copy `config.example.h` to `config.h` in the same folder. This file is ignored by Git.
5. Enter Wi-Fi credentials, `SERVER_URL` with the computer's LAN IP, and `DEVICE_KEY` matching `ESP32_DEVICE_KEY`.
6. Verify all GPIOs, sensor models, and relay active level. Leave `RELAY_CONFIGURED false` until checked.
7. Upload and open Serial Monitor at **115200 baud**.

## 3. Calibrate before trusting soil moisture

Moving away from Blynk does not fix faulty wiring, incorrect sensor conversions, or missing calibration.

1. With the moisture probe in your chosen dry reference condition, record several `Raw moisture` readings from Serial Monitor. Set `MOISTURE_DRY_RAW` to their stable average.
2. Repeat in your chosen wet/saturated reference condition and set `MOISTURE_WET_RAW`. Keep electronics and connectors dry.
3. Set `MOISTURE_CALIBRATED true` and upload again. The endpoints must differ. Until calibrated, the sketch prints raw readings and deliberately withholds telemetry.
4. Compare air/soil temperatures and humidity against a known reference. DHT NaN or DS18B20 −127 °C indicates a sensor problem. Invalid readings are withheld, so the dashboard becomes stale rather than displaying made-up values.

Moisture percentage is **relative to these calibration endpoints**, not laboratory volumetric water content. Values outside the endpoints are clamped with a Serial warning. Server range validation catches malformed/out-of-range data; plausible but inaccurate sensor values still require physical calibration.

## 4. Connect the dashboard

1. Keep the Python server running and open **http://localhost:8000**.
2. Select **Connect ESP32** and enter your local device key.
3. The dashboard loads recent stored history and polls every two seconds.
4. The ESP32 publishes every five seconds. Serial Monitor should show **Telemetry HTTP status: 200**.
5. When telemetry arrives, gauges populate and graphs begin updating. No Blynk token or virtual pins are needed.

| Symptom | Check |
| --- | --- |
| Waiting for ESP32 | Sketch uploaded, calibration enabled, sensors valid, Wi-Fi connected. |
| HTTP 401 | Server/firmware/dashboard keys must match exactly. |
| Negative HTTP code / connection timeout | Computer LAN IP, port, firewall, same network, server running. |
| HTTP 400 | JSON field names, numeric ranges, booleans and uptime. |
| Telemetry stale | No valid packet for 15 seconds; check Serial Monitor. |
| Pump unavailable | Relay configuration is disabled in firmware. |
| Strange values | Sensor model, wiring, pull-ups, power, raw ADC values, calibration. |

## 5. Pump behavior

After confirming your relay wiring/active level, set `RELAY_CONFIGURED true` and upload. The dashboard sends a requested state to the local server; the ESP32 fetches it every two seconds and reports its applied relay state in telemetry. The label can show **Command pending device confirmation** until the ESP32 reports back.

The sketch requests off on startup, switches off on Wi-Fi loss, and switches off if no valid command response arrives for 15 seconds. The server returns an off command when telemetry is stale. These are software controls; power loss, stuck relays, and physical flow require suitable hardware design/feedback. The dashboard reports firmware relay state, not measured water flow.

## HTTP API (for existing firmware)

Every API request needs the header `X-Device-Key: YOUR_KEY`. Send JSON with `Content-Type: application/json`.

**POST `/api/telemetry`**, every five seconds:

```json
{
  "soil_moisture": 53.2,
  "soil_temperature": 22.6,
  "air_temperature": 25.1,
  "humidity": 61.8,
  "pump": false,
  "pump_available": true,
  "uptime_ms": 125000
}
```

The numbers above illustrate the format only; firmware must replace them with actual measurements. All four sensor values must be finite numbers. Allowed ranges: moisture/humidity 0–100; temperatures −40–125 °C. `pump` and `pump_available` must be booleans; `uptime_ms` is a nonnegative integer.

- **GET `/api/command`** → `{"pump": false}`. Firmware applies this request and reports its state in the next telemetry packet.
- **GET `/api/status`** → latest sample, freshness, age, requested pump state.
- **GET `/api/history?minutes=60`** → up to 720 most recent samples in the requested period (1–10080 minutes).
- **POST `/api/pump`** with `{"pump": true}` → queue a command; pump-on is rejected if telemetry is stale or control unavailable.

Timestamps are server receive times; the computer clock should be correct. This version supports **one ESP32 per server instance**, with no cloud ingestion or Blynk connection. Local readings live in `data/telemetry.sqlite3`, which is ignored by Git.

## Verification

Run `python -m unittest discover -s tests` and `node tests/history.test.cjs`. JavaScript can be checked with `node --check app.js`, `node --check charts.js`, and `node --check history.js`. Physical sensor accuracy, firmware compilation, relay behavior, and browser rendering still need verification with your actual hardware and board configuration.
