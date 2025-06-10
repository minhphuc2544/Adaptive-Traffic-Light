#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Wi-Fi credentials (replace with your network details)
const char* ssid = "test";
const char* password = "12345678";

// MQTT broker details (from .env)
const char* mqtt_server = "192.168.179.8";
const int mqtt_port = 1883;
const char* mqtt_topic = "iot/response";

// GPIO pins for EW traffic light LEDs
#define EW_RED_PIN 25
#define EW_YELLOW_PIN 33
#define EW_GREEN_PIN 32

// WiFi and MQTT clients
WiFiClient espClient;
PubSubClient client(espClient);

// Function prototypes
void setup_wifi();
void reconnect();
void callback(char* topic, byte* payload, unsigned int length);
void set_traffic_lights(String phase);
void default_safe_state();

void setup() {
  // Initialize serial for debugging
  Serial.begin(115200);

  // Initialize LED pins as outputs
  pinMode(EW_RED_PIN, OUTPUT);
  pinMode(EW_YELLOW_PIN, OUTPUT);
  pinMode(EW_GREEN_PIN, OUTPUT);

  // Set default safe state (EW red ON)
  default_safe_state();

  // Connect to Wi-Fi
  setup_wifi();

  // Set MQTT server and callback
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // No timing logic needed - ESP32 responds immediately to MQTT signals
  delay(100); // Small delay to prevent excessive CPU usage
}

void setup_wifi() {
  delay(10);
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32TrafficLight-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      client.subscribe(mqtt_topic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  // Allocate buffer for payload
  char message[length + 1];
  for (unsigned int i = 0; i < length; i++) {
    message[i] = (char)payload[i];
  }
  message[length] = '\0';

  // Parse JSON
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.print("deserializeJson() failed: ");
    Serial.println(error.c_str());
    return;
  }

  // Extract phase (duration is no longer needed)
  const char* phase = doc["phase"];

  if (phase) {
    String phaseStr = String(phase);
    Serial.print("Received phase change signal: ");
    Serial.println(phaseStr);

    // Only process EW phases, ignore NS phases
    if (phaseStr.startsWith("EW_")) {
      set_traffic_lights(phaseStr);
    } else {
      Serial.println("Ignoring NS phase (not relevant for this ESP32)");
    }
  } else {
    Serial.println("Invalid phase received");
    default_safe_state();
  }
}

void set_traffic_lights(String phase) {
  // Turn off all LEDs first
  digitalWrite(EW_RED_PIN, LOW);
  digitalWrite(EW_YELLOW_PIN, LOW);
  digitalWrite(EW_GREEN_PIN, LOW);

  // Set LEDs based on EW phase only
  if (phase == "EW_green") {
    digitalWrite(EW_GREEN_PIN, HIGH);
    Serial.println("EW Traffic Light: GREEN ON");
  } else if (phase == "EW_yellow") {
    digitalWrite(EW_YELLOW_PIN, HIGH);
    Serial.println("EW Traffic Light: YELLOW ON");
  } else if (phase == "EW_red") {
    digitalWrite(EW_RED_PIN, HIGH);
    Serial.println("EW Traffic Light: RED ON");
  } else {
    // For any invalid or unknown EW phase, default to safe state
    default_safe_state();
    Serial.println("Unknown EW phase, defaulting to safe state");
  }
}

void default_safe_state() {
  // Turn off all LEDs except EW red
  digitalWrite(EW_RED_PIN, HIGH);
  digitalWrite(EW_YELLOW_PIN, LOW);
  digitalWrite(EW_GREEN_PIN, LOW);
  Serial.println("EW Traffic Light: SAFE STATE (RED ON)");
}