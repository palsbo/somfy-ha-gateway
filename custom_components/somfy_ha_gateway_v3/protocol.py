"""Somfy RTS JSON protocol helpers for the gateway text/sensor bridge."""

from __future__ import annotations

import json
from typing import Any


def normalize_address(address: Any) -> str:
    """Normalize an RTS address to six upper-case hex-like characters."""
    return str(address or "").strip().upper().zfill(6)


def parse_rx_payload(raw: str) -> dict[str, Any] | None:
    """Parse and validate a received Somfy RTS JSON payload.

    Returns a normalized dict with address, command and rolling_code, or None
    when the payload is not relevant for this integration.
    """
    raw = (raw or "").strip()
    if not raw.startswith("{"):
        return None

    data = json.loads(raw)

    protocol = data.get("protocol")
    direction = data.get("dir")

    if protocol is not None and protocol != "somfy_rts":
        return None
    if direction is not None and direction != "rx":
        return None

    address = normalize_address(data.get("address"))
    command = str(data.get("command", "")).lower().strip()
    rolling_code = int(data.get("rolling_code", data.get("rolling", 0)))

    if not address or not command:
        return None

    return {
        "address": address,
        "command": command,
        "rolling_code": rolling_code,
    }


def build_tx_payload(
    *,
    address: str,
    command: str,
    rolling_code: int,
    repeat: int,
) -> str:
    """Build the compact JSON payload sent to the TX text entity."""
    payload = {
        "protocol": "somfy_rts",
        "dir": "tx",
        "address": normalize_address(address),
        "command": command.lower().strip(),
        "rolling_code": int(rolling_code),
        "repeat": int(repeat),
    }

    return json.dumps(payload, separators=(",", ":"))
