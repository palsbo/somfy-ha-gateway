# Somfy HA Gateway V3
# FILE: gateway.py

import logging
import time
from collections.abc import Callable
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_TX_ENTITY,
    CONF_RX_ENTITY,
    CONF_COVERS,
    CONF_COVER_ID,
    CONF_COVER_NAME,
    CONF_ADDRESS,
    CONF_ROLLING,
    CONF_REPEAT,
    CONF_OBSERVED_ADDRESSES,
    CONF_POSITION,
    CONF_COVER_TYPE,
    CONF_TIME_OUT,
    CONF_TIME_IN,
    CONF_MY_POSITION,
)
from .models import normalize_cover, normalize_observed_addresses
from .position import (
    apply_received_command,
    clamp_position,
    estimated_position,
    start_movement,
    stop_movement,
)
from .protocol import build_tx_payload, normalize_address, parse_rx_payload

_LOGGER = logging.getLogger(__name__)


class SomfyGatewayV3:
    """Runtime gateway for Somfy RTS covers bridged through HA text/sensor entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._hass = hass
        self._entry = entry
        config = {**entry.data, **entry.options}

        self._name = config[CONF_NAME]
        self._tx_entity = config[CONF_TX_ENTITY]
        self._rx_entity = config.get(CONF_RX_ENTITY)

        self._listeners: list[Callable[[], None]] = []
        self._covers: list[dict] = [
            normalize_cover(item) for item in config.get(CONF_COVERS, [])
        ]

        self._unsub_tick = async_track_time_interval(
            hass,
            self._tick,
            timedelta(seconds=1),
        )

        self._unsub_rx = None
        if self._rx_entity:
            self._unsub_rx = async_track_state_change_event(
                hass,
                [self._rx_entity],
                self._rx_callback,
            )

    def async_unload(self) -> None:
        """Release event listeners owned by this gateway."""
        if self._unsub_rx:
            self._unsub_rx()
            self._unsub_rx = None

        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def covers(self) -> list[dict]:
        return self._covers

    def get_cover(self, cover_id: str) -> dict | None:
        for cover in self._covers:
            if cover[CONF_COVER_ID] == cover_id:
                return cover
        return None

    def cover_device_info(self, cover_id: str) -> dict:
        cover = self.get_cover(cover_id)
        name = cover[CONF_COVER_NAME] if cover else cover_id
        return {
            "identifiers": {(DOMAIN, f"{self._entry.entry_id}_{cover_id}")},
            "name": name,
            "manufacturer": "Custom",
            "model": "RTS Cover V3",
            "via_device": (DOMAIN, self._entry.entry_id),
        }

    def gateway_device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._name,
            "manufacturer": "Custom",
            "model": "RTS Gateway V3",
        }

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _estimated_position(self, cover: dict, now: float | None = None) -> int:
        return estimated_position(cover, now)

    def get_cover_position(self, cover_id: str) -> int | None:
        cover = self.get_cover(cover_id)
        if not cover:
            return None
        return self._estimated_position(cover)

    @callback
    def _tick(self, now) -> None:
        any_moving = False

        for cover in self._covers:
            if not cover.get("moving", False):
                continue

            any_moving = True
            pos = self._estimated_position(cover)
            cover[CONF_POSITION] = pos

            target = cover.get("target_position")
            direction = cover.get("direction")

            if direction == "up":
                if target is not None and pos <= int(target):
                    self._stop_at_target(cover, int(target))
                elif pos <= 0:
                    stop_movement(cover, position=0)

            elif direction == "down":
                if target is not None and pos >= int(target):
                    self._stop_at_target(cover, int(target))
                elif pos >= 100:
                    stop_movement(cover, position=100)

        if any_moving:
            self._notify_listeners()

    def _stop_at_target(self, cover: dict, target: int) -> None:
        stop_movement(cover, position=target)

        self._hass.async_create_task(
            self.send_command(
                cover[CONF_COVER_ID],
                "my",
                increment_rolling=True,
                repeat_override=0,
                update_movement=False,
            )
        )

    def _cover_matches_rx(self, cover: dict, address: str) -> bool:
        if address == cover[CONF_ADDRESS]:
            return True
        return address in cover.get(CONF_OBSERVED_ADDRESSES, [])

    async def _rx_callback(self, event) -> None:
        try:
            state = event.data.get("new_state")
            if not state or not state.state:
                return

            data = parse_rx_payload(state.state)
            if data is None:
                return

            address = data["address"]
            command = data["command"]
            rolling = data["rolling_code"]

            for cover in self._covers:
                if not self._cover_matches_rx(cover, address):
                    continue

                rx_key = f"{address}:{command}:{rolling}"
                now_ts = time.time()

                if (
                    cover.get("last_rx_key") == rx_key
                    and now_ts - float(cover.get("last_rx_key_time", 0.0)) < 2.0
                ):
                    return

                cover["last_rx_key"] = rx_key
                cover["last_rx_key_time"] = now_ts
                cover["last_rx_address"] = address
                cover["last_rx_command"] = command
                cover["last_rx_rolling"] = rolling

                apply_received_command(cover, command)

                if address == cover[CONF_ADDRESS] and rolling >= int(cover[CONF_ROLLING]):
                    cover[CONF_ROLLING] = rolling + 1

                await self._save_config()
                self._notify_listeners()
                return

        except Exception as err:
            _LOGGER.error("Somfy V3 RX parse error: %s", err)

    async def _save_config(self) -> None:
        if self._entry.options:
            new_options = dict(self._entry.options)
            new_options[CONF_COVERS] = self._covers
            self._hass.config_entries.async_update_entry(self._entry, options=new_options)
        else:
            new_data = dict(self._entry.data)
            new_data[CONF_COVERS] = self._covers
            self._hass.config_entries.async_update_entry(self._entry, data=new_data)

    async def set_cover_address(self, cover_id: str, address: str) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_ADDRESS] = normalize_address(address)
        await self._save_config()
        self._notify_listeners()

    async def set_cover_observed_addresses(self, cover_id: str, value: str) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_OBSERVED_ADDRESSES] = normalize_observed_addresses(value)
        await self._save_config()
        self._notify_listeners()

    async def set_cover_rolling(self, cover_id: str, rolling: int) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_ROLLING] = max(1, int(rolling))
        await self._save_config()
        self._notify_listeners()

    async def set_cover_repeat(self, cover_id: str, repeat: int) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_REPEAT] = max(0, min(20, int(repeat)))
        await self._save_config()
        self._notify_listeners()

    async def set_cover_time_out(self, cover_id: str, value: int) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_TIME_OUT] = max(1, int(value))
        await self._save_config()
        self._notify_listeners()

    async def set_cover_time_in(self, cover_id: str, value: int) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_TIME_IN] = max(1, int(value))
        await self._save_config()
        self._notify_listeners()

    async def set_cover_type(self, cover_id: str, cover_type: str) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_COVER_TYPE] = str(cover_type).strip().lower()
        await self._save_config()
        self._notify_listeners()

    async def set_cover_my_position(self, cover_id: str, value: int) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        cover[CONF_MY_POSITION] = clamp_position(value)
        await self._save_config()
        self._notify_listeners()

    async def set_cover_position_only(self, cover_id: str, position: int) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return
        stop_movement(cover, position=position)
        await self._save_config()
        self._notify_listeners()

    async def move_cover_to_position(self, cover_id: str, position: int) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            return

        target = clamp_position(position)
        current = self._estimated_position(cover)

        if target == current:
            return

        command = "down" if target > current else "up"
        cover["target_position"] = target

        await self.send_command(
            cover_id,
            command,
            increment_rolling=True,
            clear_target_on_direction=False,
        )

    async def send_command(
        self,
        cover_id: str,
        command: str,
        increment_rolling: bool = True,
        repeat_override: int | None = None,
        update_movement: bool = True,
        clear_target_on_direction: bool = True,
    ) -> None:
        cover = self.get_cover(cover_id)
        if not cover:
            _LOGGER.error("Unknown cover_id: %s", cover_id)
            return

        command = command.lower().strip()
        rolling_code = int(cover[CONF_ROLLING])
        repeat = int(cover[CONF_REPEAT]) if repeat_override is None else int(repeat_override)

        if update_movement:
            if command == "up":
                start_movement(cover, "up", clear_target=clear_target_on_direction)

            elif command == "down":
                start_movement(cover, "down", clear_target=clear_target_on_direction)

            elif command == "my":
                apply_received_command(cover, command)

        value = build_tx_payload(
            address=cover[CONF_ADDRESS],
            command=command,
            rolling_code=rolling_code,
            repeat=repeat,
        )

        _LOGGER.warning(
            "Somfy V3 TX JSON: %s moving=%s direction=%s target=%s",
            value,
            cover.get("moving"),
            cover.get("direction"),
            cover.get("target_position"),
        )

        await self._hass.services.async_call(
            "text",
            "set_value",
            {
                "entity_id": self._tx_entity,
                "value": value,
            },
            blocking=True,
        )

        if increment_rolling:
            cover[CONF_ROLLING] = rolling_code + 1
            await self._save_config()
            self._notify_listeners()
