# Utilities for Somfy RTS

This folder contains optional tools for testing and troubleshooting Somfy RTS radio traffic.

These utilities are not required by the Home Assistant integration itself. They are intended to help verify RF reception, inspect raw pulse timing, and identify Somfy RTS addresses and rolling codes during development or debugging.

## Available utilities

```text
utilities/
  arduino/
    Somfy_Raw_Monitor/
      Somfy_Raw_Monitor.ino
  esphome/
    raw_rts_monitor.yaml
```

## Somfy Raw Monitor - Arduino

```text
utilities/arduino/Somfy_Raw_Monitor/Somfy_Raw_Monitor.ino
```

Standalone Arduino sketch for a TTGO LoRa32-style ESP32 board with SX127x radio and OLED display.

It listens for Somfy RTS traffic on 433.42 MHz and can show:

- Somfy remote address
- command
- rolling code
- raw pulse dump in the serial monitor

Use this when you want the most detailed low-level view of received RTS frames and pulse timing.

### Typical use

1. Open the sketch in Arduino IDE.
2. Install the required board support and libraries used by the sketch.
3. Flash it to a TTGO LoRa32-compatible board.
4. Open the serial monitor at the configured baud rate.
5. Press a known Somfy RTS remote close to the monitor.
6. Compare the displayed/logged address and rolling code with the values configured in Home Assistant.

## Raw RTS Monitor - ESPHome

```text
utilities/esphome/raw_rts_monitor.yaml
```

ESPHome-based monitor for TTGO LoRa32-style hardware.

It configures the SX127x radio for OOK reception at 433.42 MHz and uses ESPHome `remote_receiver` raw dumps to log pulse timing.

Use this when you want a simple ESPHome-based diagnostic device that can be viewed from ESPHome logs or the device web server.

### Typical use

1. Copy `utilities/esphome/raw_rts_monitor.yaml` to your ESPHome configuration folder.
2. Make sure your ESPHome secrets contain `wifi_ssid` and `wifi_password`.
3. Confirm that the board and SX127x pin mapping match your TTGO LoRa32 variant.
4. Compile and flash with ESPHome.
5. Open the ESPHome logs.
6. Press a Somfy RTS remote close to the receiver and inspect the raw pulse output.

## Notes

- These tools are receive/debug helpers, not normal gateway firmware.
- They should not manage rolling codes.
- They should not be used as the primary Home Assistant gateway unless explicitly adapted for the JSON TX/RX protocol.
- RF reception is sensitive to antenna, module variant, power supply, and distance to the remote.
- If the monitor sees raw pulses but cannot decode frames, compare pulse lengths and receiver settings before changing Home Assistant configuration.

## Suggested troubleshooting workflow

1. First verify that the RF hardware receives any signal from a known Somfy RTS remote.
2. Confirm that received frames show the expected address.
3. Compare the observed rolling code with the rolling code configured in Home Assistant.
4. Then test the normal ESPHome gateway firmware.
5. Finally select the gateway TX/RX entities in the Somfy HA Gateway integration.
