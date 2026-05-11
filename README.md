# Somfy HA Gateway

Home Assistant custom integration for controlling Somfy RTS covers through a replaceable RF gateway.

The integration separates Home Assistant state management from the RF hardware. Home Assistant owns cover configuration, rolling codes, repeat count, estimated position and device entities. The RF gateway is a stateless transport adapter that sends and receives Somfy RTS frames using JSON.

> Status: early development / public testing.

## Features

* Home Assistant custom integration for Somfy RTS covers
* Local control through an ESPHome-based RF gateway
* Gateway-agnostic JSON protocol
* Rolling code management in Home Assistant
* Estimated cover position based on configured travel times
* Add and remove covers from the integration options UI
* Cover configuration entities for address, rolling code, repeat count, timing and MY position
* Cover type selector for blind, awning, curtain and shutter
* PROG button entity per cover
* Optional RX support for receiving Somfy RTS frames

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
  - receives Somfy RTS frames
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

Recommended reference gateway:

* TTGO LoRa32 433 MHz / SX1278

Planned migration gateway:

* ESP32 + CC1101
* Intended for users who already have ESPSomfyRTS-style hardware and want to reuse the hardware with ESPHome firmware

Other gateways may work if they implement the same JSON TX/RX protocol.

## Installation

### Manual installation

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

This repository can later be added to HACS as a custom repository.

```text
https://github.com/palsbo/somfy-ha-gateway
```

Repository type:

```text
Integration
```

## Initial Configuration

During setup, select:

* Gateway name
* TX text entity
* RX sensor or text entity

The TX entity is where Home Assistant writes outgoing Somfy RTS JSON commands.

The RX entity is where the RF gateway publishes received Somfy RTS JSON frames.

Example entities:

```text
text.ttgo_somfy_gateway_somfy_json_tx
sensor.ttgo_somfy_gateway_somfy_json_rx
```

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

See the full protocol documentation:

```text
docs/protocol-json.md
```

## Rolling Code Warning

Somfy RTS uses rolling codes. Do not control the same Somfy device from multiple systems using the same address unless you understand the rolling code implications.

This integration expects Home Assistant to be the owner of the rolling code state.

The RF gateway must not increment, persist or validate rolling codes.

## ESPHome Gateway

ESPHome gateway examples are expected to live in:

```text
esphome/
```

Planned examples:

```text
esphome/ttgo-lora32-somfy-gateway.yaml
esphome/esp32-cc1101-somfy-gateway.yaml
```

## Development Status

This project is currently under active development.

Current focus:

* Stable Home Assistant integration
* UI-based add/remove cover flow
* JSON protocol documentation
* TTGO LoRa32 ESPHome gateway

Planned:

* Translations
* HACS-ready packaging
* ESP32 + CC1101 gateway template
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
    ...
  README.md
  hacs.json
```

## License

License to be decided.
