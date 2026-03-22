"""Number platform for IOTAVX AVX1 trim and dimmer controls."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_CENTER_DOWN,
    CMD_CENTER_UP,
    CMD_DIM,
    CMD_REAR_DOWN,
    CMD_REAR_UP,
    CMD_SUB_DOWN,
    CMD_SUB_UP,
    CONF_NAME,
    DEFAULT_NAME,
    DOMAIN,
)
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IOTAVX AVX1 number entities."""
    protocol: IOTAVXAVX1Protocol = hass.data[DOMAIN][entry.entry_id]["protocol"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": name,
        "manufacturer": "IOTAVX",
        "model": "AVX1",
    }

    entities = [
        IOTAVXAVX1Dimmer(protocol, entry.entry_id, device_info),
        IOTAVXAVX1Trim(
            protocol, entry.entry_id, device_info,
            "center_trim", "Center Trim",
            CMD_CENTER_UP, CMD_CENTER_DOWN,
        ),
        IOTAVXAVX1Trim(
            protocol, entry.entry_id, device_info,
            "sub_trim", "Subwoofer Trim",
            CMD_SUB_UP, CMD_SUB_DOWN,
        ),
        IOTAVXAVX1Trim(
            protocol, entry.entry_id, device_info,
            "surround_trim", "Surround Trim",
            CMD_REAR_UP, CMD_REAR_DOWN,
        ),
    ]

    async_add_entities(entities)


class IOTAVXAVX1Dimmer(NumberEntity):
    """Display dimmer control (0–10)."""

    _attr_has_entity_name = True
    _attr_name = "Display Dimmer"
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:brightness-6"

    def __init__(
        self,
        protocol: IOTAVXAVX1Protocol,
        entry_id: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialise the dimmer entity."""
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_dimmer"
        self._attr_device_info = device_info
        self._attr_native_value = 10  # Default full brightness

    async def async_set_native_value(self, value: float) -> None:
        """Set the dimmer level."""
        level = int(value)
        level_str = f"{level:02d}"
        await self._protocol.send_command(f"{CMD_DIM}{level_str}")
        self._attr_native_value = level
        self.async_write_ha_state()


class IOTAVXAVX1Trim(NumberEntity):
    """Channel trim control (step-based, no absolute set)."""

    _attr_has_entity_name = True
    _attr_native_min_value = -12
    _attr_native_max_value = 12
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:tune-vertical"

    def __init__(
        self,
        protocol: IOTAVXAVX1Protocol,
        entry_id: str,
        device_info: dict[str, Any],
        key: str,
        name: str,
        cmd_up: str,
        cmd_down: str,
    ) -> None:
        """Initialise a trim entity."""
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = device_info
        self._cmd_up = cmd_up
        self._cmd_down = cmd_down
        self._attr_native_value = 0  # Assumed centre

    async def async_set_native_value(self, value: float) -> None:
        """Set trim by stepping up or down from current value."""
        target = int(value)
        current = int(self._attr_native_value or 0)
        diff = target - current

        if diff == 0:
            return

        cmd = self._cmd_up if diff > 0 else self._cmd_down
        steps = abs(diff)

        for _ in range(steps):
            await self._protocol.send_command(cmd)

        self._attr_native_value = target
        self.async_write_ha_state()
