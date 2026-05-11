DOMAIN = "somfy_ha_gateway_v3"

CONF_NAME = "name"
CONF_TX_ENTITY = "tx_entity"
CONF_RX_ENTITY = "rx_entity"
CONF_COVERS = "covers"
CONF_COVERS_JSON = "covers_json"

CONF_COVER_ID = "id"
CONF_COVER_NAME = "name"
CONF_ADDRESS = "address"
CONF_ROLLING = "rolling"
CONF_REPEAT = "repeat"
CONF_OBSERVED_ADDRESSES = "observed_addresses"
CONF_POSITION = "position"
CONF_COVER_TYPE = "cover_type"
CONF_TIME_OUT = "time_out"
CONF_TIME_IN = "time_in"
CONF_MY_POSITION = "my_position"

PLATFORMS = ["cover", "button", "text", "number", "select"]

DEFAULT_TX_ENTITY = "text.ttgo_somfy_gateway_somfy_json_tx"
DEFAULT_RX_ENTITY = "sensor.ttgo_somfy_gateway_somfy_json_rx"