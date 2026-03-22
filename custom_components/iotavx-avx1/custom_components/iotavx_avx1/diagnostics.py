"""Diagnostics support for IOTAVX AVX1."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .protocol import IOTAVXAVX1Protocol


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    protocol: IOTAVXAVX1Protocol = data["protocol"]

    # Query current status
    status = await protocol.query_status()

    return {
        "config": {
            "serial_port": protocol.port,
        },
        "connection": {
            "connected": protocol.connected,
        },
        "device_status": status,
        "recent_commands": protocol.command_log,
    }
