"""Select platform for IOTAVX AVX1 – Input Source and Sound Mode."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN, SOURCE_MAP, SOUND_MODE_MAP
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
        IOTAVXAVX1InputSelect(hass, protocol, coordinator, entry.entry_id, device_info),
        IOTAVXAVX1ModeSelect(hass, protocol, coordinator, entry.entry_id, device_info),
    ])


class IOTAVXAVX1InputSelect(CoordinatorEntity[IOTAVXAVX1Coordinator], SelectEntity):
    """Input source selection."""

    _attr_has_entity_name = True
    _attr_name = "Eingang"
    _attr_icon = "mdi:video-input-hdmi"
    _attr_options = list(SOURCE_MAP.keys())

    def __init__(self, hass, protocol, coordinator, entry_id, device_info):
        super().__init__(coordinator)
        self.hass = hass
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_input"
        self._attr_device_info = device_info
        self._attr_current_option = None

    @callback
    def _handle_coordinator_update(self) -> None:
        status = self.coordinator.data or {}
        if status.get("source"):
            self._attr_current_option = status["source"]
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        cmd = SOURCE_MAP.get(option)
        if cmd:
            self._protocol.apply_optimistic(cmd)
            await self.hass.async_add_executor_job(
                self._protocol.send_command, cmd
            )
            self._attr_current_option = option
            self.coordinator.async_set_updated_data(self._protocol.state.as_dict())


class IOTAVXAVX1ModeSelect(CoordinatorEntity[IOTAVXAVX1Coordinator], SelectEntity):
    """Sound mode selection."""

    _attr_has_entity_name = True
    _attr_name = "Soundmodus"
    _attr_icon = "mdi:surround-sound"
    _attr_options = list(SOUND_MODE_MAP.keys())

    def __init__(self, hass, protocol, coordinator, entry_id, device_info):
        super().__init__(coordinator)
        self.hass = hass
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_mode"
        self._attr_device_info = device_info
        self._attr_current_option = None

    @callback
    def _handle_coordinator_update(self) -> None:
        status = self.coordinator.data or {}
        if status.get("sound_mode"):
            self._attr_current_option = status["sound_mode"]
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        cmd = SOUND_MODE_MAP.get(option)
        if cmd:
            self._protocol.apply_optimistic(cmd)
            await self.hass.async_add_executor_job(
                self._protocol.send_command, cmd
            )
            self._attr_current_option = option
            self.coordinator.async_set_updated_data(self._protocol.state.as_dict())
