# ESPHome Gateway

This folder contains ESPHome gateway examples for Somfy HA Gateway.

The ESPHome gateways expose the JSON TX/RX entities used by the Home Assistant integration. Home Assistant owns cover configuration and rolling codes; the ESPHome device only sends and receives RF frames.

## Available Gateway Options

| Gateway | Radio | Use when |
|---|---|---|
| TTGO LoRa32 | SX1276/SX1278 433 MHz | You already use the original TTGO LoRa32 reference gateway |
| ESP32 + CC1101 | CC1101 / E07-M1101D 433 MHz | You want to reuse ESP32 + CC1101 hardware, including ESPSomfyRTS-style wiring |

## Common Installation Steps

1. Copy the relevant YAML file from this folder to your Home Assistant ESPHome configuration directory.
2. Copy any required custom component folder from `esphome/components/` to your ESPHome `components/` directory.
3. Update Wi-Fi secrets if needed.
4. Check the device name and pin configuration.
5. Compile and flash the device with ESPHome Builder.
6. Confirm that Home Assistant discovers the ESPHome device.
7. In Somfy HA Gateway V3, select the gateway's JSON TX and RX entities.

Expected entities are similar to:

```text
text.<device_name>_somfy_json_tx
sensor.<device_name>_somfy_json_rx
```

The exact names may vary depending on the ESPHome device name and Home Assistant entity naming.

## TTGO LoRa32 Gateway

Use this option for TTGO LoRa32 433 MHz hardware with an SX1276/SX1278 transceiver.

The TTGO gateway is the original reference gateway and normally does not require hardware changes.
### TTGO Lora32 Gateway - in a box
![ESP32+CC1101](../docs/Lora32_box.png)


### TTGO Installation

1. Copy the TTGO YAML file from this folder to your ESPHome configuration directory.
2. Copy the required TTGO custom component folder from `components/` to your ESPHome `components/` directory.
3. Install and flash from ESPHome Builder.
4. Select the generated JSON TX and RX entities in the Somfy HA Gateway V3 integration.

> Note: file and component folder names should match the names in this repository. If you rename the YAML file, the ESPHome device name and generated entity names may also change.

## ESP32 + CC1101 Gateway

Use this option for ESP32 + CC1101 hardware, including E07-M1101D modules and similar 433 MHz CC1101 boards.

The CC1101 gateway is configured through the `substitutions:` section in the YAML file. This is the preferred place to change ESP32 board type, device name and GPIO pin assignments.
### ESP32 + CC1101 Gateway - in a box
![ESP32+CC1101](../docs/cc1101_box.png)

## Default CC1101 Wiring

The default CC1101 template assumes this wiring:

| Pin | E07-M1101D / CC1101 | ESP32 | Purpose |
|---|---:|---|
| 1 | GND | GND | Ground |
| 2 | VCC | 3V3 | Power |
| 3 | GDO0 | GPIO26 | TX output |
| 4 | CSN | GPIO5 | SPI chip select |
| 5 | SCK | GPIO18 | SPI clock |
| 6 | MOSI | GPIO23 | SPI MOSI |
| 7 | MISO | GPIO19 | SPI MISO |
| 8 | GDO2 | GPIO35 | RX input |

Important notes:

* Follow the labels on your CC1101 board, not only the physical pin position.
* Different CC1101 breakout boards may use different physical layouts.
* `GDO0` is used for TX.
* `GDO2` is used for RX.
* GPIO35 is input-only on many ESP32 boards, so it is suitable for RX but not TX.
* Use only 3.3V power and logic for the CC1101 module.

## CC1101 Pin Configuration

Adjust pins in the YAML `substitutions:` section:

```yaml
substitutions:
  my_name: somfy-cc1101-gw
  my_friendly_name: Somfy CC1101 Gateway
  my_board: esp32dev

  # SPI pins
  cc_cs: GPIO5
  cc_clk: GPIO18
  cc_mosi: GPIO23
  cc_miso: GPIO19

  # CC1101 GDO pins
  cc_gdo0: GPIO26
  cc_gdo2: GPIO35
```

The substitutions are then used by the ESPHome sections that need those pins:

```yaml
spi:
  clk_pin: $cc_clk
  mosi_pin: $cc_mosi
  miso_pin: $cc_miso

cc1101:
  cs_pin: $cc_cs
  frequency: 433.42MHz

remote_transmitter:
  pin: $cc_gdo0

remote_receiver:
  pin: $cc_gdo2
```

If your hardware uses different pins, change only the values in `substitutions:` unless you intentionally want to change the YAML structure.

## CC1101 Installation

1. Copy `somfy_cc1101_gateway.yaml` to your ESPHome configuration directory.
2. Copy the required custom component folder from `components/` to your ESPHome `components/` directory.
3. Update the `substitutions:` section:
   * `my_name`
   * `my_friendly_name`
   * `my_board`
   * CC1101 SPI and GDO pins
4. Update Wi-Fi secrets if needed.
5. Compile and flash from ESPHome Builder.
6. Confirm that Home Assistant discovers the ESPHome device.
7. In Somfy HA Gateway V3, select:
   * `text.<device_name>_somfy_json_tx`
   * `sensor.<device_name>_somfy_json_rx`

## Troubleshooting

### ESPHome cannot compile

Check:

* The custom component folder has been copied to the correct ESPHome `components/` directory.
* The YAML file references the same component name as the component folder.
* The ESPHome version is compatible with the `min_version` in the YAML.
* The selected ESP32 board matches your hardware.

### CC1101 TX does not work

Check:

* `GDO0` is connected to the configured TX GPIO.
* The TX GPIO is output-capable.
* The CC1101 module has stable 3.3V power.
* The antenna is connected.
* The ESPHome log shows that a JSON TX payload was received.

### CC1101 RX does not work

Check:

* `GDO2` is connected to the configured RX GPIO.
* The RX GPIO is input-capable.
* The CC1101 module is the expected 433 MHz variant.
* The remote is close to the receiver during testing.
* The ESPHome log shows that the device has entered RX mode after transmit.

## JSON TX/RX Payloads

The ESPHome gateway receives outgoing commands through the JSON TX text entity:

```json
{
  "address": "A1B2C3",
  "command": "up",
  "rolling_code": 103,
  "repeat": 2
}
```

The gateway publishes received Somfy RTS frames through the JSON RX sensor:

```json
{
  "protocol": "somfy_rts",
  "dir": "rx",
  "address": "A1B2C3",
  "command": "Up",
  "rolling_code": 1234
}
```

The full JSON protocol is documented in:

```text
../docs/protocol-json.md
```
