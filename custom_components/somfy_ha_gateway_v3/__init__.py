from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .gateway import SomfyGatewayV3


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Somfy HA Gateway V3 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    gateway = SomfyGatewayV3(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = {
        "gateway": gateway,
        "unsub_options_update": entry.add_update_listener(_async_reload_entry),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Somfy HA Gateway V3 config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data:
            gateway = data.get("gateway")
            if gateway:
                gateway.async_unload()

            unsub_options_update = data.get("unsub_options_update")
            if unsub_options_update:
                unsub_options_update()

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
