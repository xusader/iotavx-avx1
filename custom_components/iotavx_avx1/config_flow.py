"""Config flow for IOTAVX AVX1 integration."""

from __future__ import annotations

import logging
from typing import Any

import serial.tools.list_ports
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    DEFAULT_NAME,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)


def _get_serial_ports() -> list[str]:
    """List available serial ports on the system."""
    ports = serial.tools.list_ports.comports()
    return sorted([p.device for p in ports])


async def _validate_connection(hass: HomeAssistant, port: str) -> bool:
    """Validate that we can talk to the AVX1 on the given port."""
    protocol = IOTAVXAVX1Protocol(port)
    try:
        return await protocol.test_connection()
    finally:
        await protocol.disconnect()


class IOTAVXAVX1ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IOTAVX AVX1."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> IOTAVXAVX1OptionsFlow:
        """Return the options flow handler."""
        return IOTAVXAVX1OptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            port = user_input[CONF_SERIAL_PORT]
            name = user_input.get(CONF_NAME, DEFAULT_NAME)

            # Check uniqueness
            await self.async_set_unique_id(port)
            self._abort_if_unique_id_configured()

            # Validate connection
            can_connect = await _validate_connection(self.hass, port)
            if can_connect:
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_SERIAL_PORT: port,
                        CONF_NAME: name,
                    },
                )
            errors["base"] = "cannot_connect"

        # Build the form
        available_ports = await self.hass.async_add_executor_job(_get_serial_ports)

        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT, default="/dev/ttyUSB0"): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "ports": ", ".join(available_ports) if available_ports else "keine erkannt",
            },
        )


class IOTAVXAVX1OptionsFlow(OptionsFlow):
    """Handle options for IOTAVX AVX1."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, SCAN_INTERVAL_SECONDS
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
