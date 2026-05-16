# ESPHome CC1101 based interface for Somfy HA Gateway
## Hardware
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
