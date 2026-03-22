"""Media Player platform for the IOTAVX AVX1."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CMD_MUTE_OFF,
    CMD_MUTE_ON,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    CMD_VOLUME_DOWN,
    CMD_VOLUME_SET,
    CMD_VOLUME_UP,
    CONF_NAME,
    DEFAULT_NAME,
    DOMAIN,
    SOUND_MODE_MAP,
    SOURCE_MAP,
)
from .coordinator import IOTAVXAVX1Coordinator
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    protocol: IOTAVXAVX1Protocol = data["protocol"]
    coordinator: IOTAVXAVX1Coordinator = data["coordinator"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    async_add_entities([IOTAVXAVX1MediaPlayer(hass, protocol, coordinator, entry.entry_id, name)])


class IOTAVXAVX1MediaPlayer(CoordinatorEntity[IOTAVXAVX1Coordinator], MediaPlayerEntity):

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )
    _attr_source_list = list(SOURCE_MAP.keys())
    _attr_sound_mode_list = list(SOUND_MODE_MAP.keys())

    def __init__(self, hass, protocol, coordinator, entry_id, name):
        super().__init__(coordinator)
        self.hass = hass
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}"
        self._attr_state = MediaPlayerState.OFF
        self._attr_source = None
        self._attr_sound_mode = None
        self._attr_volume_level = None
        self._attr_is_volume_muted = False
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
            "manufacturer": "IOTAVX",
            "model": "AVX1",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        status = self.coordinator.data or {}
        if "power" in status:
            self._attr_state = (
                MediaPlayerState.ON if status["power"] else MediaPlayerState.OFF
            )
        if status.get("source"):
            self._attr_source = status["source"]
        if status.get("sound_mode"):
            self._attr_sound_mode = status["sound_mode"]
        if "volume_level" in status:
            self._attr_volume_level = status["volume_level"]
        if "muted" in status:
            self._attr_is_volume_muted = status["muted"]
        self.async_write_ha_state()

    async def _send(self, command: str) -> None:
        """Send command via executor and apply optimistic state."""
        self._protocol.apply_optimistic(command)
        await self.hass.async_add_executor_job(
            self._protocol.send_command, command
        )
        # Push updated state immediately
        self.coordinator.async_set_updated_data(self._protocol.state.as_dict())

    async def async_turn_on(self) -> None:
        await self._send(CMD_POWER_ON)

    async def async_turn_off(self) -> None:
        await self._send(CMD_POWER_OFF)

    async def async_set_volume_level(self, volume: float) -> None:
        state = self._protocol.state
        rng = state.volume_max - state.volume_min
        raw = int(state.volume_min + volume * rng)
        await self._send(f"{CMD_VOLUME_SET}{raw:03d}")

    async def async_volume_up(self) -> None:
        await self._send(CMD_VOLUME_UP)

    async def async_volume_down(self) -> None:
        await self._send(CMD_VOLUME_DOWN)

    async def async_mute_volume(self, mute: bool) -> None:
        await self._send(CMD_MUTE_ON if mute else CMD_MUTE_OFF)

    async def async_select_source(self, source: str) -> None:
        cmd = SOURCE_MAP.get(source)
        if cmd:
            await self._send(cmd)

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        cmd = SOUND_MODE_MAP.get(sound_mode)
        if cmd:
            await self._send(cmd)
