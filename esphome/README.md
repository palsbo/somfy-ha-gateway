# ESPHome based interface for Somfy HA Gateway
There are 2 available hardware options:
1) TTGO Lora32 hardware with ESP32 and SX1276 tranceiver for 433mHx
2) ESP32 + CC1101 module. Software needs to be adjusted to fit the actual hardware connection between ESP32 and the CC1101 module
## TTGO Lora32
This module can be used as is without hardware changes
### Installation
- copy the file 'esphome/somfy_ttrgo_gateway.yaml to your config/esphome directory on your HomeAssistant
- copy the folder 'esphome/components/sp,fu_ttgo_v3 tyour config/esphome/components
- install in ESPHome Builder
## ESP32 + CC1101
### Hardware
This interface is based on ESP32 + CC1101 module for RTS communication via 433.43mHz.
The code supplied is configured as follow:
|Pin|Description|ESP32 Pin|
|---|---|---|
|1|GND|GND|
|2|VCC|3v3|
|3|GDO0 (Tx)|GPIO35|
|4|CSN|GP*IO5|
|5|SCK|GPIO18|
|6|MOSI|GPIO23|
|7|MISO|GPIO19|
|8|GDP2 (Rx)|GPIO26|

This pin reference is for the E07-M1101D. If you have another transceiver the pins should match the function in the second column.
### Installation
- copy the file 'esphome/somfy_ttrgo_gateway.yaml to your config/esphome directory on your HomeAssistant
- copy the folder 'esphome/components/sp,fu_ttgo_v3 tyour config/esphome/components
- adjust the pin-assignments in the substitution part of the somfy_cc1101_yaml to fit your acual hardware
- install in ESPHome Builder
