"""Position and movement state helpers for Somfy RTS covers."""

from __future__ import annotations

import time

from .const import (
    CONF_MY_POSITION,
    CONF_POSITION,
    CONF_TIME_IN,
    CONF_TIME_OUT,
)


def clamp_position(position: int | float) -> int:
    """Clamp a position value to Home Assistant's 0-100 cover range."""
    return max(0, min(100, int(position)))


def estimated_position(cover: dict, now: float | None = None) -> int:
    """Estimate current cover position from runtime movement state."""
    if now is None:
        now = time.time()

    position = clamp_position(cover.get(CONF_POSITION, 0))

    if not cover.get("moving", False):
        return position

    direction = cover.get("direction", "idle")
    started_at = float(cover.get("move_started_at", 0.0) or 0.0)
    start_position = clamp_position(cover.get("move_start_position", position))

    if started_at <= 0:
        return start_position

    elapsed = max(0.0, now - started_at)

    if direction == "up":
        full_time = max(1, int(cover.get(CONF_TIME_IN, 30)))
        delta = 100.0 * elapsed / full_time
        return clamp_position(round(start_position - delta))

    if direction == "down":
        full_time = max(1, int(cover.get(CONF_TIME_OUT, 30)))
        delta = 100.0 * elapsed / full_time
        return clamp_position(round(start_position + delta))

    return start_position


def start_movement(
    cover: dict,
    direction: str,
    *,
    target_position: int | None = None,
    clear_target: bool = True,
) -> None:
    """Update runtime state for a newly started movement."""
    current_position = estimated_position(cover)

    cover["moving"] = True
    cover["direction"] = direction
    cover["move_started_at"] = time.time()
    cover["move_start_position"] = current_position

    if target_position is not None:
        cover["target_position"] = clamp_position(target_position)
    elif clear_target:
        cover["target_position"] = None


def stop_movement(cover: dict, *, position: int | None = None) -> None:
    """Stop movement and optionally persist the final position."""
    cover[CONF_POSITION] = estimated_position(cover) if position is None else clamp_position(position)
    cover["moving"] = False
    cover["direction"] = "idle"
    cover["target_position"] = None


def apply_received_command(cover: dict, command: str) -> None:
    """Apply RX command semantics to local movement state."""
    command = command.lower().strip()

    if command == "up":
        start_movement(cover, "up")
        return

    if command == "down":
        start_movement(cover, "down")
        return

    if command == "my":
        if cover.get("moving", False):
            stop_movement(cover)
            return

        current_position = estimated_position(cover)
        target_position = clamp_position(cover.get(CONF_MY_POSITION, 50))

        if target_position != current_position:
            direction = "down" if target_position > current_position else "up"
            start_movement(cover, direction, target_position=target_position)
