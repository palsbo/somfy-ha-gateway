#pragma once

#include "esphome.h"
#include "esphome/components/remote_transmitter/remote_transmitter.h"
#include "esphome/components/remote_base/remote_base.h"
#include <ArduinoJson.h>

namespace somfy_cc1101_v2 {

static const char *const TAG = "somfy_cc1101_v2";

// ===================== Somfy RTS frame decoder =====================
// Bruges af decode_raw_pulses() kaldt fra remote_receiver on_raw lambda.
//
// Signal-konventioner (ESPHome native cc1101 + remote_receiver):
//   - Positiv puls (mark)  = carrier ON  = HIGH
//   - Negativ puls (space) = carrier OFF = LOW
//
// Manchester-kodning (Somfy RTS):
//   - LOW-HIGH transition = bit 1
//   - HIGH-LOW transition = bit 0
//
// SW sync LOW (~640µs) smelter typisk med første data-halvdel
// (også carrier-OFF for bit=1), og ses som ~1280µs.

class SomfyFrameDecoder {
 public:
  bool     frame_ready  = false;
  uint32_t address      = 0;
  uint8_t  command      = 0;
  uint16_t rolling_code = 0;

  void reset() {
    state_       = IDLE;
    second_half_ = false;
    bit_count_   = 0;
    frame_ready  = false;
    memset(obf_, 0, sizeof(obf_));
  }

  void handle_pulse(bool level, uint32_t dur) {
    switch (state_) {

      case IDLE:
        if (level && near(dur, 4550)) {
          state_ = SW_SYNC_LO;
        }
        break;

      case SW_SYNC_LO:
        if (!level && near(dur, 640)) {
          // Ren SW sync LOW
          state_       = DATA;
          bit_count_   = 0;
          second_half_ = false;
          memset(obf_, 0, sizeof(obf_));
        } else if (!level && near(dur, 1280)) {
          // SW sync LOW (640µs) smeltet med første data-halvdel (carrier-OFF)
          state_       = DATA;
          bit_count_   = 0;
          second_half_ = false;
          memset(obf_, 0, sizeof(obf_));
          feed_half_(false);
        } else {
          state_ = IDLE;
        }
        break;

      case DATA:
        if (near(dur, 640)) {
          feed_half_(level);
        } else if (near(dur, 1280)) {
          feed_half_(level);
          if (state_ == DATA) feed_half_(level);
        } else if (dur > 5000) {
          if (second_half_ && bit_count_ == 55) {
            // End-of-stream: lang pause = carrier-off afslutter sidste bit
            feed_half_(false);
          } else {
            reset();
            if (level && near(dur, 4550)) state_ = SW_SYNC_LO;
          }
        } else {
          reset();
        }
        break;
    }
  }

 private:
  enum State { IDLE, SW_SYNC_LO, DATA };
  State   state_       = IDLE;
  bool    second_half_ = false;
  bool    first_half_  = false;
  int     bit_count_   = 0;
  uint8_t obf_[7]      = {};

  static bool near(uint32_t v, uint32_t target) {
    return v > (target * 6 / 10) && v < (target * 14 / 10);
  }

  void set_bit_(int n, bool val) {
    int byte_idx = n / 8;
    int bit_idx  = 7 - (n % 8);
    if (val) obf_[byte_idx] |=  (1u << bit_idx);
    else     obf_[byte_idx] &= ~(1u << bit_idx);
  }

  void feed_half_(bool val) {
    if (!second_half_) {
      first_half_  = val;
      second_half_ = true;
    } else {
      bool bit;
      if (!first_half_ && val) {
        bit = true;   // LOW-HIGH = 1
      } else if (first_half_ && !val) {
        bit = false;  // HIGH-LOW = 0
      } else {
        reset();
        return;
      }
      set_bit_(bit_count_, bit);
      bit_count_++;
      second_half_ = false;
      if (bit_count_ == 56) try_decode_();
    }
  }

  void try_decode_() {
    uint8_t frame[7];
    frame[0] = obf_[0];
    for (int i = 1; i < 7; i++) frame[i] = obf_[i] ^ obf_[i - 1];

    // Verificer kun checksum (key byte varierer mellem remotes: 0xA4, 0xA5, 0xA7 m.fl.)
    uint8_t chk = 0;
    for (int i = 0; i < 7; i++) chk ^= frame[i] ^ (frame[i] >> 4);
    if ((chk & 0x0F) != 0) {
      ESP_LOGD(TAG, "RX: checksum fejl (key=0x%02X chk=0x%02X)", frame[0], chk & 0x0F);
      reset();
      return;
    }

    command      = (frame[1] >> 4) & 0x0F;
    rolling_code = ((uint16_t)frame[2] << 8) | frame[3];
    address      = (uint32_t)frame[4]
                 | ((uint32_t)frame[5] << 8)
                 | ((uint32_t)frame[6] << 16);

    frame_ready = true;
    state_ = IDLE;
  }
};

// ===================== Kommando-strenge =====================

static uint8_t command_from_string(const char *s) {
  if (strcasecmp(s, "my") == 0) return 0x1;
  if (strcasecmp(s, "stop") == 0) return 0x1;
  if (strcasecmp(s, "up") == 0) return 0x2;
  if (strcasecmp(s, "my_up") == 0) return 0x3;
  if (strcasecmp(s, "down") == 0) return 0x4;
  if (strcasecmp(s, "dn") == 0) return 0x4;
  if (strcasecmp(s, "my_down") == 0) return 0x5;
  if (strcasecmp(s, "up_down") == 0) return 0x6;
  if (strcasecmp(s, "prog") == 0) return 0x8;
  ESP_LOGW(TAG, "Unknown command '%s', using MY", s);
  return 0x1;
}

static const char *command_to_string(uint8_t cmd) {
  switch (cmd) {
    case 0x1: return "My";
    case 0x2: return "Up";
    case 0x3: return "My+Up";
    case 0x4: return "Down";
    case 0x5: return "My+Down";
    case 0x6: return "Up+Down";
    case 0x8: return "Prog";
    default:  return "?";
  }
}

// ===================== Hovedkomponent =====================

class SomfyCC1101V2 : public esphome::Component {
 public:
  esphome::text_sensor::TextSensor *rx_sensor{nullptr};

  void set_transmitter(esphome::remote_transmitter::RemoteTransmitterComponent *tx) {
    transmitter_ = tx;
  }

  // Kaldes fra YAML remote_receiver on_raw:
  //   id(my_somfy).decode_raw_pulses(x);
  void decode_raw_pulses(std::vector<int32_t> &pulses) {
    decoder_.reset();
    for (int32_t p : pulses) {
      bool     level = (p > 0);
      uint32_t dur   = (uint32_t)(p > 0 ? p : -p);
      decoder_.handle_pulse(level, dur);
      if (decoder_.frame_ready) {
        on_frame_();
        decoder_.reset();
      }
    }
  }

  // TX JSON format:
  //   Normal: {"address":"A1B2C3","command":"up","rolling_code":103,"repeat":2}
  //   PROG:   {"address":"A1B2C3","command":"prog","rolling_code":103,"repeat":25,"interval_ms":140}
  void parse_and_send(std::string json) {
    ESP_LOGI(TAG, "TX JSON: %s", json.c_str());

    if (!transmitter_) {
      ESP_LOGE(TAG, "Ingen transmitter sat!");
      return;
    }

    JsonDocument doc;
    auto err = deserializeJson(doc, json);
    if (err) {
      ESP_LOGE(TAG, "JSON parse error: %s", err.c_str());
      return;
    }

    const char *address_s = doc["address"] | "";
    const char *command_s = doc["command"] | "my";

    uint32_t address  = strtoul(address_s, nullptr, 16);
    uint8_t  addr_lo  = (address)       & 0xFF;
    uint8_t  addr_mid = (address >> 8)  & 0xFF;
    uint8_t  addr_hi  = (address >> 16) & 0xFF;

    uint16_t rolling_code =
      doc["rolling_code"].is<int>()
        ? doc["rolling_code"].as<int>()
        : doc["rolling"].as<int>();

    uint8_t cmd     = command_from_string(command_s);
    bool    is_prog = (cmd == 0x8);

    int repeat = is_prog ? 25 : 2;
    if (doc["repeat"].is<int>()) repeat = doc["repeat"].as<int>();

    uint32_t interval_ms = is_prog ? 140 : 0;
    if (doc["interval_ms"].is<int>()) interval_ms = doc["interval_ms"].as<int>();

    uint8_t frame[7];
    build_frame_(cmd, rolling_code, addr_hi, addr_mid, addr_lo, frame);

    uint8_t obf[7];
    memcpy(obf, frame, 7);
    for (int i = 1; i < 7; i++) obf[i] ^= obf[i - 1];

    char addr_buf[8];
    snprintf(addr_buf, sizeof(addr_buf), "%06X", address);

    ESP_LOGI(TAG, "TX -> addr=%s cmd=%s rolling=%u repeat=%d interval=%ums",
             addr_buf, command_to_string(cmd), rolling_code, repeat, interval_ms);

    auto call = transmitter_->transmit();
    auto *data = call.get_data();
    data->reset();

    add_first_frame_(data, obf);
    for (int i = 0; i < repeat; i++) {
      add_repeat_frame_(data, obf, interval_ms);
    }

    call.set_send_times(1);
    call.perform();

    publish_tx_(addr_buf, command_to_string(cmd), rolling_code, repeat);
    ESP_LOGI(TAG, "TX complete");
  }

 private:
  esphome::remote_transmitter::RemoteTransmitterComponent *transmitter_{nullptr};
  SomfyFrameDecoder decoder_;

  static void build_frame_(
      uint8_t cmd, uint16_t rolling_code,
      uint8_t addr_hi, uint8_t addr_mid, uint8_t addr_lo,
      uint8_t *frame)
  {
    frame[0] = 0xA7;
    frame[1] = (uint8_t)(cmd << 4);
    frame[2] = (uint8_t)(rolling_code >> 8);
    frame[3] = (uint8_t)(rolling_code & 0xFF);
    frame[4] = addr_lo;
    frame[5] = addr_mid;
    frame[6] = addr_hi;

    uint8_t chk = 0;
    for (int i = 0; i < 7; i++) chk ^= frame[i] ^ (frame[i] >> 4);
    frame[1] |= (chk & 0x0F);
  }

  static void add_manchester_bits_(
      esphome::remote_base::RemoteTransmitData *data,
      const uint8_t *obf)
  {
    static constexpr uint32_t SYMBOL = 640;
    for (int i = 0; i < 56; i++) {
      bool bit = (obf[i / 8] >> (7 - (i % 8))) & 1;
      if (bit) {
        data->mark(SYMBOL);
        data->space(SYMBOL);
      } else {
        data->space(SYMBOL);
        data->mark(SYMBOL);
      }
    }
  }

  static void add_first_frame_(
      esphome::remote_base::RemoteTransmitData *data,
      const uint8_t *obf)
  {
    data->mark(9415);
    data->space(89565);
    for (int i = 0; i < 2; i++) {
      data->mark(2560);
      data->space(2560);
    }
    data->mark(4550);
    data->space(640);
    add_manchester_bits_(data, obf);
  }

  static void add_repeat_frame_(
      esphome::remote_base::RemoteTransmitData *data,
      const uint8_t *obf,
      uint32_t interval_ms)
  {
    data->space(30415 + interval_ms * 1000);
    for (int i = 0; i < 7; i++) {
      data->mark(2560);
      data->space(2560);
    }
    data->mark(4550);
    data->space(640);
    add_manchester_bits_(data, obf);
  }

  void on_frame_() {
    char addr_buf[8];
    snprintf(addr_buf, sizeof(addr_buf), "%06X", decoder_.address);

    ESP_LOGI(TAG, "RX <- addr=%s cmd=%s rolling=%u",
             addr_buf,
             command_to_string(decoder_.command),
             decoder_.rolling_code);

    if (!rx_sensor) return;

    JsonDocument doc;
    doc["protocol"]     = "somfy_rts";
    doc["dir"]          = "rx";
    doc["address"]      = addr_buf;
    doc["command"]      = command_to_string(decoder_.command);
    doc["rolling_code"] = decoder_.rolling_code;

    std::string out;
    serializeJson(doc, out);
    rx_sensor->publish_state(out);
  }

  void publish_tx_(
      const char *addr_buf, const char *command_s,
      uint16_t rolling_code, int repeat)
  {
    if (!rx_sensor) return;

    JsonDocument doc;
    doc["protocol"]     = "somfy_rts";
    doc["dir"]          = "tx";
    doc["address"]      = addr_buf;
    doc["command"]      = command_s;
    doc["rolling_code"] = rolling_code;
    doc["repeat"]       = repeat;

    std::string out;
    serializeJson(doc, out);
    ESP_LOGI(TAG, "TX JSON <- %s", out.c_str());
    rx_sensor->publish_state(out);
  }
};

} // namespace somfy_cc1101_v2