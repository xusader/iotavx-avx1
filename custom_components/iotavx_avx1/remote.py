"""Remote platform for IOTAVX AVX1 OSD menu navigation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

from homeassistant.components.remote import RemoteEntity, RemoteEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_DOWN_ARROW,
    CMD_ENTER,
    CMD_EXIT,
    CMD_LEFT_ARROW,
    CMD_MENU,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    CMD_RETURN,
    CMD_RIGHT_ARROW,
    CMD_UP_ARROW,
    CONF_NAME,
    DEFAULT_NAME,
    DOMAIN,
)
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)

# Map remote button names to RS-232 commands
BUTTON_MAP: dict[str, str] = {
    "menu": CMD_MENU,
    "up": CMD_UP_ARROW,
    "down": CMD_DOWN_ARROW,
    "left": CMD_LEFT_ARROW,
    "right": CMD_RIGHT_ARROW,
    "enter": CMD_ENTER,
    "select": CMD_ENTER,
    "exit": CMD_EXIT,
    "back": CMD_RETURN,
    "return": CMD_RETURN,
    "power_on": CMD_POWER_ON,
    "power_off": CMD_POWER_OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IOTAVX AVX1 remote from a config entry."""
    protocol: IOTAVXAVX1Protocol = hass.data[DOMAIN][entry.entry_id]["protocol"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    async_add_entities([IOTAVXAVX1Remote(protocol, entry.entry_id, name)])


class IOTAVXAVX1Remote(RemoteEntity):
    """Remote entity for OSD menu navigation on the IOTAVX AVX1."""

    _attr_has_entity_name = True
    _attr_name = "Remote"
    _attr_supported_features = RemoteEntityFeature.ACTIVITY
    _attr_is_on = True
    _attr_activity_list = list(BUTTON_MAP.keys())

    def __init__(
        self,
        protocol: IOTAVXAVX1Protocol,
        entry_id: str,
        name: str,
    ) -> None:
        """Initialise the remote entity."""
        self._protocol = protocol
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_remote"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": name,
            "manufacturer": "IOTAVX",
            "model": "AVX1",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on (power on the AVX1)."""
        await self._protocol.send_command(CMD_POWER_ON)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off (power off the AVX1)."""
        await self._protocol.send_command(CMD_POWER_OFF)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send one or more button presses.

        Usage in automations:
          service: remote.send_command
          target:
            entity_id: remote.iotavx_avx1_remote
          data:
            command:
              - menu
              - down
              - down
              - enter
        """
        num_repeats = kwargs.get("num_repeats", 1)
        delay = kwargs.get("delay_secs", 0.3)

        for _ in range(num_repeats):
            for cmd_name in command:
                key = cmd_name.lower().strip()
                rs232_cmd = BUTTON_MAP.get(key)

                if rs232_cmd is None:
                    # Allow raw RS-232 commands prefixed with @
                    if key.startswith("@"):
                        rs232_cmd = key
                    else:
                        _LOGGER.warning("Unknown remote button: %s", cmd_name)
                        continue

                await self._protocol.send_command(rs232_cmd)

                if delay > 0:
                    await asyncio.sleep(delay)
