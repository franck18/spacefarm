// SpaceFarm 2080 : JSON sur USB et envoi Wi-Fi vers le Raspberry Pi.
#include <DHT.h>
#include <Bridge.h>
#include <Process.h>
#include <Servo.h>

const char API_URL[] = "http://192.168.41.88:8000/api/ingest";
const float SENSOR_HEIGHT_CM = 30.0; // Distance du capteur à la base du pot, à mesurer.
const uint8_t DHT_PIN = 2, LED_PIN = 4, LIGHT_PIN = A0, WATER_PIN = A1;
const uint8_t WATER_POWER_PIN = 3; // VCC de la sonde d'eau uniquement.
const unsigned long WATER_SETTLE_MS = 10UL;
const uint8_t TRIG_PIN = 7, ECHO_PIN = 8, SERVO_PIN = 9;
// Servo.h occupe Timer1 : D10 perd son PWM sur la Yún. D11 reste disponible.
const uint8_t FAN_ENABLE_PIN = 11;
const unsigned long SAMPLE_INTERVAL_MS = 2000UL;

DHT dht(DHT_PIN, DHT11);
Servo hatch;
Process request;
unsigned long lastSample = 0;
unsigned long waterPoweredAt = 0;
bool waterSampling = false;
bool sending = false;
int servoAngle = 0, fanPwm = 0;
bool lightingOn = false;
unsigned long lastAck = 0;
unsigned long manualUntil = 0;
String responseBody;

struct Measurements {
  float temperature, humidity, distanceCm, plantHeightCm;
  int lightRaw, waterRaw;
};

void readDHT(Measurements &m) {
  m.humidity = dht.readHumidity();
  m.temperature = dht.readTemperature();
}

int readAnalogAverage(uint8_t pin) {
  analogRead(pin); // Écarter la première conversion après changement de voie.
  long total = 0;
  for (uint8_t i = 0; i < 8; ++i) {
    total += analogRead(pin);
    delayMicroseconds(200);
  }
  return total / 8;
}

int readLight() { return readAnalogAverage(LIGHT_PIN); }
int readWaterLevel() {
  int value = readAnalogAverage(WATER_PIN);
  digitalWrite(WATER_POWER_PIN, LOW); // Couper la sonde après la lecture.
  return value;
}

// Deux lectures cohérentes au minimum ; un écho absent expire après 25 ms.
float readUltrasonic() {
  float v[3];
  uint8_t n = 0;
  for (uint8_t i = 0; i < 3; ++i) {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);
    unsigned long us = pulseIn(ECHO_PIN, HIGH, 25000UL);
    float cm = us * 0.0343f / 2.0f;
    if (us && cm >= 2.0f && cm <= 400.0f) v[n++] = cm;
  }
  if (n < 2) return NAN;
  if (v[0] > v[1]) { float t = v[0]; v[0] = v[1]; v[1] = t; }
  if (n == 2) return v[1] - v[0] <= 8.0f ? (v[0] + v[1]) / 2.0f : NAN;
  if (v[1] > v[2]) { float t = v[1]; v[1] = v[2]; v[2] = t; }
  if (v[0] > v[1]) { float t = v[0]; v[0] = v[1]; v[1] = t; }
  if (v[1] - v[0] > 8.0f && v[2] - v[1] > 8.0f) return NAN;
  return v[1]; // Médiane : supprime un écho aberrant.
}

void controlVentilation(float temperature) {
  // DHT invalide : ventilateur arrêté, trappe conservée à sa dernière position.
  int targetFan = 0;
  if (!isnan(temperature)) {
    int targetAngle = temperature < 26.0f ? 0 : (temperature < 28.0f ? 45 : 90);
    targetFan = temperature < 28.0f ? 0 : (temperature <= 30.0f ? 150 : 255);
    bool manualActive = manualUntil && (long)(manualUntil - millis()) > 0;
    if (!manualActive && targetAngle != servoAngle) {
      hatch.write(targetAngle);
      servoAngle = targetAngle;
    }
  }
  if (targetFan != fanPwm) {
    analogWrite(FAN_ENABLE_PIN, targetFan);
    fanPwm = targetFan;
  }
}

void appendNumber(String &json, float value) {
  if (isnan(value)) json += F("null");
  else json += String(value, 1);
}

void sendData(const Measurements &m) {
  // Une ligne USB = un objet JSON décodable par json.loads().
  String line;
  line.reserve(200);
  line = F("{\"temperature\":"); appendNumber(line, m.temperature);
  line += F(",\"humidite\":"); appendNumber(line, m.humidity);
  line += F(",\"luminosite\":"); line += m.lightRaw;
  line += F(",\"niveau_eau\":"); line += m.waterRaw;
  line += F(",\"distance_plante\":"); appendNumber(line, m.distanceCm);
  line += F(",\"hauteur_plante\":"); appendNumber(line, m.plantHeightCm);
  line += F(",\"servo\":"); line += servoAngle;
  line += F(",\"ventilateur\":"); line += fanPwm;
  line += F(",\"eclairage\":"); line += lightingOn ? 1 : 0;
  line += '}';
  Serial.println(line);

  // Garder le format HTTP déjà utilisé par le backend du Pi.
  if (sending) return;
  String payload;
  payload.reserve(330);
  payload = F("{\"sensor\":\"spacefarm-yun\",\"ack\":");
  payload += lastAck;
  payload += F(",\"readings\":{\"temperature\":");
  appendNumber(payload, m.temperature);
  payload += F(",\"humidity\":"); appendNumber(payload, m.humidity);
  payload += F(",\"light_raw\":{\"value\":"); payload += m.lightRaw;
  payload += F(",\"unit\":\"ADC\"},\"water_raw\":{\"value\":"); payload += m.waterRaw;
  payload += F(",\"unit\":\"ADC\"},\"distance_plante\":{\"value\":");
  appendNumber(payload, m.distanceCm);
  payload += F(",\"unit\":\"cm\"},\"hauteur_plante\":{\"value\":");
  appendNumber(payload, m.plantHeightCm);
  payload += F(",\"unit\":\"cm\"},\"servo\":"); payload += servoAngle;
  payload += F(",\"ventilateur\":"); payload += fanPwm;
  payload += F(",\"lighting\":"); payload += lightingOn ? 1 : 0;
  payload += F("}}");

  request.begin("curl");
  request.addParameter("--silent");
  request.addParameter("--connect-timeout"); request.addParameter("3");
  request.addParameter("--max-time"); request.addParameter("8");
  request.addParameter("--header"); request.addParameter("Content-Type: application/json");
  request.addParameter("--data-binary"); request.addParameter(payload);
  request.addParameter(API_URL);
  request.runAsynchronously();
  responseBody = "";
  sending = true;
}

// Le Pi transmet les ordres de servo ou d'éclairage dans sa réponse HTTP.
void readCommand() {
  int key = responseBody.indexOf("\"command\"");
  if (key < 0) return;
  int colon = responseBody.indexOf(':', key + 9);
  int quote = responseBody.indexOf('"', colon + 1);
  if (colon < 0 || quote < 0) return;
  int start = quote + 1;
  int end = responseBody.indexOf('"', start);
  if (end < 0) return;
  String command = responseBody.substring(start, end);
  int first = command.indexOf(' ');
  int second = command.indexOf(' ', first + 1);
  if (first < 0 || second < 0) return;
  String action = command.substring(0, first);
  int value = command.substring(first + 1, second).toInt();
  unsigned long id = command.substring(second + 1).toInt();
  if (id == 0) return;
  if (action == "lighting" && (value == 0 || value == 1)) {
    lightingOn = value == 1;
    digitalWrite(LED_PIN, lightingOn ? HIGH : LOW);
    lastAck = id;
  } else if (action == "servo" && value >= 0 && value <= 180) {
    if (value != servoAngle) hatch.write(value);
    servoAngle = value;
    manualUntil = millis() + 30000UL; // Retour à l'automatique après 30 s.
    lastAck = id;
  }
}

void setup() {
  Serial.begin(115200);
  digitalWrite(WATER_POWER_PIN, LOW);
  pinMode(WATER_POWER_PIN, OUTPUT);
  pinMode(WATER_PIN, INPUT);
  digitalWrite(WATER_PIN, LOW); // Pas de pull-up sur le signal analogique.
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(LED_PIN, LOW);
  pinMode(LED_PIN, OUTPUT);
  pinMode(FAN_ENABLE_PIN, OUTPUT);
  analogWrite(FAN_ENABLE_PIN, 0);
  hatch.write(0);
  hatch.attach(SERVO_PIN);
  dht.begin();
  Bridge.begin();
  lastSample = millis() - SAMPLE_INTERVAL_MS;
}

void loop() {
  if (sending) {
    while (request.available()) {
      char c = request.read();
      if (responseBody.length() < 160) responseBody += c;
    }
    if (!request.running()) {
      readCommand();
      request.close();
      sending = false;
    }
  }
  unsigned long now = millis();
  if (!waterSampling) {
    if (now - lastSample < SAMPLE_INTERVAL_MS) return;
    lastSample = now;
    digitalWrite(WATER_POWER_PIN, HIGH);
    waterPoweredAt = now;
    waterSampling = true;
    return;
  }
  // Stabiliser la sonde sans bloquer le traitement des réponses Wi-Fi.
  if (now - waterPoweredAt < WATER_SETTLE_MS) return;
  Measurements m;
  m.waterRaw = readWaterLevel();
  waterSampling = false;
  readDHT(m);
  m.lightRaw = readLight();
  m.distanceCm = readUltrasonic();
  m.plantHeightCm = isnan(m.distanceCm) ? NAN : SENSOR_HEIGHT_CM - m.distanceCm;
  if (!isnan(m.plantHeightCm) && m.plantHeightCm < 0) m.plantHeightCm = NAN;
  controlVentilation(m.temperature);
  sendData(m);
}
