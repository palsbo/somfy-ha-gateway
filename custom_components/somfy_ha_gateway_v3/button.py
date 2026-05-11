from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, CONF_COVER_ID, CONF_COVER_NAME


async def async_setup_entry(hass, entry, async_add_entities):
    gateway = hass.data[DOMAIN][entry.entry_id]["gateway"]

    entities = []
    for cover in gateway.covers:
        cover_id = cover[CONF_COVER_ID]
        entities.append(SomfyCommandButtonV3(entry.entry_id, gateway, cover_id, "prog", "PROG"))

    async_add_entities(entities)


class SomfyCommandButtonV3(ButtonEntity):
    def __init__(self, entry_id, gateway, cover_id, command, label, repeat_override=None):
        self._entry_id = entry_id
        self._gateway = gateway
        self._cover_id = cover_id
        self._command = command
        self._repeat_override = repeat_override

        cover = self._gateway.get_cover(cover_id)
        self._attr_name = f"{cover[CONF_COVER_NAME]} {label}"
        self._attr_unique_id = f"{entry_id}_{cover_id}_{command}"
        self._attr_device_info = gateway.cover_device_info(cover_id)
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        await self._gateway.send_command(
            self._cover_id,
            self._command,
            repeat_override=self._repeat_override,
        )