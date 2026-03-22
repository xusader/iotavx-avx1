"""Sensor platform for the IOTAVX AVX1."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import IOTAVXAVX1Coordinator
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IOTAVX AVX1 sensor entities."""
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
        IOTAVXAVX1StatusSensor(coordinator, protocol, entry.entry_id, device_info),
        IOTAVXAVX1SourceSensor(coordinator, entry.entry_id, device_info),
        IOTAVXAVX1SoundModeSensor(coordinator, entry.entry_id, device_info),
    ])


class IOTAVXAVX1StatusSensor(CoordinatorEntity[IOTAVXAVX1Coordinator], SensorEntity):
    """Diagnostic sensor showing the raw status response and connection state."""

    _attr_has_entity_name = True
    _attr_name = "Verbindungsstatus"
    _attr_icon = "mdi:lan-connect"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: IOTAVXAVX1Coordinator,
        protocol: IOTAVXAVX1Protocol,
        entry_id: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_status"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> str:
        """Return connection state."""
        return "Verbunden" if self._protocol.connected else "Getrennt"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        state = self._protocol.state
        return {
            "connected": self._protocol.connected,
            "port": self._protocol.port,
            "volume_raw": state.volume_raw,
            "volume_range": f"{state.volume_min}–{state.volume_max}",
            "dimmer": state.dimmer,
            "last_update": state.last_update,
        }


class IOTAVXAVX1SourceSensor(CoordinatorEntity[IOTAVXAVX1Coordinator], SensorEntity):
    """Sensor showing the currently active source."""

    _attr_has_entity_name = True
    _attr_name = "Aktuelle Quelle"
    _attr_icon = "mdi:video-input-hdmi"

    def __init__(
        self,
        coordinator: IOTAVXAVX1Coordinator,
        entry_id: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_source_sensor"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> str | None:
        """Return current source."""
        if self.coordinator.data:
            return self.coordinator.data.get("source")
        return None


class IOTAVXAVX1SoundModeSensor(CoordinatorEntity[IOTAVXAVX1Coordinator], SensorEntity):
    """Sensor showing the currently active sound mode."""

    _attr_has_entity_name = True
    _attr_name = "Aktueller Soundmodus"
    _attr_icon = "mdi:surround-sound"

    def __init__(
        self,
        coordinator: IOTAVXAVX1Coordinator,
        entry_id: str,
        device_info: dict[str, Any],
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_sound_mode_sensor"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> str | None:
        """Return current sound mode."""
        if self.coordinator.data:
            return self.coordinator.data.get("sound_mode")
        return None
