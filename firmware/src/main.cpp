#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include "esp_camera.h"
#include "secrets.h"

// AI-Thinker ESP32-CAM pin map.
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

constexpr int PIR_PIN = 13;
constexpr int BUZZER_PIN = 14;
constexpr bool BUZZER_ACTIVE_HIGH = true;
constexpr unsigned long HARD_CAP_MS = 3000;
constexpr unsigned long CONTROL_TIMEOUT_MS = 5000;

String deviceId;
uint32_t frameCounter = 0;
uint32_t lastGeneration = 0;
unsigned long lastCaptureAt = 0;
unsigned long lastControlAt = 0;
unsigned long buzzerOffAt = 0;

void setBuzzer(bool on) {
  digitalWrite(BUZZER_PIN, (on == BUZZER_ACTIVE_HIGH) ? HIGH : LOW);
  if (!on) buzzerOffAt = 0;
}

bool initCamera() {
  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM; config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM; config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM; config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = psramFound() ? 2 : 1;
  config.grab_mode = CAMERA_GRAB_LATEST;
  return esp_camera_init(&config) == ESP_OK;
}

String isoTimestamp() {
  // TODO(Firmware): sync NTP and return real UTC. Server rejects stale frames after integration.
  return "2026-10-03T00:00:00Z";
}

bool uploadFrame() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return false;
  const String boundary = "----SmartSecurityBoundary";
  String head = "--" + boundary + "\r\nContent-Disposition: form-data; name=\"frame_id\"\r\n\r\n" + String(frameCounter) +
    "\r\n--" + boundary + "\r\nContent-Disposition: form-data; name=\"captured_at\"\r\n\r\n" + isoTimestamp() +
    "\r\n--" + boundary + "\r\nContent-Disposition: form-data; name=\"pir_active\"\r\n\r\n" + (digitalRead(PIR_PIN) ? "true" : "false") +
    "\r\n--" + boundary + "\r\nContent-Disposition: form-data; name=\"frame\"; filename=\"frame.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";

  WiFiClient client;
  HTTPClient http;
  String url = String(SERVER_BASE_URL) + "/api/v1/devices/" + deviceId + "/frames";
  http.begin(client, url);
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  if (strlen(DEVICE_TOKEN)) http.addHeader("X-Device-Token", DEVICE_TOKEN);
  const size_t total = head.length() + fb->len + tail.length();
  uint8_t *body = static_cast<uint8_t *>(ps_malloc(total));
  if (!body) { esp_camera_fb_return(fb); http.end(); return false; }
  memcpy(body, head.c_str(), head.length());
  memcpy(body + head.length(), fb->buf, fb->len);
  memcpy(body + head.length() + fb->len, tail.c_str(), tail.length());
  int code = http.POST(body, total);
  free(body);
  esp_camera_fb_return(fb);
  http.end();
  frameCounter++;
  return code >= 200 && code < 300;
}

void pollCommands() {
  WiFiClient client;
  HTTPClient http;
  String url = String(SERVER_BASE_URL) + "/api/v1/devices/" + deviceId + "/commands?after_generation=" + String(lastGeneration);
  http.begin(client, url);
  if (strlen(DEVICE_TOKEN)) http.addHeader("X-Device-Token", DEVICE_TOKEN);
  int code = http.GET();
  if (code != 200) { http.end(); return; }
  JsonDocument doc;
  if (deserializeJson(doc, http.getString())) { http.end(); return; }
  lastControlAt = millis();
  for (JsonObject command : doc["commands"].as<JsonArray>()) {
    uint32_t generation = command["generation"] | 0;
    if (generation <= lastGeneration) continue;
    lastGeneration = generation;
    String action = command["action"] | "STOP";
    if (action == "START") {
      unsigned long duration = min<unsigned long>(command["duration_ms"] | 0, HARD_CAP_MS);
      setBuzzer(duration > 0);
      buzzerOffAt = millis() + duration;
    } else {
      setBuzzer(false);
    }
    // TODO(Firmware): POST ACK after executing/rejecting each command.
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  setBuzzer(false);
  deviceId = "door-" + String(static_cast<uint32_t>(ESP.getEfuseMac()), HEX);
  if (!initCamera()) ESP.restart();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { setBuzzer(false); delay(250); }
  lastControlAt = millis();
}

void loop() {
  const unsigned long now = millis();
  if (buzzerOffAt && static_cast<long>(now - buzzerOffAt) >= 0) setBuzzer(false);
  if (now - lastControlAt > CONTROL_TIMEOUT_MS) setBuzzer(false);
  if (WiFi.status() != WL_CONNECTED) { setBuzzer(false); delay(100); return; }

  const unsigned long captureInterval = digitalRead(PIR_PIN) ? 500 : 1000;
  if (now - lastCaptureAt >= captureInterval) {
    uploadFrame();
    lastCaptureAt = now;
  }
  pollCommands();
  delay(100);
}

