"""Module for interacting with a JVC Projector."""

from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable, Iterable, Mapping
import logging
import re
from . import command
from .command import JvcCommand, JvcCommandHelpers
from .connection import resolve
from .device import JvcDevice
from .error import JvcProjectorConnectError, JvcProjectorError
from . import const

DEFAULT_PORT = 20554
DEFAULT_TIMEOUT = 15.0

_LOGGER = logging.getLogger(__name__)


class JvcProjector:
    """Class for interacting with a JVC Projector."""

    def __init__(
        self,
        host: str,
        *,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        password: str | None = None,
    ) -> None:
        """Initialize class."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._password = password

        self._device: JvcDevice | None = None
        self._ip: str = ""
        self._model: str = ""
        self._mac: str = ""
        self._version: str = ""
        self._dict: dict[str, str] = {}

    @property
    def ip(self) -> str:
        """Returns ip."""
        if not self._ip:
            raise JvcProjectorError("ip not initialized")
        return self._ip

    @property
    def host(self) -> str:
        """Returns host."""
        return self._host

    @property
    def port(self) -> int:
        """Returns port."""
        return self._port

    @property
    def model(self) -> str:
        """Returns model name."""
        if not self._model:
            raise JvcProjectorError("model not initialized")
        return self.process_model_code(self._model)

    @property
    def mac(self) -> str:
        """Returns mac address."""
        if not self._mac:
            raise JvcProjectorError("mac address not initialized")
        return self._mac

    @property
    def version(self) -> str:
        """Get device software version."""
        if not self._version:
            raise JvcProjectorError("version address not initialized")
        return self.process_version(self._version)

    async def is_on(self) -> bool:
        """Return if device is fully on and ready."""
        return await self.get_power() == const.ON

    async def connect(self, get_info: bool = False) -> None:
        """Connect to device."""
        if self._device:
            return

        if not self._ip:
            self._ip = await resolve(self._host)

        self._device = JvcDevice(self._ip, self._port, self._timeout, self._password)

        try:
            if not await self.test():
                raise JvcProjectorConnectError("Failed to verify connection")  # noqa: TRY301

            if get_info:
                await self.get_info()
        except (Exception, asyncio.CancelledError):
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Disconnect from device."""
        if self._device:
            await self._device.disconnect()
            self._device = None

    async def get_info(self) -> dict[str, str]:
        """Get device info.

        Returns:
            dict[str, str]: Dictionary containing model and MAC address

        Raises:
            JvcProjectorError: If device is not connected or MAC address is unavailable

        """
        if not self._device:
            raise JvcProjectorError("Must call connect before getting info")

        # Create base commands that work regardless of power state
        model = JvcCommand(const.CMD_MODEL, True)
        mac = JvcCommand(const.CMD_LAN_SETUP_MAC_ADDRESS, True)
        commands = [model, mac]
        _LOGGER.debug("Getting info with commands %s", commands)

        # Only add version command if projector is on
        is_on = await self.is_on()
        if is_on:
            _LOGGER.debug("Projector is on, adding version command")
            version = JvcCommand(const.CMD_VERSION, True)
            commands.append(version)

        # Send commands
        await self._send(commands)
        _LOGGER.debug("Got responses %s", [cmd.response for cmd in commands])

        # Validate
        if mac.response is None:
            raise JvcProjectorError("MAC address not available")

        # responses
        self._model = model.response or "(unknown)"
        self._mac = mac.response  # None checked above
        self._version = version.response if is_on and version.response else "(unknown)"

        return {const.KEY_MODEL: self._model, const.KEY_MAC: self._mac}

    async def get_state(
        self,
        *,
        requested_keys: Iterable[str] | None = None,
        reference_reader: Callable[[str], Awaitable[str | None]] | None = None,
    ) -> Mapping[str, str | None]:
        """Get state, polling extra settings only when their keys are requested.

        An optional reference reader owns connection and serialization for each
        complete reference exchange. This lets callers yield between references
        to prioritize controls without interrupting an in-flight response. A
        reader exception aborts the snapshot before it replaces cached state.
        Without a reader, references retain the original batched behavior.
        """
        if not self._device and reference_reader is None:
            raise JvcProjectorError("Must call connect before getting state")

        # Add static values
        requested = None if requested_keys is None else set(requested_keys)
        state = {
            const.KEY_MODEL: self.process_model_code(self._model),
            const.KEY_VERSION: self.process_version(self._version),
            const.KEY_MAC: self.process_mac(self._mac),
        }

        async def send_and_update(commands: dict[str, str]) -> None:
            """Send commands and update the dictionary."""
            if requested is not None:
                dependencies = {const.KEY_POWER, const.KEY_SOURCE, const.KEY_HDR}
                commands = {
                    key: code
                    for key, code in commands.items()
                    if key in requested or key in dependencies
                }
            if not commands:
                return
            if reference_reader is None:
                # Preserve batching for callers that own the complete refresh.
                cmd_vals = [JvcCommand(cmd, True) for cmd in commands.values()]
                res = await self._send(cmd_vals)
            else:
                res = [await reference_reader(code) for code in commands.values()]
            # discard the command values and zip the keys with the responses
            state.update(
                {
                    key: value
                    for key, value in zip(commands, res, strict=True)
                    if value is not None
                }
            )

        # Always get power state
        await send_and_update({const.KEY_POWER: const.CMD_POWER})

        # If power is on, get additional states
        if state.get(const.KEY_POWER) == const.ON:
            if self._version in ("", "(unknown)"):
                version = (
                    await self.get_version()
                    if reference_reader is None
                    else await reference_reader(const.CMD_VERSION)
                )
                self._version = version or "(unknown)"
                state[const.KEY_VERSION] = self.process_version(self._version)
            await send_and_update(
                {
                    const.KEY_INPUT: const.CMD_INPUT,
                    const.KEY_SOURCE: const.CMD_SOURCE,
                    const.KEY_PICTURE_MODE: const.CMD_PICTURE_MODE,
                    const.KEY_LOW_LATENCY: const.CMD_PICTURE_MODE_LOW_LATENCY,
                    const.KEY_LASER_POWER: const.CMD_PICTURE_MODE_LASER_POWER,
                    const.KEY_LASER_TIME: const.CMD_FUNCTION_LASER_TIME,
                    const.KEY_ANAMORPHIC: const.CMD_INSTALLATION_ANAMORPHIC,
                    **(
                        {const.KEY_INSTALLATION_MODE: const.CMD_INSTALLATION_MODE}
                        if state[const.KEY_MODEL] not in const.MODERN_MODELS
                        else {}
                    ),
                }
            )

            if state[const.KEY_MODEL] in const.MODERN_MODELS:
                optional = {
                    const.KEY_ALLM: const.CMD_INPUT_SIGNAL_ALLM,
                    const.KEY_DEEP_BLACK: const.CMD_PICTURE_MODE_DEEP_BLACK,
                    const.KEY_FILMMAKER_AUTO: const.CMD_INPUT_SIGNAL_FILMMAKER_AUTO,
                    const.KEY_HIGHLIGHT_COLOR: const.CMD_PICTURE_MODE_HIGHLIGHT_COLOR,
                    const.KEY_SMOOTHER: const.CMD_PICTURE_MODE_SMOOTHER,
                }
                await send_and_update(
                    {
                        key: code
                        for key, code in optional.items()
                        if requested is not None and key in requested
                    }
                )

            # Check if there's a signal before getting signal-dependent states
            if state.get(const.KEY_SOURCE) == const.SIGNAL:
                await send_and_update(
                    {
                        const.KEY_HDR: const.CMD_FUNCTION_HDR,
                        const.KEY_HDMI_INPUT_LEVEL: const.CMD_INPUT_SIGNAL_HDMI_INPUT_LEVEL,
                        const.KEY_HDMI_COLOR_SPACE: const.CMD_INPUT_SIGNAL_HDMI_COLOR_SPACE,
                        const.KEY_COLOR_PROFILE: const.CMD_PICTURE_MODE_COLOR_PROFILE,
                        const.KEY_GRAPHICS_MODE: const.CMD_PICTURE_MODE_GRAPHICS_MODE,
                        const.KEY_COLOR_SPACE: const.CMD_FUNCTION_COLOR_SPACE,
                        const.KEY_RESOLUTION: const.CMD_FUNCTION_SOURCE,
                    }
                )
                optional = {
                    const.KEY_DEEP_COLOR: const.CMD_FUNCTION_DEEP_COLOR,
                    const.KEY_COLORIMETRY: const.CMD_FUNCTION_COLORIMETRY,
                }
                await send_and_update(
                    {
                        key: code
                        for key, code in optional.items()
                        if requested is not None and key in requested
                    }
                )

            # NX9 and NZ model specific commands
            if "NZ" in state[const.KEY_MODEL] or "NX9" in state[const.KEY_MODEL]:
                await send_and_update(
                    {
                        const.KEY_ESHIFT: const.CMD_PICTURE_MODE_8K_ESHIFT,
                        const.KEY_CLEAR_MOTION_DRIVE: const.CMD_PICTURE_MODE_CLEAR_MOTION_DRIVE,
                        const.KEY_MOTION_ENHANCE: const.CMD_PICTURE_MODE_MOTION_ENHANCE,
                        const.KEY_LASER_VALUE: const.CMD_PICTURE_MODE_LASER_VALUE,
                        const.KEY_LASER_DIMMING: const.CMD_LASER_DIMMING,
                    }
                )

            # HDR-specific commands
            if (
                state.get(const.KEY_HDR)
                not in [None, const.HDR_CONTENT_NONE, const.HDR_CONTENT_SDR]
            ) and state.get(const.KEY_SOURCE) == const.SIGNAL:
                await send_and_update(
                    {
                        const.KEY_HDR_PROCESSING: const.CMD_PICTURE_MODE_HDR_PROCESSING,
                        const.KEY_HDR_CONTENT_TYPE: const.CMD_PICTURE_MODE_HDR_CONTENT_TYPE,
                    }
                )

        self._dict = state
        return dict(state)

    def process_mac(self, mac: str) -> str:
        """Process mac address."""
        # skip every 2 characters and join with :
        return ":".join(mac[i : i + 2] for i in range(0, len(mac), 2))

    def process_model_code(self, model: str) -> str:
        """Process model code."""
        return const.MODEL_MAP.get(model[-4:], f"{model}: Unknown")

    def process_version(self, version: str) -> str:
        """Process version string."""

        if not version or version == "(unknown)":
            return "(unknown)"

        version = version.strip().removesuffix("PJ").strip()
        if re.fullmatch(r"\d{2}-\d{3}", version, flags=re.ASCII):
            return f"{int(version[:2])}.{version[3:]}"
        if not version.isascii() or not version.isdigit() or len(version) > 4:
            return version
        version = version.zfill(4)

        # Extract major, minor, and patch versions
        major = str(
            int(version[0:2])
        )  # Remove leading zero and convert to int then back to str
        minor = str(int(version[2]))
        patch = str(int(version[3]))

        return f"{major}.{minor}.{patch}"

    async def get_version(self) -> str | None:
        """Get device software version."""
        return await self.ref(const.CMD_VERSION)

    async def get_power(self) -> str | None:
        """Get power state."""
        return await self.ref(const.CMD_POWER)

    async def get_input(self) -> str | None:
        """Get current input."""
        return await self.ref(const.CMD_INPUT)

    async def get_signal(self) -> str | None:
        """Get if has signal."""
        return await self.ref(const.CMD_SOURCE)

    async def test(self) -> bool:
        """Run test command."""
        cmd = JvcCommand(f"{command.TEST}")
        await self._send([cmd])
        return cmd.ack

    async def power_on(self) -> None:
        """Run power on command."""
        await self.op(f"{const.CMD_POWER}1")

    async def power_off(self) -> None:
        """Run power off command."""
        await self.op(f"{const.CMD_POWER}0")

    async def remote(self, code: str) -> None:
        """Run remote code command."""
        if not isinstance(code, str) or re.fullmatch(r"[0-9a-fA-F]{4}", code) is None:
            raise ValueError("Remote code must contain exactly four hexadecimal digits")
        await self.op(f"{const.CMD_REMOTE}{code.upper()}")

    async def lens_move(self, direction: str, *, start: bool) -> None:
        """Start or stop a continuous lens motor on a documented model.

        The caller must ensure a matching stop, including after cancellation or
        an uncertain start response. Only one motor may run at a time. Closing
        the TCP connection is not a documented motor stop.
        """
        if not isinstance(direction, str) or direction not in const.LENS_COMMANDS:
            raise ValueError("Unknown lens direction")
        if not isinstance(start, bool):
            raise ValueError("Lens start must be a boolean")  # noqa: TRY004
        model = self.process_model_code(self._model)
        if model not in const.LENS_MODELS:
            raise ValueError(f"Continuous lens movement is not verified for {model}")
        await self.op(f"{const.LENS_COMMANDS[direction]}{int(start)}")

    async def lens_step(self, direction: str) -> None:
        """Move one native lens step on a documented model, without repetition.

        The caller must serialize this with continuous motor operations; only
        one motor may run at a time. The single-shot commands take no parameter.
        """
        if not isinstance(direction, str) or direction not in const.LENS_STEP_COMMANDS:
            raise ValueError("Unknown lens direction")
        model = self.process_model_code(self._model)
        if model not in const.LENS_MODELS:
            raise ValueError(f"Lens steps are not verified for {model}")
        await self.op(const.LENS_STEP_COMMANDS[direction])

    async def op(self, code: str) -> None:
        """Send operation code."""
        await self._send([JvcCommand(code, False)])

    async def ref(self, code: str) -> str | None:
        """Send reference code."""
        return (await self._send([JvcCommand(code, True)]))[0]

    async def _send(self, cmds: list[JvcCommand]) -> list[str | None]:
        """Send command to device."""
        if self._device is None:
            raise JvcProjectorError("Must call connect before sending commands")

        model = self.process_model_code(self._model)
        for cmd in cmds:
            cmd.model = model
        await self._device.send(cmds)

        return [cmd.response for cmd in cmds]

    async def send_command(self, cmd: str, val: str) -> None:
        """Send a command to the projector using well-known names like "power". Intended to be human readable commands."""
        model = self.process_model_code(self._model)
        cmd, val = self.validate_command(cmd, val, model=model)
        raw_cmd = const.KEY_MAP_TO_COMMAND[cmd]
        command_info = JvcCommand.command_map[raw_cmd]
        inverse = command_info["inverse"]
        if model in const.MODERN_MODELS and raw_cmd in const.MODERN_COMMAND_VALUES:
            inverse = {
                value: code
                for code, value in const.MODERN_COMMAND_VALUES[raw_cmd].items()
            }
        value = inverse[val]
        await self.op(f"{raw_cmd}{value}")

    @staticmethod
    def validate_command(
        cmd: str, val: str, *, model: str | None = None
    ) -> tuple[str, str]:
        """Validate a named operation without connecting or changing device state."""
        if not isinstance(cmd, str) or not isinstance(val, str):
            raise ValueError("Command and value must be strings")  # noqa: TRY004
        cmd, val = cmd.strip().lower(), val.strip().lower()
        raw_cmd = const.KEY_MAP_TO_COMMAND.get(cmd)
        if raw_cmd is None:
            raise ValueError(f"Unknown command: {cmd}")
        command_info = JvcCommand.command_map.get(raw_cmd, {})
        if not command_info:
            raise ValueError(f"Unknown command: {cmd}")
        if (
            raw_cmd.startswith("IF")
            or JvcCommandHelpers.COMMAND_VALUE_OVERRIDES.get(cmd, True) is None
        ):
            raise ValueError(f"Command is read-only: {cmd}")
        inverse = command_info.get("inverse", {})
        if model in const.MODERN_MODELS and raw_cmd in const.MODERN_COMMAND_VALUES:
            inverse = {
                value: code
                for code, value in const.MODERN_COMMAND_VALUES[raw_cmd].items()
            }
        if not inverse:
            raise ValueError(f"Command is read-only: {cmd}")
        allowed = JvcCommandHelpers.COMMAND_VALUE_OVERRIDES.get(cmd, inverse)
        if val not in inverse or val not in allowed:
            raise ValueError(f"Invalid value for {cmd}: {val}")
        return cmd, val

    def is_command_supported(self, code: str) -> bool:
        """Return whether a reference is outside its temporary timeout backoff."""
        if self._device is None:
            return True
        return self._device.is_command_supported(code)

    def clear_unsupported_commands(self) -> None:
        """Clear the cache of unsupported commands to retry them."""
        if self._device is not None:
            self._device.clear_unsupported_commands()

    def get_unsupported_commands(self) -> set[str]:
        """Get the set of commands that have been marked as unsupported."""
        if self._device is None:
            return set()
        return self._device.get_unsupported_commands()
