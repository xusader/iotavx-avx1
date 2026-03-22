"""The IOTAVX AVX1 integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)
from .coordinator import IOTAVXAVX1Coordinator
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.REMOTE,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]

type IOTAVXAVX1ConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: IOTAVXAVX1ConfigEntry) -> bool:
    """Set up IOTAVX AVX1 from a config entry."""
    port = entry.data[CONF_SERIAL_PORT]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS)

    protocol = IOTAVXAVX1Protocol(port)

    if not await protocol.connect():
        _LOGGER.error("Could not connect to IOTAVX AVX1 on %s", port)
        return False

    coordinator = IOTAVXAVX1Coordinator(hass, protocol, scan_interval)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "protocol": protocol,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates (scan interval change)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # --- Register services ---
    async def handle_send_command(call: ServiceCall) -> None:
        """Handle the send_command service."""
        command = call.data["command"]
        await protocol.send_command(command)

    async def handle_set_dimmer(call: ServiceCall) -> None:
        """Handle the set_dimmer service."""
        level = call.data["level"]
        level_str = f"{int(level):02d}"
        await protocol.send_command(f"@12D{level_str}")

    async def handle_navigate_menu(call: ServiceCall) -> None:
        """Handle the navigate_menu service – send a sequence of nav commands."""
        commands = call.data["commands"]
        from .remote import BUTTON_MAP
        for cmd_name in commands:
            key = cmd_name.lower().strip()
            rs232_cmd = BUTTON_MAP.get(key, key if key.startswith("@") else None)
            if rs232_cmd:
                await protocol.send_command(rs232_cmd)
                import asyncio
                await asyncio.sleep(0.3)

    if not hass.services.has_service(DOMAIN, "send_command"):
        hass.services.async_register(
            DOMAIN,
            "send_command",
            handle_send_command,
            schema=vol.Schema({
                vol.Required("command"): cv.string,
            }),
        )

        hass.services.async_register(
            DOMAIN,
            "set_dimmer",
            handle_set_dimmer,
            schema=vol.Schema({
                vol.Required("level"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=10)
                ),
            }),
        )

        hass.services.async_register(
            DOMAIN,
            "navigate_menu",
            handle_navigate_menu,
            schema=vol.Schema({
                vol.Required("commands"): vol.All(
                    cv.ensure_list, [cv.string]
                ),
            }),
        )

    return True


async def _async_update_options(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update – reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: IOTAVXAVX1ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        protocol: IOTAVXAVX1Protocol = data["protocol"]
        await protocol.disconnect()

    return unload_ok
