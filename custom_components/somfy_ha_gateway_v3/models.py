"""Cover configuration normalization for Somfy HA Gateway V3."""

from __future__ import annotations

from .const import (
    CONF_ADDRESS,
    CONF_COVER_ID,
    CONF_COVER_NAME,
    CONF_COVER_TYPE,
    CONF_MY_POSITION,
    CONF_OBSERVED_ADDRESSES,
    CONF_POSITION,
    CONF_REPEAT,
    CONF_ROLLING,
    CONF_TIME_IN,
    CONF_TIME_OUT,
)
from .position import clamp_position
from .protocol import normalize_address


def normalize_observed_addresses(value) -> list[str]:
    """Normalize observed address config from string or list input."""
    if isinstance(value, str):
        value = [x.strip() for x in value.split(",") if x.strip()]

    return [normalize_address(x) for x in value or []]


def normalize_cover(item: dict) -> dict:
    """Normalize a cover config dict and add runtime state defaults."""
    return {
        CONF_COVER_ID: str(item[CONF_COVER_ID]).strip(),
        CONF_COVER_NAME: str(item.get(CONF_COVER_NAME, item[CONF_COVER_ID])).strip(),
        CONF_ADDRESS: normalize_address(item[CONF_ADDRESS]),
        CONF_ROLLING: max(1, int(item.get(CONF_ROLLING, 1))),
        CONF_REPEAT: max(0, min(20, int(item.get(CONF_REPEAT, 2)))),
        CONF_OBSERVED_ADDRESSES: normalize_observed_addresses(
            item.get(CONF_OBSERVED_ADDRESSES, [])
        ),
        CONF_POSITION: clamp_position(item.get(CONF_POSITION, 0)),
        CONF_COVER_TYPE: str(item.get(CONF_COVER_TYPE, "blind")).strip().lower(),
        CONF_TIME_OUT: max(1, int(item.get(CONF_TIME_OUT, 30))),
        CONF_TIME_IN: max(1, int(item.get(CONF_TIME_IN, 30))),
        CONF_MY_POSITION: clamp_position(item.get(CONF_MY_POSITION, 50)),
        "moving": bool(item.get("moving", False)),
        "direction": str(item.get("direction", "idle")),
        "move_started_at": float(item.get("move_started_at", 0.0)),
        "move_start_position": clamp_position(
            item.get("move_start_position", item.get(CONF_POSITION, 0))
        ),
        "target_position": item.get("target_position"),
        "last_rx_address": item.get("last_rx_address"),
        "last_rx_command": item.get("last_rx_command"),
        "last_rx_rolling": item.get("last_rx_rolling"),
        "last_rx_key": item.get("last_rx_key"),
        "last_rx_key_time": float(item.get("last_rx_key_time", 0.0)),
    }


def normalize_cover_config(item: dict) -> dict:
    """Normalize a cover configuration dict.

    Compatibility wrapper used by config_flow.py. Kept separate so UI flows can
    import a config-focused name while the gateway can continue using
    normalize_cover().
    """
    return normalize_cover(item)
