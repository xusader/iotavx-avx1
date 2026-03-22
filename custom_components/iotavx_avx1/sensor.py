"""Sensor platform for the IOTAVX AVX1."""

from __future__ import annotations

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
        IOTAVXAVX1StatusSensor(protocol, coordinator, entry.entry_id, device_info),
        IOTAVXAVX1SourceSensor(coordinator, entry.entry_id, device_info),
    ])


class IOTAVXAVX1StatusSensor(CoordinatorEntity[IOTAVXAVX1Coordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Verbindungsstatus"
    _attr_icon = "mdi:lan-connect"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, protocol, coordinator, entry_id, device_info):
        super().__init__(coordinator)
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_status"
        self._attr_device_info = device_info

    @property
    def native_value(self):
        return "Verbunden" if self._protocol.connected else "Getrennt"

    @property
    def extra_state_attributes(self):
        s = self._protocol.state
        return {
            "connected": self._protocol.connected,
            "port": self._protocol.port,
            "volume_raw": s.volume_raw,
            "dimmer": s.dimmer,
        }


class IOTAVXAVX1SourceSensor(CoordinatorEntity[IOTAVXAVX1Coordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Aktuelle Quelle"
    _attr_icon = "mdi:video-input-hdmi"

    def __init__(self, coordinator, entry_id, device_info):
        super().__init__(coordinator)
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_source_sensor"
        self._attr_device_info = device_info

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get("source")
        return None
