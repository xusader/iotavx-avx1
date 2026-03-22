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
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type IOTAVXAVX1ConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: IOTAVXAVX1ConfigEntry) -> bool:
    """Set up IOTAVX AVX1 from a config entry."""
    port = entry.data[CONF_SERIAL_PORT]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS)

    protocol = IOTAVXAVX1Protocol(port)

    # Connect in executor (sync serial)
    connected = await hass.async_add_executor_job(protocol.connect)
    if not connected:
        _LOGGER.warning("Could not connect to IOTAVX AVX1 on %s", port)

    coordinator = IOTAVXAVX1Coordinator(hass, protocol, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "protocol": protocol,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # Services
    async def handle_send_command(call: ServiceCall) -> None:
        await hass.async_add_executor_job(
            protocol.send_command, call.data["command"]
        )

    if not hass.services.has_service(DOMAIN, "send_command"):
        hass.services.async_register(
            DOMAIN,
            "send_command",
            handle_send_command,
            schema=vol.Schema({vol.Required("command"): cv.string}),
        )

    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: IOTAVXAVX1ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(data["protocol"].disconnect)
    return unload_ok
