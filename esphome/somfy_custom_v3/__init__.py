import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

somfy_ns = cg.esphome_ns.namespace('somfy_ns')
SomfyComponent = somfy_ns.class_('SomfyComponent', cg.Component)

AUTO_LOAD = ['json', 'text_sensor']

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(SomfyComponent),
}).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    cg.add_library("Open RTS", None, "https://github.com/loopj/open-rts")
    cg.add_library("SPI", None)
    cg.add_build_flag("-DOPENRTS_BOARD_TTGO_LORA32_V21")
    cg.add_build_flag("-DEXCLUDE_EEPROM_SUPPORT")
    cg.add_build_flag("-Isrc/somfy_custom_v3")
    cg.add_build_flag("-I$PROJECT_PACKAGES_DIR/framework-arduinoespressif32/libraries/SPI/src")
    cg.add_build_flag("-I$PROJECT_PACKAGES_DIR/framework-arduinoespressif32/libraries/EEPROM/src")
    cg.add_build_flag("-Wl,--allow-multiple-definition")