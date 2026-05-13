import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

somfy_v2_ns = cg.esphome_ns.namespace("somfy_cc1101_v2")
SomfyCC1101V2 = somfy_v2_ns.class_("SomfyCC1101V2", cg.Component)

# Refererer til remote_transmitter via namespace (undgår import-afhængighed)
remote_transmitter_ns = cg.esphome_ns.namespace("remote_transmitter")
RemoteTransmitterComponent = remote_transmitter_ns.class_("RemoteTransmitterComponent")

CONF_TRANSMITTER = "transmitter"

DEPENDENCIES = ["remote_transmitter"]
AUTO_LOAD = ["text_sensor"]

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(SomfyCC1101V2),
    cv.Required(CONF_TRANSMITTER): cv.use_id(RemoteTransmitterComponent),
}).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    tx = await cg.get_variable(config[CONF_TRANSMITTER])
    cg.add(var.set_transmitter(tx))