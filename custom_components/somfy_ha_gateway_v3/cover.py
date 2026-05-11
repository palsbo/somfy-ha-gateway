from homeassistant.components.cover import CoverDeviceClass, CoverEntity, CoverEntityFeature

from .const import (
    DOMAIN,
    CONF_COVER_ID,
    CONF_COVER_NAME,
    CONF_POSITION,
    CONF_COVER_TYPE,
)


async def async_setup_entry(hass, entry, async_add_entities):
    gateway = hass.data[DOMAIN][entry.entry_id]["gateway"]

    async_add_entities(
        [
            SomfyCoverV3(entry.entry_id, gateway, cover[CONF_COVER_ID])
            for cover in gateway.covers
        ]
    )


class SomfyCoverV3(CoverEntity):
    def __init__(self, entry_id, gateway, cover_id):
        self._entry_id = entry_id
        self._gateway = gateway
        self._cover_id = cover_id
        self._remove_listener = None

        cover = self._gateway.get_cover(cover_id)
        self._attr_name = cover[CONF_COVER_NAME]
        self._attr_unique_id = f"{entry_id}_{cover_id}_cover"
        self._attr_available = True
        self._attr_assumed_state = True
        self._attr_device_info = gateway.cover_device_info(cover_id)

        cover_type = cover.get(CONF_COVER_TYPE, "blind")
        if cover_type == "awning":
            self._attr_device_class = CoverDeviceClass.AWNING
        elif cover_type == "curtain":
            self._attr_device_class = CoverDeviceClass.CURTAIN
        elif cover_type == "shutter":
            self._attr_device_class = CoverDeviceClass.SHUTTER
        else:
            self._attr_device_class = CoverDeviceClass.BLIND

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

    async def async_added_to_hass(self):
        self._remove_listener = self._gateway.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None

    @property
    def device_class(self):
        cover = self._gateway.get_cover(self._cover_id)
        cover_type = cover.get(CONF_COVER_TYPE, "blind") if cover else "blind"
        if cover_type == "awning":
            return CoverDeviceClass.AWNING
        if cover_type == "curtain":
            return CoverDeviceClass.CURTAIN
        if cover_type == "shutter":
            return CoverDeviceClass.SHUTTER
        return CoverDeviceClass.BLIND

    @property
    def is_closed(self):
        cover = self._gateway.get_cover(self._cover_id)
        if not cover:
            return None
        position = self._gateway.get_cover_position(self._cover_id)
        if position is None:
            return None
        if position <= 0:
            return True
        if position >= 100:
            return False
        return None

    @property
    def current_cover_position(self):
        cover = self._gateway.get_cover(self._cover_id)
        if not cover:
            return None
        position = self._gateway.get_cover_position(self._cover_id)
        return position if position is not None else int(cover.get(CONF_POSITION, 0))

    @property
    def extra_state_attributes(self):
        cover = self._gateway.get_cover(self._cover_id)
        if not cover:
            return {}
        return {
            "cover_id": self._cover_id,
            "address": cover.get("address"),
            "rolling": cover.get("rolling"),
            "repeat": cover.get("repeat"),
            "observed_addresses": cover.get("observed_addresses", []),
            "position": self._gateway.get_cover_position(self._cover_id),
            "cover_type": cover.get("cover_type", "blind"),
            "last_rx_address": cover.get("last_rx_address"),
            "last_rx_command": cover.get("last_rx_command"),
            "last_rx_rolling": cover.get("last_rx_rolling"),
            "moving": cover.get("moving", False),
            "direction": cover.get("direction", "idle"),
            "move_started_at": cover.get("move_started_at", 0.0),
            "move_start_position": cover.get("move_start_position", 0),
            "target_position": cover.get("target_position"),
            "time_out": cover.get("time_out", 30),
            "time_in": cover.get("time_in", 30),
            "my_position": cover.get("my_position", 50),
        }

    async def async_open_cover(self, **kwargs):
        await self._gateway.send_command(self._cover_id, "up")
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        await self._gateway.send_command(self._cover_id, "down")
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        await self._gateway.send_command(self._cover_id, "my", repeat_override=0)
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        position = kwargs.get("position")
        if position is None:
            return
        await self._gateway.move_cover_to_position(self._cover_id, int(position))
        self.async_write_ha_state()