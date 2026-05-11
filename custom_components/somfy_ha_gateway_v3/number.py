# Somfy HA Gateway V3
# VERSION: 2026-05-10 18:20
# FILE: number.py

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN,
    CONF_COVER_ID,
    CONF_COVER_NAME,
    CONF_ROLLING,
    CONF_REPEAT,
    CONF_POSITION,
    CONF_TIME_OUT,
    CONF_TIME_IN,
    CONF_MY_POSITION,
)


async def async_setup_entry(hass, entry, async_add_entities):
    gateway = hass.data[DOMAIN][entry.entry_id]["gateway"]

    entities = []
    for cover in gateway.covers:
        cover_id = cover[CONF_COVER_ID]
        entities.append(SomfyPositionNumberV3(entry.entry_id, gateway, cover_id))
        entities.append(SomfyRollingNumberV3(entry.entry_id, gateway, cover_id))
        entities.append(SomfyRepeatNumberV3(entry.entry_id, gateway, cover_id))
        entities.append(SomfyTimeOutNumberV3(entry.entry_id, gateway, cover_id))
        entities.append(SomfyTimeInNumberV3(entry.entry_id, gateway, cover_id))
        entities.append(SomfyMyPositionNumberV3(entry.entry_id, gateway, cover_id))

    async_add_entities(entities)


class SomfyBaseNumberV3(NumberEntity):
    def __init__(self, entry_id, gateway, cover_id):
        self._entry_id = entry_id
        self._gateway = gateway
        self._cover_id = cover_id
        self._remove_listener = None
        self._attr_device_info = gateway.cover_device_info(cover_id)
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_added_to_hass(self):
        self._remove_listener = self._gateway.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None


class SomfyPositionNumberV3(SomfyBaseNumberV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Position"
        self._attr_unique_id = f"{entry_id}_{cover_id}_position"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = "slider"
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        return cover.get(CONF_POSITION, 0) if cover else None

    async def async_set_native_value(self, value: float) -> None:
        await self._gateway.move_cover_to_position(self._cover_id, int(value))
        self.async_write_ha_state()


class SomfyRollingNumberV3(SomfyBaseNumberV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Rolling Code"
        self._attr_unique_id = f"{entry_id}_{cover_id}_rolling"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 65535
        self._attr_native_step = 1
        self._attr_mode = "box"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        return cover[CONF_ROLLING] if cover else None

    async def async_set_native_value(self, value: float) -> None:
        await self._gateway.set_cover_rolling(self._cover_id, int(value))
        self.async_write_ha_state()


class SomfyRepeatNumberV3(SomfyBaseNumberV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Repeat"
        self._attr_unique_id = f"{entry_id}_{cover_id}_repeat"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 20
        self._attr_native_step = 1
        self._attr_mode = "box"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        return cover[CONF_REPEAT] if cover else None

    async def async_set_native_value(self, value: float) -> None:
        await self._gateway.set_cover_repeat(self._cover_id, int(value))
        self.async_write_ha_state()


class SomfyTimeOutNumberV3(SomfyBaseNumberV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Time Out"
        self._attr_unique_id = f"{entry_id}_{cover_id}_time_out"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 300
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "s"
        self._attr_mode = "box"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        return cover.get(CONF_TIME_OUT, 30) if cover else None

    async def async_set_native_value(self, value: float) -> None:
        await self._gateway.set_cover_time_out(self._cover_id, int(value))
        self.async_write_ha_state()


class SomfyTimeInNumberV3(SomfyBaseNumberV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Time In"
        self._attr_unique_id = f"{entry_id}_{cover_id}_time_in"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 300
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "s"
        self._attr_mode = "box"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        return cover.get(CONF_TIME_IN, 30) if cover else None

    async def async_set_native_value(self, value: float) -> None:
        await self._gateway.set_cover_time_in(self._cover_id, int(value))
        self.async_write_ha_state()


class SomfyMyPositionNumberV3(SomfyBaseNumberV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} MY Position"
        self._attr_unique_id = f"{entry_id}_{cover_id}_my_position"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "%"
        self._attr_mode = "slider"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        return cover.get(CONF_MY_POSITION, 50) if cover else None

    async def async_set_native_value(self, value: float) -> None:
        await self._gateway.set_cover_my_position(self._cover_id, int(value))
        self.async_write_ha_state()