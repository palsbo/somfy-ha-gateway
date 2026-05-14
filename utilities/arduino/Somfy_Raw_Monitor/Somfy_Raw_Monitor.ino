#include <openrts.hpp>
#include <U8g2lib.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include "driver/gpio.h"
#include "esp_timer.h"

// --- Hardware Konfiguration for T3 V1.6.1 ---
#define OPENRTS_RADIO_CS   18
#define OPENRTS_RADIO_RST  23
#define OPENRTS_RADIO_DATA 32  // Baseret på din fungerende ESPHome YAML

#define SCK_PIN   5
#define MISO_PIN  19
#define MOSI_PIN  27

#define SHOW_RAW  // Viser puls-dump i Serial Monitor

// --- Serial ---
// 115200 er ofte for langsomt til rå puls-dumps.
#define SERIAL_BAUD 115200

// --- Raw dump tuning ---
// MIN_VALID_PULSE_US filtrerer de mange 50-100 us glitches væk, før raw capture starter.
// RAW_START_* gør, at vi først logger, når vi ser en puls der ligner Somfy wakeup/sync.
#define RAW_DUMP_SIZE       512
#define MIN_VALID_PULSE_US  300
#define RAW_START_MIN_US    2000
#define RAW_START_MAX_US    6000
#define RAW_END_GAP_US      5000

// --- Display ---
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0);

// --- Globale Objekter ---
RTSRadio_SX1278 radio(OPENRTS_RADIO_CS);
RTSFrameBuilder frameBuilder;
RTSRemoteStore_Memory remoteStore;
RTSFrame *lastFrame = nullptr;

char lastStatus[64] = "System Klar";
bool shouldRedraw = true;
unsigned long lastFrameTime = 0;

// --- ISR Puls Buffer ---
struct RxPulse {
  bool level;
  uint32_t duration_us;
};

// Øget fra 128 til 1024 for at undgå overflow ved bursts.
static const int RX_BUF_SIZE = 1024;
static volatile RxPulse s_rx_buf[RX_BUF_SIZE];
static volatile int s_rx_head = 0;
static volatile int s_rx_tail = 0;
static volatile int64_t s_last_edge_us = 0;
static volatile bool s_last_level = true;
static volatile uint32_t s_rx_overflow_count = 0;

// --- Raw dump buffer ---
// Pulser printes samlet efter en lang pause, i stedet for én for én i realtid.
struct RawDumpPulse {
  bool level;
  uint32_t duration_us;
};

static RawDumpPulse rawDump[RAW_DUMP_SIZE];
static int rawDumpCount = 0;
static bool rawDumpOverflow = false;
static bool rawCaptureActive = false;

// --- ISR ---
static void IRAM_ATTR rx_isr(void *arg) {
  int64_t now = esp_timer_get_time();
  bool level = (bool)gpio_get_level((gpio_num_t)(intptr_t)arg);

  if (s_last_edge_us > 0) {
    uint32_t dur = (uint32_t)(now - s_last_edge_us);
    int next = (s_rx_head + 1) % RX_BUF_SIZE;

    if (next != s_rx_tail) {
      s_rx_buf[s_rx_head].level = s_last_level;
      s_rx_buf[s_rx_head].duration_us = dur;
      s_rx_head = next;
    } else {
      s_rx_overflow_count++;
    }
  }

  s_last_level = level;
  s_last_edge_us = now;
}

void rx_isr_install(int pin) {
  gpio_config_t cfg = {};
  cfg.intr_type = GPIO_INTR_ANYEDGE;
  cfg.pin_bit_mask = (1ULL << pin);
  cfg.mode = GPIO_MODE_INPUT;
  cfg.pull_up_en = GPIO_PULLUP_DISABLE;
  cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
  gpio_config(&cfg);

  esp_err_t err = gpio_install_isr_service(0);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    Serial.printf("gpio_install_isr_service failed: %d\n", err);
  }

  s_last_level = gpio_get_level((gpio_num_t)pin);
  s_last_edge_us = esp_timer_get_time();

  gpio_isr_handler_add((gpio_num_t)pin, rx_isr, (void *)(intptr_t)pin);
}

// --- Hjælpefunktioner ---
void setStatus(const char *msg) {
  strncpy(lastStatus, msg, sizeof(lastStatus) - 1);
  lastStatus[sizeof(lastStatus) - 1] = '\0';
  shouldRedraw = true;
}

void drawOLED() {
  display.setDrawColor(1);
  display.drawBox(0, 0, display.getWidth(), 16);

  display.setDrawColor(0);
  display.setCursor(18, 3);
  display.print("Somfy RAW Monitor");

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

void flushRawDump() {
#ifndef SHOW_RAW
  rawDumpCount = 0;
  rawDumpOverflow = false;
  rawCaptureActive = false;
  return;
#else
  if (rawDumpCount == 0) {
    rawDumpOverflow = false;
    rawCaptureActive = false;
    return;
  }

  Serial.print("PULSES ");

  if (rawDumpOverflow) {
    Serial.print("[RAW_OVERFLOW] ");
  }

  uint32_t isrOverflowSnapshot = s_rx_overflow_count;
  if (isrOverflowSnapshot > 0) {
    Serial.printf("[ISR_OVERFLOW=%lu] ", (unsigned long)isrOverflowSnapshot);
  }

  for (int i = 0; i < rawDumpCount; i++) {
    Serial.print(rawDump[i].level ? "+" : "-");
    Serial.print(rawDump[i].duration_us);
    Serial.print(" ");
  }

  Serial.println();

  rawDumpCount = 0;
  rawDumpOverflow = false;
  rawCaptureActive = false;
#endif
}

void addPulseToRawDump(bool level, uint32_t duration_us) {
#ifndef SHOW_RAW
  return;
#else
  // Når vi ikke allerede optager, ignorerer vi korte glitches.
  // Det fjerner typisk de mange +56/-57 us støjpulser fra SX1278 DATA.
  if (!rawCaptureActive && duration_us < MIN_VALID_PULSE_US) {
    return;
  }

  // Start kun raw capture, når en puls ligner starten på en Somfy RTS burst.
  // Dine gyldige dumps starter typisk med en positiv/high puls omkring +2500 us.
  // Derfor må capture IKKE starte på f.eks. -2160 us støj.
  if (!rawCaptureActive) {
    if (level == true && duration_us >= RAW_START_MIN_US && duration_us <= RAW_START_MAX_US) {
      rawCaptureActive = true;
      rawDumpCount = 0;
      rawDumpOverflow = false;
    } else {
      return;
    }
  }

  if (rawDumpCount < RAW_DUMP_SIZE) {
    rawDump[rawDumpCount].level = level;
    rawDump[rawDumpCount].duration_us = duration_us;
    rawDumpCount++;
  } else {
    rawDumpOverflow = true;
  }
#endif
}

void printDecodedFrame(RTSFrame *frame) {
  Serial.printf("RX: %06X | CMD: %-10s | Roll: %d\n",
                frame->remote_address,
                rts_command_to_string(frame->command),
                frame->rolling_code);

#ifdef SHOW_RAW
  // Dette er ikke de oprindelige radio-pulser.
  // Det er kun en visning af de dekodede frame-felter.
  Serial.printf("DECODED_FIELDS: CMD=%s ROLL=%u ADDR=%06X\n",
                rts_command_to_string(frame->command),
                frame->rolling_code,
                frame->remote_address);
#endif
}

// --- Setup ---
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(500);

  // 1. Display start
  display.begin();
  display.setFont(u8g2_font_6x10_tf);
  display.setFontPosTop();
  setStatus("Booting...");

  display.firstPage();
  do {
    drawOLED();
  } while (display.nextPage());

  // 2. SPI og Radio Reset
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, OPENRTS_RADIO_CS);

  pinMode(OPENRTS_RADIO_RST, OUTPUT);
  digitalWrite(OPENRTS_RADIO_RST, LOW);
  delay(100);
  digitalWrite(OPENRTS_RADIO_RST, HIGH);
  delay(100);

  // 3. Radio start
  radio.begin();
  radio.setMode(RTS_RADIO_MODE_RECEIVE);
  Serial.println("Radio OK");

  // 4. Callback når en Somfy-ramme genkendes
  frameBuilder.setFrameCallback([](RTSFrame *frame, uint8_t repeat, uint32_t dur, void *user) {
    if (lastFrame) {
      delete lastFrame;
      lastFrame = nullptr;
    }

    lastFrame = new RTSFrame(frame->command, frame->rolling_code, frame->remote_address);
    lastFrameTime = millis();

    printDecodedFrame(frame);

    char st[32];
    snprintf(st, sizeof(st), "RX %06X", frame->remote_address);
    setStatus(st);
  }, NULL);

  // 5. Start interrupt-lytning på radioens data-pind
  rx_isr_install(OPENRTS_RADIO_DATA);

  setStatus("Listening");
  Serial.println("System Klar - Lytter på 433.42MHz");
  Serial.printf("Serial baud: %d\n", SERIAL_BAUD);
}

// --- Loop ---
void loop() {
  // Behandl pulser fra ISR-bufferen.
  while (s_rx_tail != s_rx_head) {
    RxPulse p;

    // Kort kritisk sektion: hent én puls atomisk fra ring-bufferen.
    noInterrupts();
    p.level = s_rx_buf[s_rx_tail].level;
    p.duration_us = s_rx_buf[s_rx_tail].duration_us;
    s_rx_tail = (s_rx_tail + 1) % RX_BUF_SIZE;
    interrupts();

    // Gem raw puls i RAM. Print først efter frame/burst-pause.
    // Raw loggeren starter kun, når pulsen ligner en rigtig Somfy burst.
    addPulseToRawDump(p.level, p.duration_us);

    // Send alle pulser videre til OpenRTS-dekoderen.
    // Vigtigt: Vi filtrerer ikke her, så dekoderen får samme input som før.
    frameBuilder.handlePulse(p.level, p.duration_us);

    // Lang pause betyder typisk slut på en Somfy burst/frame.
    if (rawCaptureActive && p.duration_us > RAW_END_GAP_US) {
      flushRawDump();
    }
  }

  // Opdater display.
  if (shouldRedraw) {
    display.firstPage();
    do {
      drawOLED();
    } while (display.nextPage());
    shouldRedraw = false;
  }

  // Ryd info på display efter 15 sekunders inaktivitet.
  if (lastFrame && millis() - lastFrameTime > 15000) {
    delete lastFrame;
    lastFrame = nullptr;
    setStatus("Listening");
  }

  yield();
}
