#include <WiFi.h>
#include "secrets.h"
#include "LocalConnection.h"
#include <SPI.h>
#include <LoRa.h>

#define LORA_SCK 18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS 5
#define LORA_RST 14
#define LORA_DIO0 4

#define LED_WIFI 25
#define LED_LORA 26
#define LED_PUMP 27

char ssid[] = WIFI_SSID;
char pass[] = WIFI_PASSWORD;

// Pump command from your local dashboard. Existing LoRa command logic retained.
void onLocalPumpCommand(int state) {
  digitalWrite(LED_PUMP, state);
  LoRa.beginPacket();
  LoRa.print(state ? "PUMP:1" : "PUMP:0");   // sent to the node
  LoRa.endPacket();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_WIFI, OUTPUT);
  pinMode(LED_LORA, OUTPUT);
  pinMode(LED_PUMP, OUTPUT);

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed");
    while (true);
  }
  localBegin(ssid, pass, onLocalPumpCommand);
}

void loop() {
  localRun();
  digitalWrite(LED_WIFI, localConnected());

  int size = LoRa.parsePacket();
  if (size) {
    String msg = "";
    while (LoRa.available()) msg += (char)LoRa.read();

    digitalWrite(LED_LORA, HIGH);

    // Example payload from node: "T:27.5,H:60.2,S:43"
    float t = 0, h = 0; int soil = 0;
    if (sscanf(msg.c_str(), "T:%f,H:%f,S:%d", &t, &h, &soil) == 3) {
      localPublish(t, h, soil);
    }
    delay(50);
    digitalWrite(LED_LORA, LOW);
  }
}
