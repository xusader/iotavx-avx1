"""Serial communication for the IOTAVX AVX1.

Key discovery from working integration:
  Commands must be wrapped in single quotes: '@112' not @112
  Uses synchronous serial.Serial, not serial_asyncio.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import serial

from .const import (
    SERIAL_BAUDRATE,
    SOURCE_MAP,
    SOUND_MODE_MAP,
)

_LOGGER = logging.getLogger(__name__)

_COMMAND_TO_SOURCE: dict[str, str] = {v: k for k, v in SOURCE_MAP.items()}
_COMMAND_TO_MODE: dict[str, str] = {v: k for k, v in SOUND_MODE_MAP.items()}


class AVX1State:
    """Current known state of the AVX1."""

    def __init__(self) -> None:
        self.power: bool = False
        self.volume_raw: int = 0
        self.volume_min: int = 0
        self.volume_max: int = 600
        self.muted: bool = False
        self.source: str | None = None
        self.sound_mode: str | None = None
        self.dimmer: int = 0
        self.last_update: float = 0.0

    @property
    def volume_level(self) -> float:
        """Convert raw volume to HA level (0.0-1.0).

        AVX1 volume: 0.0-80.0 on display, raw @14K values 0-800.
        HA slider 0.0-1.0 maps to raw 0-800.
        """
        return max(0.0, min(1.0, self.volume_raw / 800.0))

    def as_dict(self) -> dict[str, Any]:
        return {
            "power": self.power,
            "volume_raw": self.volume_raw,
            "volume_level": self.volume_level,
            "muted": self.muted,
            "source": self.source,
            "sound_mode": self.sound_mode,
            "dimmer": self.dimmer,
            "last_update": self.last_update,
        }


class IOTAVXAVX1Protocol:
    """Synchronous serial protocol handler for the IOTAVX AVX1.

    Uses plain serial.Serial like the proven working integration.
    Commands are wrapped in single quotes as the device expects.
    """

    def __init__(self, port: str) -> None:
        self._port = port
        self._ser: serial.Serial | None = None
        self._connected = False
        self._command_log: list[dict[str, Any]] = []
        self.state = AVX1State()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> str:
        return self._port

    @property
    def command_log(self) -> list[dict[str, Any]]:
        return self._command_log[-50:]

    def connect(self) -> bool:
        """Open the serial port."""
        try:
            self._ser = serial.Serial(self._port, SERIAL_BAUDRATE, timeout=1)
            self._connected = True
            _LOGGER.info("Connected to IOTAVX AVX1 on %s", self._port)
            return True
        except serial.SerialException as err:
            _LOGGER.error("Failed to connect to %s: %s", self._port, err)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Close the serial port."""
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:  # noqa: BLE001
                pass
        self._connected = False
        self._ser = None

    def send_command(self, command: str) -> str | None:
        """Send a command wrapped in single quotes and read response.

        The AVX1 expects commands like: '@112' (with quotes!)
        """
        if not self._connected or self._ser is None or not self._ser.is_open:
            _LOGGER.warning("Not connected")
            return None

        try:
            # Wrap in single quotes – this is what the working integration does
            payload = f"'{command}'"
            self._ser.write(payload.encode())
            _LOGGER.info("TX → %s", payload)

            # Read response
            response = self._ser.readline().decode().strip()
            if response:
                _LOGGER.info("RX ← %s", response)
                self._parse_response(response)
            else:
                _LOGGER.debug("RX ← (no response)")

            self._log_cmd(command, True)
            return response
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Serial error: %s", err)
            self._log_cmd(command, False, str(err))
            return None

    def _parse_response(self, response: str) -> None:
        """Parse any response from the AVX1 and update state."""
        changed = False

        # DIM heartbeat: DIM3*
        dim_match = re.search(r"DIM(\d+)\*", response)
        if dim_match:
            self.state.dimmer = int(dim_match.group(1))
            self.state.power = True
            changed = True
            _LOGGER.debug("Parsed DIM=%d", self.state.dimmer)

        # Volume: '@14K380'
        vol_match = re.search(r"@14K(\d+)", response)
        if vol_match:
            val = int(vol_match.group(1))
            self.state.volume_raw = val
            if val > self.state.volume_max:
                self.state.volume_max = val
            changed = True
            _LOGGER.debug("Parsed VOL=%d", val)

        # Command echoes: '@11B', '@11Q', etc.
        for cmd_match in re.finditer(r"'(@[^']+)'", response):
            cmd = cmd_match.group(1)
            if cmd.startswith("@14K"):
                continue

            src = _COMMAND_TO_SOURCE.get(cmd)
            if src:
                self.state.source = src
                changed = True
                continue

            mode = _COMMAND_TO_MODE.get(cmd)
            if mode:
                self.state.sound_mode = mode
                changed = True
                continue

            if cmd == "@11Q":
                self.state.muted = True
                changed = True
            elif cmd == "@11R":
                self.state.muted = False
                changed = True

        if changed:
            self.state.last_update = time.time()

    def apply_optimistic(self, command: str) -> None:
        """Set optimistic state before sending."""
        if command == "@112":
            self.state.power = True
        elif command == "@113":
            self.state.power = False

        if command == "@11Q":
            self.state.muted = True
        elif command == "@11R":
            self.state.muted = False

        src = _COMMAND_TO_SOURCE.get(command)
        if src:
            self.state.source = src

        mode = _COMMAND_TO_MODE.get(command)
        if mode:
            self.state.sound_mode = mode

        self.state.last_update = time.time()

    def query_status(self) -> dict[str, Any]:
        """Query status and return state dict."""
        self.send_command("@12S")
        return self.state.as_dict()

    def _log_cmd(self, cmd: str, ok: bool, err: str | None = None) -> None:
        entry: dict[str, Any] = {"time": time.time(), "command": cmd, "success": ok}
        if err:
            entry["error"] = err
        self._command_log.append(entry)
        if len(self._command_log) > 50:
            self._command_log = self._command_log[-50:]

    # For config flow compatibility
    async def test_connection(self) -> bool:
        return self.connect()
