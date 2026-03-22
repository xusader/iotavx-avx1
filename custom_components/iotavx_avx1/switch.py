"""Switch platform for IOTAVX AVX1 – Mute toggle."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CMD_MUTE_OFF,
    CMD_MUTE_ON,
    CONF_NAME,
    DEFAULT_NAME,
    DOMAIN,
)
from .coordinator import IOTAVXAVX1Coordinator
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IOTAVX AVX1 switch entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    protocol: IOTAVXAVX1Protocol = data["protocol"]
    coordinator: IOTAVXAVX1Coordinator = data["coordinator"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": name,
        "manufacturer": "IOTAVX",
        "model": "AVX1",
    }

    async_add_entities([
        IOTAVXAVX1MuteSwitch(protocol, coordinator, entry.entry_id, device_info),
    ])


class IOTAVXAVX1MuteSwitch(CoordinatorEntity[IOTAVXAVX1Coordinator], SwitchEntity):
    """A toggle switch for mute on the IOTAVX AVX1."""

    _attr_has_entity_name = True
    _attr_name = "Stummschaltung"
    _attr_icon = "mdi:volume-mute"

    def __init__(
        self,
        protocol: IOTAVXAVX1Protocol,
        coordinator: IOTAVXAVX1Coordinator,
        entry_id: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialise the mute switch."""
        super().__init__(coordinator)
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_mute"
        self._attr_device_info = device_info
        self._attr_is_on = False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator data update."""
        if self.coordinator.data:
            self._attr_is_on = self.coordinator.data.get("muted", False)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Mute the AVX1."""
        await self._protocol.send_command(CMD_MUTE_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unmute the AVX1."""
        await self._protocol.send_command(CMD_MUTE_OFF)
