"""Module for representing a JVC Projector network connection."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import socket

from .error import JvcProjectorConnectError


class JvcConnection:
    """Class for representing a JVC Projector network connection."""

    def __init__(self, ip: str, port: int, timeout: float):
        """Initialize class."""
        self._ip = ip
        self._port = port
        self._timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    @property
    def ip(self) -> str:
        """Return ip address."""
        return self._ip

    @property
    def port(self) -> int:
        """Return port."""
        return self._port

    def is_connected(self) -> bool:
        """Return if connected to device."""
        return self._reader is not None and self._writer is not None

    async def connect(self) -> None:
        """Connect to device."""
        assert self._reader is None and self._writer is None
        conn = asyncio.open_connection(self._ip, self._port)
        self._reader, self._writer = await asyncio.wait_for(conn, timeout=self._timeout)

    async def read(self, n: int) -> bytes:
        """Read n bytes from device."""
        assert self._reader
        return await asyncio.wait_for(
            self._reader.readexactly(n), timeout=self._timeout
        )

    async def readline(self, timeout: float | None = None) -> bytes:
        """Read all bytes up to newline from device.

        Args:
            timeout: Optional timeout override. Uses default if not specified.

        """
        assert self._reader
        return await asyncio.wait_for(
            self._reader.readline(),
            timeout=self._timeout if timeout is None else timeout,
        )

    async def write(self, data: bytes) -> None:
        """Write data to device."""
        assert self._writer
        self._writer.write(data)
        await asyncio.wait_for(self._writer.drain(), timeout=self._timeout)

    async def disconnect(self) -> None:
        """Disconnect from device."""
        writer = self._writer
        self._writer = None
        self._reader = None
        if writer:
            writer.close()
            # Closing an already broken connection must not hide the real error.
            with suppress(asyncio.TimeoutError, OSError):
                await asyncio.wait_for(writer.wait_closed(), timeout=self._timeout)


async def resolve(host: str) -> str:
    """Resolve a hostname to its first IPv4 address using the system resolver."""
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host, None, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
    except OSError as err:
        raise JvcProjectorConnectError(f"Failed to resolve host {host}") from err

    for family, _socktype, _protocol, _canonical, address in addresses:
        if family == socket.AF_INET:
            return address[0]
    raise JvcProjectorConnectError(f"No IPv4 addresses returned for host {host}")
