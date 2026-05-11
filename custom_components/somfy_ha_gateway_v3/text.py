from homeassistant.components.text import TextEntity, TextMode
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN,
    CONF_COVER_ID,
    CONF_COVER_NAME,
    CONF_ADDRESS,
    CONF_OBSERVED_ADDRESSES,
)


async def async_setup_entry(hass, entry, async_add_entities):
    gateway = hass.data[DOMAIN][entry.entry_id]["gateway"]

    entities = []
    for cover in gateway.covers:
        cover_id = cover[CONF_COVER_ID]
        entities.append(SomfyAddressTextV3(entry.entry_id, gateway, cover_id))
        entities.append(SomfyObservedAddressesTextV3(entry.entry_id, gateway, cover_id))

    async_add_entities(entities)


class SomfyBaseTextV3(TextEntity):
    def __init__(self, entry_id, gateway, cover_id):
        self._entry_id = entry_id
        self._gateway = gateway
        self._cover_id = cover_id
        self._remove_listener = None
        self._attr_device_info = gateway.cover_device_info(cover_id)
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_mode = TextMode.TEXT

    async def async_added_to_hass(self):
        self._remove_listener = self._gateway.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None


class SomfyAddressTextV3(SomfyBaseTextV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Address"
        self._attr_unique_id = f"{entry_id}_{cover_id}_address"
        self._attr_native_min = 6
        self._attr_native_max = 6
        self._attr_pattern = "[0-9A-Fa-f]{6}"
        self._attr_icon = "mdi:identifier"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        return cover[CONF_ADDRESS] if cover else None

    async def async_set_value(self, value: str) -> None:
        await self._gateway.set_cover_address(self._cover_id, value)
        self.async_write_ha_state()


class SomfyObservedAddressesTextV3(SomfyBaseTextV3):
    def __init__(self, entry_id, gateway, cover_id):
        super().__init__(entry_id, gateway, cover_id)
        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Observed Addresses"
        self._attr_unique_id = f"{entry_id}_{cover_id}_observed_addresses"
        self._attr_native_max = 255
        self._attr_icon = "mdi:access-point"

    @property
    def native_value(self):
        cover = self._gateway.get_cover(self._cover_id)
        if not cover:
            return ""
        return ",".join(cover.get(CONF_OBSERVED_ADDRESSES, []))

    async def async_set_value(self, value: str) -> None:
        await self._gateway.set_cover_observed_addresses(self._cover_id, value)
        self.async_write_ha_state()