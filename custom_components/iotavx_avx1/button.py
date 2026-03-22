"""Button platform for IOTAVX AVX1 one-shot actions."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_MENU,
    CMD_RESET,
    CMD_SOURCE_DOWN,
    CMD_SOURCE_UP,
    CMD_MODE_UP,
    CMD_MODE_DOWN,
    CONF_NAME,
    DEFAULT_NAME,
    DOMAIN,
)
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)

BUTTON_DEFINITIONS: list[dict[str, Any]] = [
    {
        "key": "menu",
        "name": "Menü",
        "icon": "mdi:menu",
        "command": CMD_MENU,
    },
    {
        "key": "source_up",
        "name": "Source Up",
        "icon": "mdi:arrow-up-bold",
        "command": CMD_SOURCE_UP,
    },
    {
        "key": "source_down",
        "name": "Source Down",
        "icon": "mdi:arrow-down-bold",
        "command": CMD_SOURCE_DOWN,
    },
    {
        "key": "mode_up",
        "name": "Mode Up",
        "icon": "mdi:surround-sound",
        "command": CMD_MODE_UP,
    },
    {
        "key": "mode_down",
        "name": "Mode Down",
        "icon": "mdi:surround-sound",
        "command": CMD_MODE_DOWN,
    },
    {
        "key": "system_reset",
        "name": "System Reset",
        "icon": "mdi:restart",
        "command": CMD_RESET,
        "entity_category": "config",
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IOTAVX AVX1 button entities."""
    protocol: IOTAVXAVX1Protocol = hass.data[DOMAIN][entry.entry_id]["protocol"]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": name,
        "manufacturer": "IOTAVX",
        "model": "AVX1",
    }

    entities = [
        IOTAVXAVX1Button(protocol, entry.entry_id, device_info, defn)
        for defn in BUTTON_DEFINITIONS
    ]
    async_add_entities(entities)


class IOTAVXAVX1Button(ButtonEntity):
    """A one-shot button for the IOTAVX AVX1."""

    _attr_has_entity_name = True

    def __init__(
        self,
        protocol: IOTAVXAVX1Protocol,
        entry_id: str,
        device_info: dict[str, Any],
        definition: dict[str, Any],
    ) -> None:
        """Initialise the button."""
        self._protocol = protocol
        self._command = definition["command"]
        self._attr_unique_id = f"iotavx_avx1_{entry_id}_{definition['key']}"
        self._attr_name = definition["name"]
        self._attr_icon = definition.get("icon")
        self._attr_device_info = device_info
        if "entity_category" in definition:
            from homeassistant.helpers.entity import EntityCategory
            self._attr_entity_category = EntityCategory(definition["entity_category"])

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._protocol.send_command(self._command)
