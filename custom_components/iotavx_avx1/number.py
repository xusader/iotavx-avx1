"""Number platform for IOTAVX AVX1 – Display dimmer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_DIM, CONF_NAME, DEFAULT_NAME, DOMAIN
from .protocol import IOTAVXAVX1Protocol


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    protocol = data["protocol"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": name,
        "manufacturer": "IOTAVX",
        "model": "AVX1",
    }
    async_add_entities([IOTAVXAVX1Dimmer(hass, protocol, entry.entry_id, device_info)])


class IOTAVXAVX1Dimmer(NumberEntity):
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
