# Smart Agric

Responsive ESP32 dashboard with four sensor gauges and a manual water pump switch, using the Blynk Cloud HTTPS API.

## Run

Serve this directory with any static web host, or run `python3 -m http.server 8000` and open `http://localhost:8000`.

For GitHub Pages, select **Settings → Pages → Deploy from a branch → main → / (root)** and save. Publishing is a separate step; uploading this repository does not enable Pages.

## Connect your ESP32

1. Ensure your ESP32 firmware is connected to Blynk Cloud.
2. Configure the virtual datastreams below in your Blynk template.
3. Open the dashboard and select **Connect ESP32**.
4. Enter the Blynk server (such as `blynk.cloud` or your regional Blynk server) and your device Auth Token from Blynk Console → Devices → Device Info.

The Auth Token stays only in the tab's memory and is sent directly to Blynk over HTTPS. Reloading clears it. Do not commit device tokens or Wi-Fi passwords.

| Reading | Virtual pin | Range |
| --- | --- | --- |
| Soil moisture | V4 | 0–100 % |
| Soil temperature | V0 | −40–125 °C |
| Air temperature | V5 | −40–125 °C |
| Humidity | V3 | 0–100 % |
| Water pump | V6 | Integer: 0 off, 1 on |

Your existing firmware must publish sensor readings and handle `BLYNK_WRITE(V6)` to control the relay. GPIO pins, relay active level, sensor models, and wiring are hardware-specific; firmware is not included.

Readings refresh every five seconds. Pump control is enabled only when Blynk reports the device online. V6 is the Blynk datastream state, not physical confirmation that the pump is running. Loss of dashboard connectivity does not automatically switch the pump off; implement any required timeout in ESP32 firmware.

## Verification and limitations

JavaScript syntax has been checked with `node --check app.js`. Live ESP32 connectivity and browser rendering have not been verified. Direct browser access requires Blynk API cross-origin support; if the API or browser blocks these requests, a server-side integration is needed.
