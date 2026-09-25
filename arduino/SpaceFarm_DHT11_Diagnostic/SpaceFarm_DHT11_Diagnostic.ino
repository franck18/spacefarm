// SpaceFarm: diagnostic USB du DHT11 sur Arduino Yun.
// Cablage requis, grille face a soi et pattes vers le bas :
// 1 = 5V, 2 = D2, 3 = libre, 4 = GND.
// Resistance externe de 10 kohms entre les pattes 1 et 2.
// Bibliotheque : DHT sensor library, par Adafruit.
#include <DHT.h>

const uint8_t DHT_PIN = 2;
const unsigned long SAMPLE_INTERVAL_MS = 2000;
DHT sensor(DHT_PIN, DHT11);
unsigned long lastSample = 0;
unsigned long attempts = 0;
unsigned long successes = 0;

void setup() {
  Serial.begin(9600);
  // Ne bloque pas indefiniment si aucun moniteur USB n'est ouvert.
  unsigned long started = millis();
  while (!Serial && millis() - started < 5000UL) {
    delay(10);
  }
  sensor.begin();
  Serial.println(F("SpaceFarm | Diagnostic DHT11 | DATA=D2 | USB=9600"));
  Serial.println(F("Requis: VCC=5V, GND=GND, resistance 10 kohms VCC-DATA."));
  Serial.println(F("Une mesure toutes les 2 secondes. Aucune mesure simulee."));
  lastSample = millis();
}

void loop() {
  if (!Serial || millis() - lastSample < SAMPLE_INTERVAL_MS) {
    return;
  }
  lastSample = millis();
  float humidity = sensor.readHumidity();
  float temperature = sensor.readTemperature();
  attempts++;
  const bool valid = !isnan(humidity) && !isnan(temperature);
  if (valid) successes++;

  Serial.print(F("{\"sensor\":\"DHT11\",\"pin\":2,\"uptimeMs\":"));
  Serial.print(millis());
  Serial.print(F(",\"attempt\":"));
  Serial.print(attempts);
  Serial.print(F(",\"successfulReads\":"));
  Serial.print(successes);
  if (valid) {
    Serial.print(F(",\"status\":\"ok\",\"temperature\":"));
    Serial.print(temperature, 1);
    Serial.print(F(",\"humidity\":"));
    Serial.print(humidity, 1);
    Serial.println(F("}"));
  } else {
    Serial.println(F(",\"status\":\"error\",\"temperature\":null,\"humidity\":null,\"message\":\"Lecture impossible : verifier 5V, GND, DATA sur D2 et resistance 10 kohms.\"}"));
  }
}
