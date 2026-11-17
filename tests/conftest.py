"""Fixtures using the real Home Assistant custom-integration harness."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.jvc_projector._vendor.jvcprojector import const
from custom_components.jvc_projector._vendor.jvcprojector.projector import JvcProjector


@pytest.fixture(autouse=True)
def enable_custom_components(enable_custom_integrations):
    """Allow HA to discover this checkout's custom integration."""


@pytest.fixture
def projector():
    """A deterministic device boundary; HA itself is not stubbed."""
    device = MagicMock(spec=JvcProjector)
    device.host = "192.0.2.10"
    device.mac = "AABBCCDDEEFF"
    device.model = "NZ8"
    device.version = "1.0.0"
    device.connect = AsyncMock()
    device.disconnect = AsyncMock()
    device.remote = AsyncMock()
    device.lens_move = AsyncMock()
    device.lens_step = AsyncMock()
    device.send_command = AsyncMock()
    device.ref = AsyncMock(return_value=const.STANDBY)

    async def get_state(*, reference_reader=None, **kwargs):
        if reference_reader is not None:
            await reference_reader(const.CMD_POWER)
        return device.get_state.return_value

    device.get_state = AsyncMock(
        side_effect=get_state, return_value={const.KEY_POWER: const.STANDBY}
    )
    device.validate_command = JvcProjector.validate_command
    return device
