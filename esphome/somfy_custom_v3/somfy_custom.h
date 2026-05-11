#pragma once

#include "esphome.h"
#include <openrts.hpp>
#include <ArduinoJson.h>
#include <strings.h>
#include "driver/gpio.h"
#include "esp_timer.h"

namespace somfy_ns {

static rts_command command_from_string(const char *s) {
  if      (strcasecmp(s, "my")       == 0) return RTS_COMMAND_MY;
  else if (strcasecmp(s, "up")       == 0) return RTS_COMMAND_UP;
  else if (strcasecmp(s, "my_up")    == 0) return RTS_COMMAND_MY_UP;
  else if (strcasecmp(s, "down")     == 0) return RTS_COMMAND_DOWN;
  else if (strcasecmp(s, "my_down")  == 0) return RTS_COMMAND_MY_DOWN;
  else if (strcasecmp(s, "up_down")  == 0) return RTS_COMMAND_UP_DOWN;
  else if (strcasecmp(s, "prog")     == 0) return RTS_COMMAND_PROG;
  else if (strcasecmp(s, "sun_flag") == 0) return RTS_COMMAND_SUN_FLAG;
  else if (strcasecmp(s, "flag")     == 0) return RTS_COMMAND_FLAG;

  ESP_LOGW("somfy", "Ukendt kommando: '%s', bruger MY", s);
  return RTS_COMMAND_MY;
}

struct RxPulse {
  bool level;
  uint32_t duration_us;
};

static const int RX_BUF_SIZE = 128;
static volatile RxPulse s_rx_buf[RX_BUF_SIZE];
static volatile int s_rx_head = 0;
static volatile int s_rx_tail = 0;
static volatile int64_t s_last_edge_us = 0;
static volatile bool s_last_level = true;

static void IRAM_ATTR rx_isr(void *arg) {
  int64_t now = esp_timer_get_time();
  bool level = (bool) gpio_get_level((gpio_num_t)(intptr_t) arg);

  if (s_last_edge_us > 0) {
    uint32_t dur = (uint32_t)(now - s_last_edge_us);
    int next = (s_rx_head + 1) % RX_BUF_SIZE;

    if (next != s_rx_tail) {
      s_rx_buf[s_rx_head].level = s_last_level;
      s_rx_buf[s_rx_head].duration_us = dur;
      s_rx_head = next;
    }
  }

  s_last_level = level;
  s_last_edge_us = now;
}

static void rx_isr_install(int pin) {
  gpio_config_t cfg = {};
  cfg.intr_type = GPIO_INTR_ANYEDGE;
  cfg.pin_bit_mask = (1ULL << pin);
  cfg.mode = GPIO_MODE_INPUT;
  gpio_config(&cfg);

  esp_err_t err = gpio_install_isr_service(0);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    ESP_LOGE("somfy", "gpio_install_isr_service: %s", esp_err_to_name(err));
  }

  err = gpio_isr_handler_add((gpio_num_t) pin, rx_isr, (void *)(intptr_t) pin);
  if (err != ESP_OK) {
    ESP_LOGE("somfy", "gpio_isr_handler_add: %s", esp_err_to_name(err));
  }
}

class SomfyComponent : public esphome::Component {
 public:
  esphome::text_sensor::TextSensor *rx_sensor{nullptr};

  // Display state
  std::string disp_rx_addr = "-";
  std::string disp_rx_cmd = "-";
  std::string disp_rx_rc = "-";
  std::string disp_tx_addr = "-";
  std::string disp_tx_cmd = "-";
  std::string disp_status = "Klar";

  void setup() override {
    pinMode(OPENRTS_RADIO_CS, OUTPUT);
    digitalWrite(OPENRTS_RADIO_CS, HIGH);

    pinMode(OPENRTS_RADIO_RST, OUTPUT);
    digitalWrite(OPENRTS_RADIO_RST, HIGH);

    SPI.begin(5, 19, 27, 18);

    radio_.begin();
    radio_.setMode(RTS_RADIO_MODE_RECEIVE);

    frameBuilder_.setFrameCallback([](RTSFrame *frame, uint8_t, uint32_t, void *user) {
      static_cast<SomfyComponent *>(user)->on_frame_(frame);
    }, this);

    rx_isr_install(OPENRTS_RADIO_DATA);

    ESP_LOGI("somfy", "Somfy Gateway klar");
  }

  void loop() override {
    while (s_rx_tail != s_rx_head) {
      RxPulse p;
      p.level = s_rx_buf[s_rx_tail].level;
      p.duration_us = s_rx_buf[s_rx_tail].duration_us;
      s_rx_tail = (s_rx_tail + 1) % RX_BUF_SIZE;

      frameBuilder_.handlePulse(p.level, p.duration_us);
    }
  }

  // TX JSON format fra Home Assistant:
  //   {"protocol":"somfy_rts","dir":"tx","address":"A1B2C1","command":"up","rolling_code":103,"repeat":2}
  //   {"protocol":"somfy_rts","dir":"tx","address":"A1B2C1","command":"prog","rolling_code":103,"repeat":25,"interval_ms":140}
  //
  // Legacy accepteres også:
  //   "rolling" som alias for "rolling_code"
  //   "repeats" som alias for "repeat"
  //
  // address er altid hex-streng uden 0x.
  // Kommandoer: my, up, my_up, down, my_down, up_down, prog, sun_flag, flag
  void parse_and_send(std::string json) {
    if (json.empty()) return;

    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, json);
    if (err) {
      ESP_LOGE("somfy", "JSON fejl: %s", err.c_str());
      return;
    }

    if (!doc["address"].is<const char *>() || !doc["command"].is<const char *>()) {
      ESP_LOGE("somfy", "JSON mangler 'address' eller 'command'");
      return;
    }

    const char *address_s = doc["address"].as<const char *>();
    const char *command_s = doc["command"].as<const char *>();

    uint32_t address = strtoul(address_s, nullptr, 16);
    rts_command command = command_from_string(command_s);

    bool has_rolling_code = false;
    uint16_t rolling_code = 0;

    if (doc["rolling_code"].is<int>()) {
      rolling_code = (uint16_t) doc["rolling_code"].as<int>();
      has_rolling_code = true;
    } else if (doc["rolling"].is<int>()) {
      rolling_code = (uint16_t) doc["rolling"].as<int>();
      has_rolling_code = true;
    }

    if (has_rolling_code) {
      remoteStore_.setCode(address, rolling_code);
    }

    char addr_buf[8];
    snprintf(addr_buf, sizeof(addr_buf), "%06X", address);

    disp_tx_addr = addr_buf;
    disp_tx_cmd = rts_command_to_string(command);

    bool is_prog = (command == RTS_COMMAND_PROG);

    int repeat = 0;
    if (doc["repeat"].is<int>()) {
      repeat = doc["repeat"].as<int>();
    } else if (doc["repeats"].is<int>()) {
      repeat = doc["repeats"].as<int>();
    } else {
      repeat = is_prog ? 25 : 0;
    }

    if (repeat < 0) repeat = 0;
    if (repeat > 100) repeat = 100;

    uint32_t interval_ms = doc["interval_ms"] | 140;

    ESP_LOGI(
      "somfy",
      "TX -> addr=%s cmd=%s rolling=%s%u repeat=%d interval=%ums",
      addr_buf,
      rts_command_to_string(command),
      has_rolling_code ? "" : "internal:",
      has_rolling_code ? rolling_code : remoteStore_.getCode(address),
      repeat,
      interval_ms
    );

    gpio_isr_handler_remove((gpio_num_t) OPENRTS_RADIO_DATA);
    radio_.setMode(RTS_RADIO_MODE_TRANSMIT);
    vTaskDelay(10 / portTICK_PERIOD_MS);

    disp_status = std::string("TX: ") + rts_command_to_string(command);

    if (is_prog) {
      vTaskDelay(100 / portTICK_PERIOD_MS);
    }

    remote_.sendCommand(address, command, false);

    for (int i = 0; i < repeat; i++) {
      if (interval_ms > 0) {
        vTaskDelay(interval_ms / portTICK_PERIOD_MS);
      }
      remote_.sendCommand(address, command, true);
    }

    publish_tx_(addr_buf, command, has_rolling_code ? rolling_code : 0, repeat);

    radio_.setMode(RTS_RADIO_MODE_RECEIVE);
    s_last_edge_us = 0;
    gpio_isr_handler_add(
      (gpio_num_t) OPENRTS_RADIO_DATA,
      rx_isr,
      (void *)(intptr_t) OPENRTS_RADIO_DATA
    );
  }

 private:
  RTSRadio_SX1278 radio_{OPENRTS_RADIO_CS};
  RTSFrameBuilder frameBuilder_;
  RTSRemoteStore_Memory remoteStore_;
  RTSRemote remote_{new RTSPulseOutput_GPIO(OPENRTS_RADIO_DATA), &remoteStore_};

  void publish_tx_(const char *addr_buf, rts_command command, uint16_t rolling_code, int repeat) {
    if (!rx_sensor) return;

    JsonDocument doc;
    doc["protocol"] = "somfy_rts";
    doc["dir"] = "tx";
    doc["address"] = addr_buf;
    doc["command"] = rts_command_to_string(command);
    if (rolling_code > 0) {
      doc["rolling_code"] = rolling_code;
    }
    doc["repeat"] = repeat;

    std::string out;
    serializeJson(doc, out);
    ESP_LOGI("somfy", "TX JSON <- %s", out.c_str());
    rx_sensor->publish_state(out);
  }

  void on_frame_(RTSFrame *frame) {
    char addr_buf[8];
    snprintf(addr_buf, sizeof(addr_buf), "%06X", frame->remote_address);

    disp_rx_addr = addr_buf;
    disp_rx_cmd = rts_command_to_string(frame->command);

    char rc_buf[8];
    snprintf(rc_buf, sizeof(rc_buf), "%u", frame->rolling_code);
    disp_rx_rc = rc_buf;
    disp_status = "RX: " + disp_rx_cmd;

    if (!rx_sensor) return;

    JsonDocument doc;
    doc["protocol"] = "somfy_rts";
    doc["dir"] = "rx";
    doc["address"] = addr_buf;
    doc["command"] = rts_command_to_string(frame->command);
    doc["rolling_code"] = frame->rolling_code;

    std::string out;
    serializeJson(doc, out);
    ESP_LOGI("somfy", "RX <- %s", out.c_str());
    rx_sensor->publish_state(out);
  }
};

}  // namespace somfy_ns