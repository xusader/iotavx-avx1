"""DataUpdateCoordinator for the IOTAVX AVX1."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SCAN_INTERVAL_SECONDS
from .protocol import IOTAVXAVX1Protocol

_LOGGER = logging.getLogger(__name__)


class IOTAVXAVX1Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Simple polling coordinator.

    Runs query_status() in the executor (because serial is sync)
    and returns the state dict to all entities.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        protocol: IOTAVXAVX1Protocol,
        scan_interval: int = SCAN_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.protocol = protocol

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the device via executor (sync serial)."""
        return await self.hass.async_add_executor_job(
            self.protocol.query_status
        )
