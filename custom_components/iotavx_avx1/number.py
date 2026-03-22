"""Number platform for IOTAVX AVX1 – Volume and Dimmer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CMD_DIM, CMD_VOLUME_SET, CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import IOTAVXAVX1Coordinator
from .protocol import IOTAVXAVX1Protocol


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    protocol = data["protocol"]
    coordinator = data["coordinator"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": name,
        "manufacturer": "IOTAVX",
        "model": "AVX1",
    }
    async_add_entities([
        IOTAVXAVX1VolumeSlider(hass, protocol, coordinator, entry.entry_id, device_info),
        IOTAVXAVX1Dimmer(hass, protocol, entry.entry_id, device_info),
    ])


class IOTAVXAVX1VolumeSlider(CoordinatorEntity[IOTAVXAVX1Coordinator], NumberEntity):
    """Volume slider showing 0.0–80.0, matching the AVX1 display."""

    _attr_has_entity_name = True
    _attr_name = "Lautstärke"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 80.0
    _attr_native_step = 0.5
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:volume-high"
    _attr_native_unit_of_measurement = "dB"

    def __init__(self, hass, protocol, coordinator, entry_id, device_info):
        super().__init__(coordinator)
        self.hass = hass
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_volume"
        self._attr_device_info = device_info
        self._attr_native_value = 0.0

    @callback
    def _handle_coordinator_update(self) -> None:
        status = self.coordinator.data or {}
        if "volume_raw" in status:
            # Raw 400 = Display 40.0
            self._attr_native_value = status["volume_raw"] / 10.0
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set volume. Display value 40.0 → raw 400 → '@11P400'."""
        raw = int(round(value * 10))
        raw = max(0, min(800, raw))
        self._protocol.apply_optimistic(f"{CMD_VOLUME_SET}{raw:03d}")
        await self.hass.async_add_executor_job(
            self._protocol.send_command, f"{CMD_VOLUME_SET}{raw:03d}"
        )
        self._attr_native_value = value
        self.coordinator.async_set_updated_data(self._protocol.state.as_dict())


class IOTAVXAVX1Dimmer(NumberEntity):
    """Display dimmer control (0–10)."""

    _attr_has_entity_name = True
    _attr_name = "Display Dimmer"
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:brightness-6"

    def __init__(self, hass, protocol, entry_id, device_info):
        self.hass = hass
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_dimmer"
        self._attr_device_info = device_info
        self._attr_native_value = 10

    async def async_set_native_value(self, value: float) -> None:
        level = int(value)
        cmd = f"{CMD_DIM}{level:02d}"
        await self.hass.async_add_executor_job(self._protocol.send_command, cmd)
        self._attr_native_value = level
        self.async_write_ha_state()
