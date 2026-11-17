"""Coordinate polling and commands over the projector connection."""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ._vendor.jvcprojector import const
from ._vendor.jvcprojector.device import JvcProjectorAuthError
from ._vendor.jvcprojector.error import JvcProjectorError
from ._vendor.jvcprojector.projector import JvcProjector
from .const import NAME

_LOGGER = logging.getLogger(__name__)
INTERVAL_SLOW = timedelta(seconds=10)
INTERVAL_FAST = timedelta(seconds=5)
CONNECTION_TIMEOUT = 30
LENS_COMMAND_TIMEOUT = 2
MAX_LENS_DURATION = 5
DEFAULT_LENS_DURATION = 5
LENS_HOLD_DELAY = 0.35
_T = TypeVar("_T")


class _PollInterrupted(Exception):
    """Foreground input superseded a snapshot at a safe reference boundary."""


class JvcProjectorDataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Serialize commands and polling, with the library owning reconnects."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: JvcProjector,
        *,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator after device metadata has been read."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=NAME,
            update_interval=INTERVAL_SLOW,
        )
        self.device = device
        self.unique_id = format_mac(device.mac)
        self._operation_lock = asyncio.Lock()
        self._input_generation = 0
        self._lens_lock = asyncio.Lock()
        self._lens_direction: str | None = None
        self._lens_watchdog: asyncio.Task | None = None
        self._lens_press_token: object | None = None
        self._lens_hold_task: asyncio.Task | None = None
        self._shutting_down = False
        self._stopped = False

    def _mark_input(self) -> float:
        """Signal input before it waits for any polling or movement lock."""
        self._input_generation += 1
        return asyncio.get_running_loop().time()

    def _log_input_wait(self, action: str, requested_at: float) -> None:
        """Distinguish a queued foreground request from projector response time."""
        _LOGGER.debug(
            "%s waited %.3fs for control",
            action,
            asyncio.get_running_loop().time() - requested_at,
        )

    async def _execute(
        self,
        operation: Callable[[], Awaitable[_T]],
        *,
        operation_name: str = "command",
    ) -> _T:
        """Run one operation without replaying a possibly acknowledged keypress."""
        loop = asyncio.get_running_loop()
        queued_at = loop.time()
        async with self._operation_lock:
            started_at = loop.time()
            if self._stopped:
                raise HomeAssistantError("The projector integration is unloading")
            try:
                async with asyncio.timeout(CONNECTION_TIMEOUT):
                    # Idempotent: the library reconnects its TCP transport as needed.
                    await self.device.connect()
                    return await operation()
            except BaseException:
                # An unfinished response must not be reused, including on cancellation.
                await self.device.disconnect()
                raise
            finally:
                _LOGGER.debug(
                    "%s: queue %.3fs, exchange %.3fs",
                    operation_name,
                    started_at - queued_at,
                    loop.time() - started_at,
                )

    async def async_execute_command(
        self, operation: Callable[[], Awaitable[None]]
    ) -> None:
        """Execute a command with errors suitable for Home Assistant services."""
        requested_at = self._mark_input()
        self._lens_press_token = None
        async with self._lens_lock:
            self._log_input_wait("Command", requested_at)
            if self._shutting_down:
                raise HomeAssistantError("The projector integration is unloading")
            await self._cancel_lens_hold()
            # Stop a running motor before unrelated remote or setting commands.
            if self._lens_direction is not None:
                try:
                    await self._stop_lens_locked()
                except BaseException:
                    self._ensure_lens_watchdog(asyncio.get_running_loop().time() + 1)
                    raise
            await self._execute_service_command(operation)

    async def _execute_service_command(
        self, operation: Callable[[], Awaitable[None]]
    ) -> None:
        """Translate transport errors without replaying the operation."""
        try:
            await self._execute(operation)
        except JvcProjectorAuthError as err:
            raise ConfigEntryAuthFailed("Password authentication failed") from err
        except (JvcProjectorError, OSError, TimeoutError) as err:
            raise HomeAssistantError(
                f"Unable to send projector command: {err}"
            ) from err

    async def _send_lens(self, direction: str, *, start: bool) -> None:
        """Bound an uncertain motor response before trying a fresh stop."""
        try:
            async with asyncio.timeout(LENS_COMMAND_TIMEOUT):
                await self._execute_service_command(
                    lambda: self.device.lens_move(direction, start=start)
                )
        except TimeoutError as err:
            raise HomeAssistantError("Lens command acknowledgement timed out") from err

    async def _send_lens_step(self, direction: str) -> None:
        """Send one finite motor step, without replaying an uncertain ACK."""
        try:
            async with asyncio.timeout(LENS_COMMAND_TIMEOUT):
                await self._execute_service_command(
                    lambda: self.device.lens_step(direction)
                )
        except TimeoutError as err:
            raise HomeAssistantError("Lens command acknowledgement timed out") from err

    async def _cancel_lens_hold(self) -> None:
        """Cancel a pending promotion while holding the movement lock."""
        if self._lens_hold_task is asyncio.current_task():
            return
        task, self._lens_hold_task = self._lens_hold_task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def _ensure_lens_watchdog(self, deadline: float) -> None:
        """Keep a stop task until the motor is known stopped or retries expire."""
        if self._lens_direction is not None and self._lens_watchdog is None:
            self._lens_watchdog = asyncio.create_task(self._watch_lens(deadline))

    async def _cancel_lens_watchdog(self) -> None:
        """Cancel a pending watchdog while holding the movement lock."""
        task, self._lens_watchdog = self._lens_watchdog, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _stop_lens_locked(self) -> None:
        """Stop the current motor, retaining its direction if the ACK is lost."""
        await self._cancel_lens_hold()
        await self._cancel_lens_watchdog()
        if self._lens_direction is not None:
            await self._send_lens(self._lens_direction, start=False)
            self._lens_direction = None

    async def _watch_lens(self, deadline: float) -> None:
        """Best-effort stop at the deadline, with bounded retries on lost ACKs."""
        task = asyncio.current_task()
        try:
            for attempt in range(3):
                await asyncio.sleep(
                    max(0, deadline - asyncio.get_running_loop().time())
                    if attempt == 0
                    else 1
                )
                async with self._lens_lock:
                    if self._lens_direction is None:
                        return
                    try:
                        await self._send_lens(self._lens_direction, start=False)
                    except (HomeAssistantError, ValueError):
                        _LOGGER.exception("Unable to stop lens movement automatically")
                    else:
                        self._lens_direction = None
                        return
        finally:
            if self._lens_watchdog is task:
                self._lens_watchdog = None

    def _validate_lens(self, direction: str, duration: float) -> None:
        """Validate before changing an existing gesture or writing any command."""
        if not isinstance(direction, str) or direction not in const.LENS_COMMANDS:
            raise ServiceValidationError("Unknown lens direction")
        if self.device.model not in const.LENS_MODELS:
            raise ServiceValidationError(
                "Continuous lens movement is not verified for this projector model"
            )
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or not 0 < duration <= MAX_LENS_DURATION
        ):
            raise ServiceValidationError(
                f"duration must be greater than 0 and at most {MAX_LENS_DURATION} seconds"
            )

    async def _start_lens_locked(self, direction: str, duration: float) -> None:
        """Start continuous movement with the movement lock already held."""
        try:
            await self._stop_lens_locked()
        except BaseException:
            self._ensure_lens_watchdog(asyncio.get_running_loop().time() + 1)
            raise
        if self._shutting_down:
            raise HomeAssistantError("The projector integration is unloading")
        deadline = asyncio.get_running_loop().time() + duration
        # Track before sending: a missing ACK does not mean the motor stayed off.
        self._lens_direction = direction
        try:
            await self._send_lens(direction, start=True)
        except BaseException:
            try:
                await self._stop_lens_locked()
            except (HomeAssistantError, ValueError):
                _LOGGER.exception("Unable to stop lens after uncertain start")
            finally:
                self._ensure_lens_watchdog(deadline)
            raise
        self._ensure_lens_watchdog(deadline)

    async def async_start_lens(
        self, direction: str, duration: float = DEFAULT_LENS_DURATION
    ) -> None:
        """Start continuous movement immediately, without a preceding step."""
        self._validate_lens(direction, duration)
        requested_at = self._mark_input()
        self._lens_press_token = None
        async with self._lens_lock:
            self._log_input_wait("Lens start", requested_at)
            if self._shutting_down:
                raise HomeAssistantError("The projector integration is unloading")
            await self._start_lens_locked(direction, duration)

    async def async_press_lens(
        self, direction: str, duration: float = DEFAULT_LENS_DURATION
    ) -> None:
        """Step immediately, then upgrade an unreleased press to continuous motion."""
        self._validate_lens(direction, duration)
        requested_at = self._mark_input()
        token = self._lens_press_token = object()
        deadline = asyncio.get_running_loop().time() + LENS_HOLD_DELAY
        try:
            async with self._lens_lock:
                self._log_input_wait("Lens press", requested_at)
                if self._shutting_down:
                    raise HomeAssistantError("The projector integration is unloading")
                try:
                    await self._stop_lens_locked()
                    if self._shutting_down:
                        raise HomeAssistantError(
                            "The projector integration is unloading"
                        )
                    # Every accepted tap gets its finite step. Release only
                    # cancels promotion, even if a poll delayed the command.
                    await self._send_lens_step(direction)
                except BaseException:
                    self._ensure_lens_watchdog(asyncio.get_running_loop().time() + 1)
                    raise
                if self._lens_press_token is token:
                    self._lens_hold_task = asyncio.create_task(
                        self._promote_lens_press(token, direction, duration, deadline)
                    )
        except BaseException:
            if self._lens_press_token is token:
                self._lens_press_token = None
            raise

    async def _promote_lens_press(
        self, token: object, direction: str, duration: float, deadline: float
    ) -> None:
        """Upgrade only the current, still-held gesture after the hold threshold."""
        task = asyncio.current_task()
        try:
            await asyncio.sleep(max(0, deadline - asyncio.get_running_loop().time()))
            async with self._lens_lock:
                if self._shutting_down or self._lens_press_token is not token:
                    return
                self._lens_press_token = None
                await self._start_lens_locked(direction, duration)
        except (HomeAssistantError, ValueError):
            _LOGGER.exception("Unable to start continuous lens movement after hold")
        finally:
            if self._lens_hold_task is task:
                self._lens_hold_task = None

    async def async_stop_lens(self) -> None:
        """Stop on release; repeated releases after a known stop are harmless."""
        requested_at = self._mark_input()
        # Release must invalidate a promotion even while a step ACK holds the lock.
        self._lens_press_token = None
        async with self._lens_lock:
            self._log_input_wait("Lens stop", requested_at)
            if self._stopped:
                raise HomeAssistantError("The projector integration is unloading")
            try:
                await self._stop_lens_locked()
            except BaseException:
                self._ensure_lens_watchdog(asyncio.get_running_loop().time() + 1)
                raise

    async def _async_update_data(self) -> dict[str, str]:
        """Yield to input between references and publish only a complete snapshot."""
        generation = self._input_generation
        started_at = asyncio.get_running_loop().time()
        outcome = "complete"

        def check_poll_current() -> None:
            if self._shutting_down or generation != self._input_generation:
                raise _PollInterrupted

        async def read_reference(code: str) -> str | None:
            # Each acknowledged reference is the largest indivisible poll unit.
            # Check outside _execute so a clean interruption keeps the TCP stream.
            await asyncio.sleep(0)
            async with self._lens_lock:
                check_poll_current()
                if (
                    self._lens_press_token is not None
                    or self._lens_direction is not None
                ):
                    raise _PollInterrupted
                result = await self._execute(
                    lambda: self.device.ref(code), operation_name=f"reference {code}"
                )
                check_poll_current()
                return result

        try:
            async with self._lens_lock:
                if self._lens_press_token is not None:
                    outcome = "deferred during lens press"
                    return dict(self.data or {})
                # A multi-reference poll must not get between motor start and stop.
                if self._lens_direction is not None:
                    if self._lens_watchdog is not None:
                        outcome = "deferred during lens movement"
                        return dict(self.data or {})
                    # Retry a failed watchdog stop when connectivity recovers.
                    # Until then, report a failed poll instead of healthy stale data.
                    await self._stop_lens_locked()
                check_poll_current()
            async with asyncio.timeout(CONNECTION_TIMEOUT):
                mapping = await self.device.get_state(
                    requested_keys={key for key in self.async_contexts() if key},
                    reference_reader=read_reference,
                )
                check_poll_current()
        except _PollInterrupted:
            outcome = "interrupted by input"
            return dict(self.data or {})
        except ConfigEntryAuthFailed:
            outcome = "authentication failed"
            raise
        except JvcProjectorAuthError as err:
            outcome = "authentication failed"
            raise ConfigEntryAuthFailed("Password authentication failed") from err
        except (JvcProjectorError, OSError, TimeoutError, HomeAssistantError) as err:
            outcome = "failed"
            raise UpdateFailed(f"Unable to update projector: {err}") from err
        finally:
            _LOGGER.debug(
                "Status poll %s after %.3fs",
                outcome,
                asyncio.get_running_loop().time() - started_at,
            )

        state = {key: value for key, value in mapping.items() if value is not None}
        self.update_interval = (
            INTERVAL_SLOW
            if state.get(const.KEY_POWER) == const.STANDBY
            else INTERVAL_FAST
        )
        return state

    async def async_shutdown(self) -> None:
        """Stop polling and close the transport, including after partial setup."""
        if self._stopped:
            return
        self._shutting_down = True
        self._lens_press_token = None
        await super().async_shutdown()
        async with self._lens_lock:
            try:
                for attempt in range(3):
                    try:
                        await self._stop_lens_locked()
                    except (HomeAssistantError, ValueError):
                        if attempt == 2:
                            _LOGGER.exception("Unable to stop lens during shutdown")
                            raise
                        await asyncio.sleep(0.2)
                    else:
                        break
            finally:
                self._stopped = True
                async with self._operation_lock:
                    await self.device.disconnect()
