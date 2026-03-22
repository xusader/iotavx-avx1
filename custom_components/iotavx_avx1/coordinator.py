"""DataUpdateCoordinator for the IOTAVX AVX1.

Unlike a typical polling coordinator, this one is driven by events
from the serial listener. The background listener in protocol.py
parses incoming data and calls our callback, which triggers an
async_set_updated_data() to push state to all entities.

A fallback poll is still performed at scan_interval to detect
if the device has gone offline (no DIM heartbeat received).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)

# If no data received for this many seconds, consider device offline
HEARTBEAT_TIMEOUT = 60.0


class IOTAVXAVX1Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Event-driven coordinator for the IOTAVX AVX1."""

    def __init__(
        self,
        hass: HomeAssistant,
        protocol: IOTAVXAVX1Protocol,
        scan_interval: int = SCAN_INTERVAL_SECONDS,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.protocol = protocol
        self._unregister_cb: callable | None = None

    async def async_setup(self) -> None:
        """Register the state-change callback from the protocol listener."""
        self._unregister_cb = self.protocol.register_state_callback(
            self._on_state_changed
        )

    async def async_shutdown(self) -> None:
        """Unregister callbacks."""
        if self._unregister_cb:
            self._unregister_cb()
            self._unregister_cb = None

    @callback
    def _on_state_changed(self) -> None:
        """Called by the protocol listener when state changes.

        Pushes the new state directly to all entities without waiting
        for the next poll interval.
        """
        self.async_set_updated_data(self.protocol.state.as_dict())

    async def _async_update_data(self) -> dict[str, Any]:
        """Fallback poll – checks if the device is still alive.

        The real state updates come from _on_state_changed above.
        This method runs at scan_interval as a health check.
        """
        if not self.protocol.connected:
            raise UpdateFailed("Not connected to AVX1")

        import time
        elapsed = time.time() - self.protocol.state.last_update

        if elapsed > HEARTBEAT_TIMEOUT and self.protocol.state.last_update > 0:
            _LOGGER.warning(
                "No data from AVX1 for %.0fs – device may be in standby",
                elapsed,
            )
            # Device is probably in standby (no heartbeat)
            self.protocol.state.power = False

        return self.protocol.state.as_dict()
