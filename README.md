# Somfy HA Gateway

Home Assistant custom integration for controlling Somfy RTS covers through a replaceable RF gateway.

The integration separates Home Assistant state management from the RF hardware. Home Assistant owns cover configuration, rolling codes, repeat count, estimated position and device entities. The RF gateway acts as a mostly stateless transport adapter that sends and receives Somfy RTS frames using JSON.

> Status: early development / public testing.

## Features

* Home Assistant custom integration for Somfy RTS covers
* Local control through an ESPHome-based RF gateway
* Gateway-agnostic JSON TX/RX protocol
* Rolling code management in Home Assistant
* Estimated cover position based on configured travel times
* Add and remove covers from the integration options UI
* Cover configuration entities for address, rolling code, repeat count, timing and MY position
* Cover type selector for blind, awning, curtain and shutter
* PROG button entity per cover
* Optional RX support for receiving Somfy RTS frames
* ESPHome gateway examples for TTGO LoRa32 and ESP32 + CC1101 hardware

## Architecture

```text
Home Assistant integration
  - cover devices and entities
  - rolling code administration
  - repeat count
  - position estimation
  - movement state
  - MY position

RF gateway
  - receives JSON TX commands from Home Assistant
  - transmits Somfy RTS frames
  - optionally receives Somfy RTS frames
  - publishes JSON RX payloads back to Home Assistant
```

The RF gateway must not manage rolling codes. It should transmit the `rolling_code` value exactly as provided by Home Assistant.

```text
Home Assistant
  -> text.somfy_json_tx
  -> ESPHome RF gateway
  -> Somfy RTS cover

Somfy RTS remote
  -> ESPHome RF gateway
  -> sensor.somfy_json_rx
  -> Home Assistant
```

## Supported Gateway Hardware

### TTGO LoRa32 433 MHz / SX1278

This is the original reference gateway used during development.

Use this option if you already have a working TTGO LoRa32 433 MHz based gateway.

### ESP32 + CC1101 / E07-M1101D

This is the CC1101 gateway option for ESP32 + CC1101 hardware, including hardware similar to ESPSomfyRTS builds.

The CC1101 gateway uses the same JSON TX/RX contract as the TTGO gateway.

Other gateways may work if they implement the same JSON TX/RX protocol.

## Installation

### Manual Home Assistant installation

Copy the integration folder into your Home Assistant `custom_components` directory:

```text
config/
  custom_components/
    somfy_ha_gateway_v3/
      __init__.py
      manifest.json
      ...
```

Restart Home Assistant.

Then add the integration from:

```text
Settings → Devices & services → Add integration → Somfy HA Gateway V3
```

### HACS custom repository

Add this repository to HACS as a custom repository:

```text
https://github.com/palsbo/somfy-ha-gateway
```

Repository type:

```text
Integration
```

After installation, restart Home Assistant and add the integration from Devices & services.

## Initial Home Assistant Configuration

During setup, select:

* Gateway name
* TX text entity
* RX sensor or text entity

The TX entity is where Home Assistant writes outgoing Somfy RTS JSON commands.

The RX entity is where the RF gateway publishes received Somfy RTS JSON frames.

Example TTGO entities:

```text
text.ttgo_somfy_gateway_somfy_json_tx
sensor.ttgo_somfy_gateway_somfy_json_rx
```

Example CC1101 entities:

```text
text.somfy_cc1101_gw_somfy_json_tx
sensor.somfy_cc1101_gw_somfy_json_rx
```

Entity names may vary depending on the ESPHome device name and Home Assistant entity naming.

## Adding Covers

After the gateway has been configured:

```text
Settings → Devices & services → Somfy HA Gateway V3 → Configure → Add Somfy cover
```

For each cover, configure:

* Name
* Address
* Cover type
* Rolling code
* Repeat count
* Travel time out
* Travel time in
* MY position

The internal cover ID is generated automatically from the cover name and should remain stable.

## Cover Configuration Entities

Each cover exposes several entities:

```text
Cover
  - main cover entity

Configuration entities
  - Address
  - Observed addresses
  - Rolling code
  - Repeat
  - Position
  - Time out
  - Time in
  - MY position
  - Cover type
  - PROG button
```

Most cover settings are edited directly from the cover device page in Home Assistant.

## ESPHome Gateway Files

ESPHome gateway examples live in:

```text
esphome/
```

Custom ESPHome components live in:

```text
esphome/components/
```

For detailed ESPHome setup, wiring and flashing instructions, see:

```text
esphome/README.md
```

## ESP32 + CC1101 Gateway

The CC1101 gateway is intended for ESP32 + CC1101 hardware.

The default CC1101 gateway template assumes this wiring:

```text
E07-M1101D / CC1101    ESP32
--------------------------------
GND                    GND
VCC                    3V3
CSN                    GPIO5
SCK                    GPIO18
MOSI                   GPIO23
MISO                   GPIO19
GDO0 / TX              GPIO26
GDO2 / RX              GPIO35
```

Important:

* Follow the labels on your CC1101 board, not only the physical pin position.
* Many CC1101 breakout boards have different layouts.
* `GDO0` is used for TX.
* `GDO2` is used for RX.
* GPIO35 is input-only, which is suitable for RX but not TX.

### Adapting CC1101 pins

The CC1101 ESPHome YAML is intended to be configured through ESPHome substitutions.

Example:

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

These substitutions are then used by the SPI, CC1101, `remote_transmitter` and `remote_receiver` sections in the YAML.

If your hardware uses different pins, change the substitution values in the YAML file. You should not need to edit C++ `static constexpr` pin constants for normal pin changes.

### CC1101 setup steps

1. Copy the CC1101 YAML file from `esphome/` to your ESPHome configuration folder.
2. Copy the required custom component folder from `esphome/components/` to your ESPHome `components/` folder, if your setup uses local components.
3. Check the GPIO pin mapping in the YAML `substitutions:` section.
4. Update Wi-Fi secrets if needed.
5. Compile and flash from ESPHome.
6. Confirm that Home Assistant discovers the ESPHome device.
7. In Somfy HA Gateway V3, select the CC1101 gateway's TX and RX entities.

### CC1101 status

The CC1101 gateway is under active testing. TX is expected to work with the current prototype. RX support is experimental and may need tuning for specific hardware and receiver sensitivity.

## TTGO LoRa32 Gateway

The TTGO LoRa32 gateway is the original reference gateway.

Use the TTGO ESPHome YAML if your hardware is based on TTGO LoRa32 433 MHz / SX1278.

The TTGO gateway and the CC1101 gateway both expose the same JSON TX/RX entities to Home Assistant.

## JSON Protocol

The JSON protocol defines the contract between the Home Assistant integration and any compatible RF gateway.

Example TX payload:

```json
{
  "protocol": "somfy_rts",
  "dir": "tx",
  "address": "A1B2C3",
  "command": "up",
  "rolling_code": 123,
  "repeat": 2
}
```

Example RX payload:

```json
{
  "protocol": "somfy_rts",
  "dir": "rx",
  "address": "A1B2C3",
  "command": "down",
  "rolling_code": 456
}
```

Commands are case-insensitive. Gateways may publish command names such as `Up`, `Down` and `My`; the Home Assistant integration normalizes received commands to lowercase.

See the full protocol documentation:

```text
docs/protocol-json.md
```

## Rolling Code Warning

Somfy RTS uses rolling codes. Do not control the same Somfy device from multiple systems using the same address unless you understand the rolling code implications.

This integration expects Home Assistant to be the owner of the rolling code state.

The RF gateway must not increment, persist or validate rolling codes independently of the Home Assistant integration.

During testing, be careful not to send many failed commands with a real production address, as this may move the rolling code forward in Home Assistant without the motor receiving the frame.

## Troubleshooting

### The gateway sends, but the motor does not react

Check:

* The address is correct.
* The rolling code is equal to or higher than the motor expects.
* The correct TX entity is selected in the Home Assistant integration.
* The RF gateway is transmitting on 433.42 MHz.
* The antenna is connected.
* You are not using another controller with the same address and a conflicting rolling code.

### CC1101 RX does not work

Check:

* `GDO2` is connected to the configured RX GPIO.
* The RX GPIO is input-capable.
* The CC1101 module is the expected 433 MHz variant.
* The receiver is close to a known working Somfy remote during testing.

### CC1101 TX does not work

Check:

* `GDO0` is connected to the configured TX GPIO.
* The TX GPIO is output-capable.
* The CC1101 module has stable 3.3V power.
* The antenna is connected.
* The ESPHome log shows that a JSON TX payload was received.

## Development Status

This project is currently under active development.

Current focus:

* Stable Home Assistant integration
* UI-based add/remove cover flow
* JSON protocol documentation
* TTGO LoRa32 ESPHome gateway
* ESP32 + CC1101 ESPHome gateway

Planned:

* Translations
* HACS-ready release packaging
* RX-based pairing/discovery flow
* Diagnostics
* Repairs
* Tests

## Repository Layout

```text
somfy-ha-gateway/
  custom_components/
    somfy_ha_gateway_v3/
      ...
  docs/
    protocol-json.md
  esphome/
    README.md
    TTGO Somfy HA Gateway.yaml
    Somfy_CC1101_gw.yaml
    components/
      ...
  README.md
  hacs.json
```
## Utilities

Optional troubleshooting tools are available in:

```text
utilities/
```
These tools can help inspect Somfy RTS RF traffic, raw pulse timing, addresses and rolling codes during development or debugging. They are not required for normal Home Assistant gateway operation.

See:

utilities/README.md

## License

This project is released under the MIT License.

You may use, copy, modify and distribute the software freely, provided that the
copyright notice and license text are included in copies or substantial portions
of the software.

Attribution is appreciated when this project is copied, reused, referenced or
discussed publicly.

See [LICENSE](LICENSE).
