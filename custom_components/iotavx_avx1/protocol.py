"""Serial communication protocol for the IOTAVX AVX1.

Discovered protocol behaviour (from real device testing):
─────────────────────────────────────────────────────────
The AVX1 does NOT respond with a structured status query. Instead it:

1. Sends 'DIMx*' periodically as a heartbeat / dimmer status
   (x = dimmer level 0–9, * = terminator)

2. Echoes state changes as '@CMD' wrapped in single quotes:
   - Volume:  '@14Knnn'  where nnn = raw volume (e.g. 380)
   - Source:  '@11B' / '@116' / etc. – the source-select command
   - Mute:    '@11Q' (on) / '@11R' (off)

3. These arrive both after sending a command AND spontaneously
   when the user operates the physical remote control.

This means we can run a background listener instead of polling.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable
from typing import Any

import serial_asyncio

from .const import (
    SERIAL_BAUDRATE,
    SERIAL_BYTESIZE,
    SERIAL_TIMEOUT,
    SOURCE_MAP,
    SOUND_MODE_MAP,
)

_LOGGER = logging.getLogger(__name__)

MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY = 2.0
COMMAND_DELAY = 0.05

# Reverse maps: RS-232 command -> friendly name
_COMMAND_TO_SOURCE: dict[str, str] = {v: k for k, v in SOURCE_MAP.items()}
_COMMAND_TO_MODE: dict[str, str] = {v: k for k, v in SOUND_MODE_MAP.items()}

# Regex patterns for parsing AVX1 responses
_RE_DIM = re.compile(r"DIM(\d+)\*")           # DIM3*
_RE_VOLUME = re.compile(r"@14K(\d+)")          # '@14K380'
_RE_QUOTED_CMD = re.compile(r"'(@[^']+)'")     # '@11B', '@11Q', etc.


class AVX1State:
    """Holds the current known state of the AVX1."""

    def __init__(self) -> None:
        """Initialise with unknown state."""
        self.power: bool = False
        self.volume_raw: int = 0          # Raw value (e.g. 380)
        self.volume_min: int = 0          # Will be calibrated
        self.volume_max: int = 800        # Will be calibrated
        self.muted: bool = False
        self.source: str | None = None
        self.sound_mode: str | None = None
        self.dimmer: int = 0
        self.last_update: float = 0.0

    @property
    def volume_level(self) -> float:
        """Return volume as 0.0–1.0 normalised value."""
        vol_range = self.volume_max - self.volume_min
        if vol_range <= 0:
            return 0.0
        return max(0.0, min(1.0, (self.volume_raw - self.volume_min) / vol_range))

    def as_dict(self) -> dict[str, Any]:
        """Return state as a dictionary."""
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
    """Handle serial communication with the IOTAVX AVX1.

    Runs a background listener that parses all incoming data and
    updates the shared AVX1State object. Entities observe state
    changes via callbacks.
    """

    def __init__(self, port: str) -> None:
        """Initialise the protocol handler."""
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._listener_task: asyncio.Task | None = None
        self._command_log: list[dict[str, Any]] = []

        # Shared state
        self.state = AVX1State()

        # Callbacks
        self._state_callbacks: list[Callable[[], None]] = []
        self._availability_callbacks: list[Callable[[bool], None]] = []

        # Internal buffer for reassembling fragmented messages
        self._buffer = ""

    # --- Properties ---

    @property
    def connected(self) -> bool:
        """Return True if connected."""
        return self._connected

    @property
    def port(self) -> str:
        """Return the configured port."""
        return self._port

    @property
    def command_log(self) -> list[dict[str, Any]]:
        """Return the last N commands for diagnostics."""
        return self._command_log[-50:]

    # --- Callbacks ---

    def register_state_callback(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for state changes. Returns unregister fn."""
        self._state_callbacks.append(callback)
        return lambda: self._state_callbacks.remove(callback)

    def register_availability_callback(
        self, callback: Callable[[bool], None]
    ) -> Callable[[], None]:
        """Register a callback for connection changes. Returns unregister fn."""
        self._availability_callbacks.append(callback)
        return lambda: self._availability_callbacks.remove(callback)

    def _notify_state_changed(self) -> None:
        """Notify all state listeners."""
        for cb in self._state_callbacks:
            try:
                cb()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error in state callback")

    def _notify_availability(self, available: bool) -> None:
        """Notify all availability listeners."""
        for cb in self._availability_callbacks:
            try:
                cb(available)
            except Exception:  # noqa: BLE001
                pass

    # --- Connection ---

    async def connect(self) -> bool:
        """Open the serial connection and start the background listener."""
        try:
            if self._port.startswith("socket://"):
                host_port = self._port.replace("socket://", "")
                host, port_str = host_port.rsplit(":", 1)
                reader, writer = await asyncio.open_connection(host, int(port_str))
            else:
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=self._port,
                    baudrate=SERIAL_BAUDRATE,
                    bytesize=SERIAL_BYTESIZE,
                    parity="N",
                    stopbits=1,
                    timeout=SERIAL_TIMEOUT,
                )
            self._reader = reader
            self._writer = writer
            self._connected = True
            self._notify_availability(True)
            _LOGGER.info("Connected to IOTAVX AVX1 on %s", self._port)

            # Start background listener
            self._listener_task = asyncio.create_task(self._listen_loop())

            return True
        except (OSError, Exception) as err:  # noqa: BLE001
            _LOGGER.error("Failed to connect to %s: %s", self._port, err)
            self._connected = False
            self._notify_availability(False)
            return False

    async def _reconnect(self) -> bool:
        """Attempt reconnection with backoff."""
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            _LOGGER.info(
                "Reconnect attempt %d/%d to %s",
                attempt, MAX_RECONNECT_ATTEMPTS, self._port,
            )
            await self.disconnect()
            await asyncio.sleep(RECONNECT_DELAY * attempt)
            if await self.connect():
                return True
        _LOGGER.error("Failed to reconnect after %d attempts", MAX_RECONNECT_ATTEMPTS)
        return False

    async def disconnect(self) -> None:
        """Close connection and stop the listener."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

        self._connected = False
        self._reader = None
        self._writer = None
        _LOGGER.info("Disconnected from IOTAVX AVX1")

    # --- Background listener ---

    async def _listen_loop(self) -> None:
        """Continuously read from serial and parse incoming data."""
        _LOGGER.debug("Listener started")
        assert self._reader is not None

        try:
            while self._connected:
                try:
                    data = await asyncio.wait_for(
                        self._reader.read(256), timeout=30.0
                    )
                    if not data:
                        _LOGGER.warning("Serial connection closed (EOF)")
                        break

                    text = data.decode("ascii", errors="replace")
                    self._buffer += text
                    self._process_buffer()

                except asyncio.TimeoutError:
                    # No data for 30s – that's fine, AVX1 might be in standby
                    continue
                except (OSError, ConnectionError) as err:
                    _LOGGER.error("Listener read error: %s", err)
                    break

        except asyncio.CancelledError:
            _LOGGER.debug("Listener cancelled")
            return

        # If we exit the loop, we lost connection
        self._connected = False
        self._notify_availability(False)
        _LOGGER.warning("Listener stopped – connection lost")

    def _process_buffer(self) -> None:
        """Extract and parse complete messages from the buffer."""
        changed = False

        # --- Parse DIMx* heartbeats ---
        for match in _RE_DIM.finditer(self._buffer):
            dim_val = int(match.group(1))
            if self.state.dimmer != dim_val:
                self.state.dimmer = dim_val
                changed = True
            # DIM heartbeat means the device is on
            if not self.state.power:
                self.state.power = True
                changed = True
            _LOGGER.debug("Parsed DIM: %d", dim_val)

        # --- Parse '@14Knnn' volume ---
        for match in _RE_VOLUME.finditer(self._buffer):
            vol_raw = int(match.group(1))
            if self.state.volume_raw != vol_raw:
                self.state.volume_raw = vol_raw
                changed = True
                # Auto-calibrate volume range
                if vol_raw > self.state.volume_max:
                    self.state.volume_max = vol_raw
            _LOGGER.debug("Parsed Volume: %d (%.0f%%)", vol_raw, self.state.volume_level * 100)

        # --- Parse quoted command echoes '@CMD' ---
        for match in _RE_QUOTED_CMD.finditer(self._buffer):
            cmd = match.group(1)
            self._handle_command_echo(cmd)
            changed = True

        # Keep only the tail that might be an incomplete message
        # (last 20 chars should be enough for any partial token)
        if len(self._buffer) > 100:
            self._buffer = self._buffer[-40:]

        if changed:
            self.state.last_update = time.time()
            self._notify_state_changed()

    def _handle_command_echo(self, cmd: str) -> None:
        """Handle a command echo like '@11B' (source) or '@11Q' (mute)."""
        # Check if it's a source command
        source_name = _COMMAND_TO_SOURCE.get(cmd)
        if source_name:
            self.state.source = source_name
            _LOGGER.debug("Parsed Source: %s (%s)", source_name, cmd)
            return

        # Check if it's a sound mode command
        mode_name = _COMMAND_TO_MODE.get(cmd)
        if mode_name:
            self.state.sound_mode = mode_name
            _LOGGER.debug("Parsed Mode: %s (%s)", mode_name, cmd)
            return

        # Mute
        if cmd == "@11Q":
            self.state.muted = True
            _LOGGER.debug("Parsed Mute: ON")
            return
        if cmd == "@11R":
            self.state.muted = False
            _LOGGER.debug("Parsed Mute: OFF")
            return

        # Power
        if cmd == "@112":
            self.state.power = True
            _LOGGER.debug("Parsed Power: ON")
            return
        if cmd == "@113":
            self.state.power = False
            _LOGGER.debug("Parsed Power: OFF")
            return

        # Volume command echo (already handled by @14K pattern)
        if cmd.startswith("@14K"):
            return

        _LOGGER.debug("Unhandled command echo: %s", cmd)

    # --- Sending commands ---

    async def send_command(self, command: str) -> str | None:
        """Send a command to the AVX1.

        The response is not returned directly – it will be picked up
        by the background listener and parsed into state updates.
        Returns the raw response (if any) for diagnostic purposes.
        """
        if not self._connected or self._writer is None:
            _LOGGER.warning("Not connected – attempting reconnect")
            if not await self._reconnect():
                return None

        async with self._lock:
            try:
                payload = f"{command}\r"
                self._writer.write(payload.encode("ascii"))
                await self._writer.drain()
                _LOGGER.debug("Sent: %s", command)

                await asyncio.sleep(COMMAND_DELAY)

                self._log_command(command, True)
                return ""
            except (OSError, ConnectionError) as err:
                _LOGGER.error("Send error: %s", err)
                self._connected = False
                self._notify_availability(False)
                self._log_command(command, False, str(err))
                return None

    async def send_commands(self, commands: list[str]) -> None:
        """Send multiple commands sequentially."""
        for cmd in commands:
            await self.send_command(cmd)

    def _log_command(
        self,
        command: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Log a command for diagnostics."""
        entry: dict[str, Any] = {
            "time": time.time(),
            "command": command,
            "success": success,
        }
        if error:
            entry["error"] = error
        self._command_log.append(entry)
        if len(self._command_log) > 50:
            self._command_log = self._command_log[-50:]

    # --- Status query (kept for compatibility, but listener does the real work) ---

    async def query_status(self) -> dict[str, Any]:
        """Return the current state as a dict.

        This does NOT poll the device – it returns the state that has
        been accumulated by the background listener.
        """
        return self.state.as_dict()

    async def test_connection(self) -> bool:
        """Test if the serial port can be opened.

        We only verify that the port exists and is accessible.
        The device may be in standby and not respond, so we don't
        require a response – just a successful port open.
        """
        if not await self.connect():
            return False
        # Port opened successfully – that's enough for setup.
        # The background listener will pick up state once the device
        # is powered on.
        return True
