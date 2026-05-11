"""Select entities for Somfy HA Gateway V3."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    CONF_COVER_ID,
    CONF_COVER_NAME,
    CONF_COVER_TYPE,
    DOMAIN,
)

COVER_TYPE_OPTIONS = ["blind", "awning", "curtain", "shutter"]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Somfy cover config select entities."""
    gateway = hass.data[DOMAIN][entry.entry_id]["gateway"]

    entities = []
    for cover in gateway.covers:
        cover_id = cover[CONF_COVER_ID]
        entities.append(SomfyCoverTypeSelectV3(entry.entry_id, gateway, cover_id))

    async_add_entities(entities)


class SomfyCoverTypeSelectV3(SelectEntity):
    """Select the Home Assistant cover device class for one Somfy cover."""

    def __init__(self, entry_id, gateway, cover_id):
        self._entry_id = entry_id
        self._gateway = gateway
        self._cover_id = cover_id
        self._remove_listener = None

        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} Cover Type"
        self._attr_unique_id = f"{entry_id}_{cover_id}_cover_type"
        self._attr_device_info = gateway.cover_device_info(cover_id)
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:form-dropdown"
        self._attr_options = COVER_TYPE_OPTIONS

    async def async_added_to_hass(self):
        self._remove_listener = self._gateway.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None

    @property
    def current_option(self):
        cover = self._gateway.get_cover(self._cover_id)
        if not cover:
            return None
        cover_type = str(cover.get(CONF_COVER_TYPE, "blind")).lower()
        return cover_type if cover_type in COVER_TYPE_OPTIONS else "blind"

    async def async_select_option(self, option: str) -> None:
        if option not in COVER_TYPE_OPTIONS:
            return
        await self._gateway.set_cover_type(self._cover_id, option)
        self.async_write_ha_state()
