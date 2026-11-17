"""Module for representing a JVC Projector device."""

from __future__ import annotations

import asyncio
from hashlib import sha256
import logging
import struct
from time import monotonic

from . import const
from .command import (
    AUTH_SALT,
    END,
    HEAD_ACK,
    HEAD_LEN,
    HEAD_OP,
    HEAD_REF,
    HEAD_RES,
    PJACK,
    PJNAK,
    PJNG,
    PJOK,
    PJREQ,
    JvcCommand,
)
from .connection import JvcConnection
from .error import (
    JvcProjectorAuthError,
    JvcProjectorCommandError,
    JvcProjectorConnectError,
)

KEEPALIVE_TTL = 2
REF_TIMEOUT = 3.0
UNSUPPORTED_TTL = 300.0
COMMAND_INTERVAL = 0.2
CRITICAL_REFERENCES = {
    const.CMD_POWER,
    const.CMD_MODEL,
    const.CMD_LAN_SETUP_MAC_ADDRESS,
}

_LOGGER = logging.getLogger(__name__)


class JvcDevice:
    """Class for representing a JVC Projector device."""

    def __init__(
        self, ip: str, port: int, timeout: float, password: str | None = None
    ) -> None:
        """Initialize class."""
        self._conn = JvcConnection(ip, port, timeout)

        self._auth = b""
        self._password = password or ""
        if password:
            encoded = password.encode()
            self._auth = struct.pack(f"{max(10, len(encoded))}s", encoded)

        self._lock = asyncio.Lock()
        self._keepalive: asyncio.Task | None = None
        self._last: float = 0.0
        self._last_command_finished: float | None = None
        self._unsupported_commands: dict[str, float] = {}

    async def send(self, cmds: list[JvcCommand]) -> None:
        """Send commands to device."""
        if not cmds:
            return
        async with self._lock:
            # Treat status refreshes with special handling
            # if any cmd is a ref, and the first cmd is a power cmd
            is_refresh = (
                any(cmd.is_ref for cmd in cmds) and len(cmds) > 1 and cmds[0].is_power
            )
            _LOGGER.debug("Sending %s", "refresh" if is_refresh else "commands")

            # Connection keepalive window for fast command repeats
            keepalive = True

            if self._keepalive:
                self._keepalive.cancel()
                self._keepalive = None
            elif is_refresh:
                # Don't extend window below if this was a refresh
                keepalive = False

            cmd = None
            try:
                for cmd in cmds:
                    # Reset reused commands before considering cached failures.
                    cmd.ack = False
                    cmd.response = None
                    if cmd.is_ref and not self.is_command_supported(cmd.code):
                        continue
                    if not self._conn.is_connected():
                        await self._connect()
                    # Keep the projector's recovery interval between commands,
                    # without delaying the caller after the final response.
                    if self._last_command_finished is not None:
                        delay = COMMAND_INTERVAL - (
                            monotonic() - self._last_command_finished
                        )
                        if delay > 0:
                            await asyncio.sleep(delay)
                    try:
                        try:
                            await self._send(cmd)
                        finally:
                            # A failed or cancelled exchange may still have
                            # reached the projector; retain its recovery time.
                            self._last_command_finished = monotonic()
                    except asyncio.TimeoutError as err:
                        # A timeout is not proof of an unsupported feature. Retry
                        # optional reads later and discard any late TCP response.
                        await self._disconnect()
                        if not cmd.is_ref or cmd.code in CRITICAL_REFERENCES:
                            raise JvcProjectorConnectError(
                                f"Response timeout for '{cmd.code}'"
                            ) from err
                        self._unsupported_commands[cmd.code] = (
                            monotonic() + UNSUPPORTED_TTL
                        )
                        _LOGGER.debug(
                            "Temporarily skipping unresponsive reference '%s'", cmd.code
                        )
                        continue
                    # If device is not powered on, skip remaining commands
                    # mac cannot be is_refresh here and first command must be pw if its a refresh
                    if is_refresh and cmds[0].response != const.ON:
                        _LOGGER.debug(
                            "Skipping commands due to power off which are %s",
                            [c.code for c in cmds],
                        )
                        break
            except (OSError, asyncio.IncompleteReadError) as err:
                keepalive = False
                raise JvcProjectorConnectError(
                    "Connection lost while sending command"
                ) from err
            except (Exception, asyncio.CancelledError):
                keepalive = False
                raise
            finally:
                # Delay disconnect to keep connection alive.
                if keepalive and cmd and cmd.ack:
                    self._keepalive = asyncio.create_task(
                        self._disconnect(KEEPALIVE_TTL)
                    )
                else:
                    await self._disconnect()

    async def _connect(self, *, use_sha256: bool = False) -> None:
        """Connect to device."""
        assert not self._conn.is_connected()

        elapsed = monotonic() - self._last
        if elapsed < 0.75:
            await asyncio.sleep(0.75 - elapsed)

        retries = 0
        while retries < 10:
            try:
                _LOGGER.debug("Connecting to %s", self._conn.ip)
                await self._conn.connect()
            except ConnectionRefusedError:
                retries += 1
                if retries == 5:
                    _LOGGER.warning("Retrying refused connection")
                else:
                    _LOGGER.debug("Retrying refused connection")
                await asyncio.sleep(0.2 * retries)
                continue
            except (asyncio.TimeoutError, OSError) as err:
                raise JvcProjectorConnectError from err

            try:
                data = await self._conn.read(len(PJOK))
            except (asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
                raise JvcProjectorConnectError("Handshake init timeout") from err

            _LOGGER.debug("Handshake received %s", data)

            if data == PJNG:
                _LOGGER.warning("Handshake retrying on busy")
                await self._conn.disconnect()
                retries += 1
                await asyncio.sleep(0.25 * retries)
                continue

            if data != PJOK:
                raise JvcProjectorCommandError("Handshake init invalid")

            break
        else:
            raise JvcProjectorConnectError("Retries exceeded")

        _LOGGER.debug("Handshake sending '%s'", PJREQ.decode())
        hashed_auth = (
            sha256(f"{self._password}{AUTH_SALT}".encode()).hexdigest().encode()
        )
        auth = hashed_auth if use_sha256 else self._auth
        await self._conn.write(PJREQ + (b"_" + auth if auth else b""))

        try:
            data = await self._conn.read(len(PJACK))
            _LOGGER.debug("Handshake received %s", data)

            if data == PJNAK and not use_sha256 and self._auth != hashed_auth:
                _LOGGER.debug("Standard auth failed, trying SHA256 auth")
                # A rejected authentication can close the stream. Start the
                # alternate handshake on a new connection instead of reusing it.
                await self._conn.disconnect()
                await self._connect(use_sha256=True)
                return

            if data == PJNAK:
                raise JvcProjectorAuthError

            if data != PJACK:
                raise JvcProjectorCommandError("Handshake ack invalid")

        except (asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
            raise JvcProjectorConnectError("Handshake ack timeout") from err

        self._last = monotonic()
        self._auth = auth

    def is_command_supported(self, code: str) -> bool:
        """Return whether a reference is outside its temporary timeout backoff."""
        expires = self._unsupported_commands.get(code)
        if expires is not None and monotonic() >= expires:
            del self._unsupported_commands[code]
            return True
        return expires is None

    def get_unsupported_commands(self) -> set[str]:
        """Return references currently backing off after a timeout."""
        return {
            code
            for code in tuple(self._unsupported_commands)
            if not self.is_command_supported(code)
        }

    def clear_unsupported_commands(self) -> None:
        """Clear the cache of unsupported commands."""
        self._unsupported_commands.clear()

    async def _send(self, cmd: JvcCommand) -> None:
        """Send command to device."""
        assert self._conn.is_connected()
        assert len(cmd.code) >= 2

        code = cmd.code.encode()
        data = (HEAD_REF if cmd.is_ref else HEAD_OP) + code + END

        _LOGGER.debug(
            "Sending %s '%s (%s)'", "ref" if cmd.is_ref else "op", cmd.code, data
        )
        await self._conn.write(data)

        timeout = REF_TIMEOUT if cmd.is_ref else None
        data = await self._conn.readline(timeout=timeout)

        _LOGGER.debug("Received ack %s", data)

        if data != HEAD_ACK + code[0:2] + END:
            raise JvcProjectorCommandError(
                f"Response ack invalid '{data!r}' for '{cmd.code}' expected '{HEAD_ACK + code[0:2]!r}'"
            )

        if cmd.is_ref:
            data = await self._conn.readline(timeout=REF_TIMEOUT)

            _LOGGER.debug("Received ref %s (%s)", data[HEAD_LEN + 2 : -1], data)

            if not data.startswith(HEAD_RES + code[0:2]) or not data.endswith(END):
                raise JvcProjectorCommandError(
                    f"Ref ack invalid '{data!r}' for '{cmd.code}'"
                )

            try:
                cmd.response = data[HEAD_LEN + 2 : -1].decode()
            except UnicodeDecodeError:
                cmd.response = data.hex()
                _LOGGER.warning("Failed to decode response '%s'", data)

        cmd.ack = True

    async def disconnect(self) -> None:
        """Disconnect from device."""
        async with self._lock:
            if self._keepalive:
                self._keepalive.cancel()
            await self._disconnect()

    async def _disconnect(self, delay: int = 0) -> None:
        """Disconnect from device after an optional idle period."""
        if delay:
            await asyncio.sleep(delay)
            async with self._lock:
                await self._disconnect()
            return
        self._keepalive = None
        await self._conn.disconnect()
        _LOGGER.debug("Disconnected")
