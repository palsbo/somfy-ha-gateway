# Somfy HA Gateway JSON Protocol

## Design Principle

The Home Assistant integration owns all logical Somfy state:

- cover configuration
- rolling codes
- repeat count
- estimated position
- movement state
- MY position
- device/entity representation

The RF gateway is a stateless transport adapter. It sends and receives Somfy RTS frames and exposes them to Home Assistant as JSON.

## Required Entities

A compatible gateway must expose:

| Direction | Entity type | Purpose |
|---|---|---|
| TX | `text` | Home Assistant writes outgoing RTS commands |
| RX | `sensor` or `text` | Gateway publishes received RTS frames |

## TX Payload

```json
{
  "protocol": "somfy_rts",
  "dir": "tx",
  "address": "A1B2C3",
  "command": "up",
  "rolling_code": 123,
  "repeat": 2
}