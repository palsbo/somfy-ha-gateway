#define OPENRTS_BOARD_TTGO_LORA32_V21

//#define HAS_WEB
//#define HAS_MQTT

#include <openrts.hpp>
#include <U8g2lib.h>
#include <WiFi.h>

#ifdef HAS_WEB
#include "web.h"
WEB web;
#endif

#ifdef HAS_MQTT
#include "mqtt.h"
MQTT mqtt;
#endif

#define RADIO

// --- WiFi ---
const char* ssid     = "palsbo";
const char* password = "fedusmus";

// --- Display ---
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0);
unsigned long lastFrameTime = 0;
RTSRadio_SX1278 radio(OPENRTS_RADIO_CS);
RTSPulseSource_GPIO pulseSource(OPENRTS_RADIO_DATA);
RTSFrameBuilder     frameBuilder;
RTSRemoteStore_NVS remoteStore;
RTSRemote remote(new RTSPulseOutput_GPIO(OPENRTS_RADIO_DATA), &remoteStore);

struct CommandMessage {
  uint32_t address;
  rts_command command;
  uint16_t rollingCode;
  bool isIncoming; 
};

QueueHandle_t msgQueue;
RTSFrame *lastFrame = nullptr;
char lastStatus[64] = "System Klar";
bool shouldRedraw = true;

void setStatus(const char* msg) {
  strncpy(lastStatus, msg, sizeof(lastStatus) - 1);
  shouldRedraw = true;
}

void drawOLED() {
  display.setDrawColor(1);
  display.drawBox(0, 0, display.getWidth(), 16);
  display.setDrawColor(0);
  display.setCursor(25, 3);
  display.print("Somfy Monitor");
  display.setDrawColor(1);

  if (lastFrame) {
    display.setCursor(0, 22); 
    display.print("Addr: "); 
    display.print(lastFrame->remote_address, HEX);
    display.setCursor(0, 34); 
    display.print("Cmd : "); 
    display.print(rts_command_to_string(lastFrame->command));
    display.setCursor(65, 34); 
    display.print("Roll: "); 
    display.print(lastFrame->rolling_code);
  }
  display.setCursor(0, 52);
  display.print(lastStatus);
}

#ifdef HAS_MQTT
void mqttOnMessage(char* topic, char* payload) {
  CommandMessage msg;
  msg.address = strtoul(topic + strlen("somfy/cmd/"), NULL, 16);
  if (strcasecmp(payload, "Up") == 0) msg.command = RTS_COMMAND_UP;
  else if (strcasecmp(payload, "Down") == 0) msg.command = RTS_COMMAND_DOWN;
  else if (strcasecmp(payload, "Prog") == 0) msg.command = RTS_COMMAND_PROG;
  else msg.command = RTS_COMMAND_MY;
  msg.isIncoming = false;
  xQueueSend(msgQueue, &msg, 0);
}
#endif

#ifdef HAS_WEB
void webOnMessage(uint8_t num, char* payload, char* txbuf) {
  char temp[64]; strncpy(temp, payload, 63);
  char* addrStr = strtok(temp, " ");
  char* cmdStr = strtok(NULL, " ");
  if (addrStr && cmdStr) {
    CommandMessage msg;
    msg.address = strtoul(addrStr, NULL, 16);
    if (strcasecmp(cmdStr, "Up") == 0) msg.command = RTS_COMMAND_UP;
    else if (strcasecmp(cmdStr, "Down") == 0) msg.command = RTS_COMMAND_DOWN;
    else if (strcasecmp(cmdStr, "Prog") == 0) msg.command = RTS_COMMAND_PROG;
    else msg.command = RTS_COMMAND_MY;
    msg.isIncoming = false;
    xQueueSend(msgQueue, &msg, 0);
    strcpy(txbuf, "OK");
  }
}
#endif

void setup() {
  Serial.begin(115200);
  delay(500);
  msgQueue = xQueueCreate(20, sizeof(CommandMessage));

  display.begin();
  display.setFont(u8g2_font_6x10_tf);
  display.setFontPosTop();

  Serial.print("\n\nConnecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { Serial.print("."); delay(500); }
  Serial.printf("\nConnected to %s\n", WiFi.localIP().toString());

  #ifdef HAS_MQTT
  mqtt.onMessage(mqttOnMessage);
  mqtt.begin();
  #endif

  #ifdef HAS_WEB
  web.onMessage(webOnMessage);
  web.begin();
  Serial.println("Webserver started.");
  #endif

  radio.begin();
  radio.setMode(RTS_RADIO_MODE_RECEIVE);
  pulseSource.attach(&frameBuilder);
  pulseSource.enable();

  frameBuilder.setFrameCallback([](RTSFrame* frame, uint8_t repeat, uint32_t dur, void* user) {
    CommandMessage msg;
    msg.address = frame->remote_address;
    msg.command = frame->command;
    msg.rollingCode = frame->rolling_code;
    msg.isIncoming = true;
    xQueueSendFromISR(msgQueue, &msg, NULL);
  });

  setStatus("Listening");
}

void loop() {

  #ifdef HAS_MQTT
  mqtt.loop();
  static unsigned long lastMqttCheck = 0;
  if (millis() - lastMqttCheck > 5000) {
    mqtt.reconnect();
    lastMqttCheck = millis();
  }
  #endif

  CommandMessage currentMsg;
  if (xQueueReceive(msgQueue, &currentMsg, 0) == pdPASS) {
    if (currentMsg.isIncoming) {
      if (lastFrame) delete lastFrame;
      lastFrame = new RTSFrame(currentMsg.command, currentMsg.rollingCode, currentMsg.address);
      lastFrameTime = millis();
      char buf[128];
      snprintf(buf, sizeof(buf), "Modtaget: %06X [%s] Roll: %d", currentMsg.address, rts_command_to_string(currentMsg.command), currentMsg.rollingCode);
      Serial.println(buf);

      #ifdef HAS_WEB
      web.broadcast(buf);
      #endif

      #ifdef HAS_MQTT
      char mqttBuf[128];
      snprintf(mqttBuf, sizeof(mqttBuf), "{\"addr\":\"%06X\",\"cmd\":\"%s\",\"roll\":%d}", 
               currentMsg.address, rts_command_to_string(currentMsg.command), currentMsg.rollingCode);
      mqtt.publish("somfy/rx", mqttBuf);
      #endif

      char st[32];
      snprintf(st, sizeof(st), "RX %06X", currentMsg.address);
      setStatus(st);
    } 
    else {
      pulseSource.disable();
      radio.setMode(RTS_RADIO_MODE_TRANSMIT);
      vTaskDelay(10 / portTICK_PERIOD_MS); 
      remote.sendCommand(currentMsg.address, currentMsg.command, false);
      char buf[128];
      snprintf(buf, sizeof(buf), "Sendt: %06X [%s]", currentMsg.address, rts_command_to_string(currentMsg.command));
      Serial.println(buf);
      radio.setMode(RTS_RADIO_MODE_RECEIVE);
      pulseSource.enable();
      char st[64];
      snprintf(st, sizeof(st), "TX %06X %s", currentMsg.address, rts_command_to_string(currentMsg.command));
      setStatus(st);

      #ifdef HAS_WEB
      web.broadcast(st);
      #endif

      #ifdef HAS_MQTT
      mqtt.publish("somfy/stat/sent", st);
      #endif

    }
  }

  if (shouldRedraw) {
    display.firstPage();
    do { drawOLED(); } while (display.nextPage());
    shouldRedraw = false;
  }
  if (lastFrame && millis() - lastFrameTime > 15000) {
      delete lastFrame;
      lastFrame = nullptr;
      shouldRedraw = true;
  }
  pulseSource.update();
  yield();
}
