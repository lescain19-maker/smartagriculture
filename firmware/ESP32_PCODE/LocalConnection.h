#pragma once
// Connection layer only. LoRa pins, packet parsing and commands remain in the sketch.
void localBegin(const char* ssid, const char* password, void (*onPumpCommand)(int));
void localRun();
bool localConnected();
bool localPublish(float airTemperature, float humidity, int soilMoisture);
