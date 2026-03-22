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
    """Set up the IOTAVX AVX1 media player from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    protocol: IOTAVXAVX1Protocol = data["protocol"]
    coordinator: IOTAVXAVX1Coordinator = data["coordinator"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    async_add_entities([IOTAVXAVX1MediaPlayer(protocol, coordinator, entry.entry_id, name)])


class IOTAVXAVX1MediaPlayer(CoordinatorEntity[IOTAVXAVX1Coordinator], MediaPlayerEntity):
    """Representation of the IOTAVX AVX1 as a media player."""

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

    def __init__(
        self,
        protocol: IOTAVXAVX1Protocol,
        coordinator: IOTAVXAVX1Coordinator,
        entry_id: str,
        name: str,
    ) -> None:
        """Initialise the media player."""
        super().__init__(coordinator)
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}"
        self._entry_id = entry_id

        # State
        self._attr_state = MediaPlayerState.OFF
        self._attr_source = None
        self._attr_sound_mode = None
        self._attr_volume_level: float | None = None
        self._attr_is_volume_muted = False

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
            "manufacturer": "IOTAVX",
            "model": "AVX1",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        status = self.coordinator.data or {}

        if "power" in status:
            self._attr_state = (
                MediaPlayerState.ON if status["power"] else MediaPlayerState.OFF
            )
        if "source" in status:
            self._attr_source = status["source"]
        if "sound_mode" in status:
            self._attr_sound_mode = status["sound_mode"]
        if "volume_level" in status:
            self._attr_volume_level = status["volume_level"]
        if "muted" in status:
            self._attr_is_volume_muted = status["muted"]

        self.async_write_ha_state()

    # --- Power ---

    async def async_turn_on(self) -> None:
        """Turn the receiver on."""
        await self._protocol.send_command(CMD_POWER_ON)
        # Optimistic state is set in protocol._apply_optimistic_state()
        # and pushed via coordinator callback

    async def async_turn_off(self) -> None:
        """Turn the receiver off."""
        await self._protocol.send_command(CMD_POWER_OFF)

    # --- Volume ---

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        # Convert normalised level to raw value using the protocol's range
        state = self._protocol.state
        vol_range = state.volume_max - state.volume_min
        raw = int(state.volume_min + volume * vol_range)
        vol_str = f"{raw:03d}"
        await self._protocol.send_command(f"{CMD_VOLUME_SET}{vol_str}")
        # Listener will pick up the echoed '@14Knnn' and update state

    async def async_volume_up(self) -> None:
        """Increase volume by one step."""
        await self._protocol.send_command(CMD_VOLUME_UP)

    async def async_volume_down(self) -> None:
        """Decrease volume by one step."""
        await self._protocol.send_command(CMD_VOLUME_DOWN)

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute."""
        cmd = CMD_MUTE_ON if mute else CMD_MUTE_OFF
        await self._protocol.send_command(cmd)

    # --- Source ---

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        cmd = SOURCE_MAP.get(source)
        if cmd is None:
            _LOGGER.warning("Unknown source: %s", source)
            return
        await self._protocol.send_command(cmd)

    # --- Sound Mode ---

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select sound mode."""
        cmd = SOUND_MODE_MAP.get(sound_mode)
        if cmd is None:
            _LOGGER.warning("Unknown sound mode: %s", sound_mode)
            return
        await self._protocol.send_command(cmd)
