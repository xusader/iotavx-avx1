"""Switch platform for IOTAVX AVX1 – Mute toggle."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CMD_MUTE_OFF, CMD_MUTE_ON, CONF_NAME, DEFAULT_NAME, DOMAIN
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
    async_add_entities([IOTAVXAVX1MuteSwitch(hass, protocol, coordinator, entry.entry_id, device_info)])


class IOTAVXAVX1MuteSwitch(CoordinatorEntity[IOTAVXAVX1Coordinator], SwitchEntity):

    _attr_has_entity_name = True
    _attr_name = "Stummschaltung"
    _attr_icon = "mdi:volume-mute"

    def __init__(self, hass, protocol, coordinator, entry_id, device_info):
        super().__init__(coordinator)
        self.hass = hass
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_mute"
        self._attr_device_info = device_info
        self._attr_is_on = False

    @callback
    def _handle_coordinator_update(self):
        if self.coordinator.data:
            self._attr_is_on = self.coordinator.data.get("muted", False)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        self._protocol.apply_optimistic("@11Q")
        await self.hass.async_add_executor_job(self._protocol.send_command, CMD_MUTE_ON)
        self.coordinator.async_set_updated_data(self._protocol.state.as_dict())

    async def async_turn_off(self, **kwargs):
        self._protocol.apply_optimistic("@11R")
        await self.hass.async_add_executor_job(self._protocol.send_command, CMD_MUTE_OFF)
        self.coordinator.async_set_updated_data(self._protocol.state.as_dict())
