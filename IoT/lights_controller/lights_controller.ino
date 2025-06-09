#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Wi-Fi credentials
const char* ssid = "test";
const char* password = "12345678";

// MQTT broker details
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

// Timing and state variables
unsigned long phase_end_time = 0;
bool phase_active = false;
String current_phase = "";
const unsigned long YELLOW_DURATION = 3000; // 3 seconds for yellow phase
const unsigned long GREEN_DURATION_MIN = 10000; // 10 seconds minimum for green
const unsigned long GREEN_DURATION_MAX = 30000; // 30 seconds maximum for green

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

  // Check if current phase has ended
  if (phase_active && millis() >= phase_end_time) {
    phase_active = false;
    if (current_phase == "EW_green") {
      // Transition from green to yellow
      set_traffic_lights("EW_yellow");
      phase_end_time = millis() + YELLOW_DURATION;
      phase_active = true;
      current_phase = "EW_yellow";
    } else if (current_phase == "EW_yellow") {
      // Transition from yellow to red
      default_safe_state();
      current_phase = "";
    }
    Serial.println("Phase transitioned automatically");
  }
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

  // Extract phase
  const char* phase = doc["phase"];
  if (phase) {
    String new_phase = String(phase);
    Serial.print("Received phase: ");
    Serial.println(new_phase);

    // Set traffic lights based on trigger
    set_traffic_lights(new_phase);
    current_phase = new_phase;

    // Set initial phase duration
    if (new_phase == "EW_green") {
      // Random duration between 10-30 seconds for green phase
      unsigned long green_duration = random(GREEN_DURATION_MIN, GREEN_DURATION_MAX + 1);
      phase_end_time = millis() + green_duration;
      phase_active = true;
      Serial.print("Green phase duration set to: ");
      Serial.println(green_duration / 1000);
    } else if (new_phase == "EW_yellow") {
      phase_end_time = millis() + YELLOW_DURATION;
      phase_active = true;
      Serial.println("Yellow phase duration set to 3 seconds");
    } else {
      // For NS_green or NS_yellow, default to red immediately
      default_safe_state();
      current_phase = "";
      phase_active = false;
      Serial.println("Invalid phase, defaulting to red");
    }
  } else {
    Serial.println("No phase received, defaulting to red");
    default_safe_state();
    current_phase = "";
  }
}

void set_traffic_lights(String phase) {
  // Turn off all LEDs
  digitalWrite(EW_RED_PIN, LOW);
  digitalWrite(EW_YELLOW_PIN, LOW);
  digitalWrite(EW_GREEN_PIN, LOW);

  // Set LEDs based on phase
  if (phase == "EW_green") {
    digitalWrite(EW_GREEN_PIN, HIGH);
  } else if (phase == "EW_yellow") {
    digitalWrite(EW_YELLOW_PIN, HIGH);
  } else {
    // For NS_green, NS_yellow, or invalid phase, set EW red
    digitalWrite(EW_RED_PIN, HIGH);
  }
}

void default_safe_state() {
  // Turn off all LEDs except EW red
  digitalWrite(EW_RED_PIN, HIGH);
  digitalWrite(EW_YELLOW_PIN, LOW);
  digitalWrite(EW_GREEN_PIN, LOW);
}