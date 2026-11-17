"""Remote control with bounded command sequences and simulated key holds."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Iterable
from typing import Any

import voluptuous as vol
from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_HOLD_SECS,
    ATTR_NUM_REPEATS,
    RemoteEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JVCConfigEntry
from ._vendor.jvcprojector import const
from .const import REMOTE_COMMANDS
from .coordinator import DEFAULT_LENS_DURATION, JvcProjectorDataUpdateCoordinator
from .entity import JvcProjectorEntity

MIN_COMMAND_DELAY = 0.1
DEFAULT_COMMAND_DELAY = 0.2
MAX_REPEATS = 100
MAX_HOLD_SECS = 30
MAX_DELAY_SECS = 10
MAX_COMMANDS = 1000
MAX_SEQUENCE_SECS = 120


async def async_setup_entry(
    hass: HomeAssistant, entry: JVCConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the JVC Projector remote."""
    async_add_entities([JvcProjectorRemote(entry.runtime_data)])
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "press_lens",
        {
            vol.Required("direction"): vol.In(tuple(const.LENS_COMMANDS)),
            vol.Optional("duration", default=DEFAULT_LENS_DURATION): vol.Any(
                int, float
            ),
        },
        "async_press_lens",
    )
    platform.async_register_entity_service(
        "start_lens",
        {
            vol.Required("direction"): vol.In(tuple(const.LENS_COMMANDS)),
            vol.Optional("duration", default=DEFAULT_LENS_DURATION): vol.Any(
                int, float
            ),
        },
        "async_start_lens",
    )
    platform.async_register_entity_service("stop_lens", {}, "async_stop_lens")


class JvcProjectorRemote(JvcProjectorEntity, RemoteEntity):
    """Representation of the projector's acknowledged network keypresses."""

    _attr_name = None

    def __init__(self, coordinator: JvcProjectorDataUpdateCoordinator) -> None:
        """Initialize the remote and serialize service calls."""
        super().__init__(coordinator)
        self._command_lock = asyncio.Lock()
        self._last_command_time: float | None = None

    @property
    def is_on(self) -> bool:
        """Return whether the projector is on or warming up."""
        return self.coordinator.data.get(const.KEY_POWER) in (const.ON, const.WARMING)

    async def _send(self, cmd: str, value: str) -> None:
        """Rate limit across calls, including dashboard repeat actions."""
        loop = asyncio.get_running_loop()
        if self._last_command_time is not None:
            delay = MIN_COMMAND_DELAY - (loop.time() - self._last_command_time)
            if delay > 0:
                await asyncio.sleep(delay)
        if cmd == "remote":
            await self.coordinator.async_execute_command(
                lambda: self.device.remote(REMOTE_COMMANDS[value])
            )
        else:
            await self.coordinator.async_execute_command(
                lambda: self.device.send_command(cmd, value)
            )
        self._last_command_time = loop.time()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the projector on and refresh its power state."""
        async with self._command_lock:
            await self._send("power", const.ON)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the projector off and refresh its power state."""
        async with self._command_lock:
            await self._send("power", const.STANDBY)
        await self.coordinator.async_request_refresh()

    async def async_start_lens(
        self, direction: str, duration: float = DEFAULT_LENS_DURATION
    ) -> None:
        """Start native lens movement, independently of generic key repeats."""
        await self.coordinator.async_start_lens(direction, duration)

    async def async_press_lens(
        self, direction: str, duration: float = DEFAULT_LENS_DURATION
    ) -> None:
        """Step once on press, upgrading to continuous motion while still held."""
        await self.coordinator.async_press_lens(direction, duration)

    async def async_stop_lens(self) -> None:
        """Stop native lens movement on button release."""
        await self.coordinator.async_stop_lens()

    def _parse_command(self, command: str) -> tuple[str, str]:
        """Validate the complete sequence before sending its first command."""
        if not isinstance(command, str):
            raise ServiceValidationError("Projector commands must be strings")
        command = command.strip().lower()
        if "," not in command:
            cmd, value = "remote", command
        else:
            cmd, value = (part.strip() for part in command.split(",", 1))
        if cmd == "remote":
            if value not in REMOTE_COMMANDS:
                raise ServiceValidationError(f"Unknown remote command: {value}")
            return cmd, value
        try:
            return self.device.validate_command(cmd, value, model=self.device.model)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    @staticmethod
    def _number(value: Any, name: str, maximum: float) -> float:
        """Reject nonfinite and out-of-bounds durations."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ServiceValidationError(f"{name} must be a number")
        if not math.isfinite(value) or not 0 <= value <= maximum:
            raise ServiceValidationError(f"{name} must be between 0 and {maximum}")
        return float(value)

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a sequence; holds repeat keys for a fixed duration, not until release."""
        repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        if (
            isinstance(repeats, bool)
            or not isinstance(repeats, int)
            or not 1 <= repeats <= MAX_REPEATS
        ):
            raise ServiceValidationError(
                f"num_repeats must be between 1 and {MAX_REPEATS}"
            )
        delay = max(
            MIN_COMMAND_DELAY,
            self._number(
                kwargs.get(ATTR_DELAY_SECS, DEFAULT_COMMAND_DELAY),
                ATTR_DELAY_SECS,
                MAX_DELAY_SECS,
            ),
        )
        hold = self._number(
            kwargs.get(ATTR_HOLD_SECS, 0), ATTR_HOLD_SECS, MAX_HOLD_SECS
        )
        commands = [
            self._parse_command(cmd)
            for cmd in ([command] if isinstance(command, str) else command)
        ]
        if not commands:
            raise ServiceValidationError("At least one command is required")
        if hold and any(cmd != "remote" for cmd, _ in commands):
            raise ServiceValidationError(
                "hold_secs is only supported for remote key commands"
            )
        key_count = len(commands) * repeats
        # Conservative bounds keep hold/repeat combinations from queueing huge jobs.
        if key_count * (1 + math.ceil(hold / delay)) > MAX_COMMANDS:
            raise ServiceValidationError(
                f"A sequence may send at most {MAX_COMMANDS} keypresses"
            )
        if key_count * hold + (key_count - 1) * delay > MAX_SEQUENCE_SECS:
            raise ServiceValidationError(
                f"A sequence may last at most {MAX_SEQUENCE_SECS} seconds"
            )

        async with self._command_lock:
            loop = asyncio.get_running_loop()
            async with asyncio.timeout(MAX_SEQUENCE_SECS):
                for index in range(key_count):
                    if index:
                        await asyncio.sleep(delay)
                    cmd, value = commands[index % len(commands)]
                    deadline = loop.time() + hold
                    await self._send(cmd, value)
                    while hold and loop.time() + delay < deadline:
                        await asyncio.sleep(delay)
                        if loop.time() >= deadline:
                            break
                        await self._send(cmd, value)
        # Refresh outside the sequence lock so the next key can preempt its poll.
        if any(cmd != "remote" for cmd, _ in commands):
            await self.coordinator.async_request_refresh()
