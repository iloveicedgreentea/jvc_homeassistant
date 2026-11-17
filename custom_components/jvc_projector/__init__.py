"""The JVC Projector integration."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from ._vendor.jvcprojector.device import JvcProjectorAuthError
from ._vendor.jvcprojector.error import JvcProjectorError
from ._vendor.jvcprojector.projector import DEFAULT_PORT, JvcProjector
from .coordinator import CONNECTION_TIMEOUT, JvcProjectorDataUpdateCoordinator

JVCConfigEntry = ConfigEntry[JvcProjectorDataUpdateCoordinator]
PLATFORMS = [Platform.BINARY_SENSOR, Platform.REMOTE, Platform.SELECT, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: JVCConfigEntry) -> bool:
    """Read device identity, fetch state, and set up the platforms."""
    device = JvcProjector(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        password=entry.data.get(CONF_PASSWORD),
    )
    try:
        async with asyncio.timeout(CONNECTION_TIMEOUT):
            await device.connect(True)
    except JvcProjectorAuthError as err:
        await device.disconnect()
        raise ConfigEntryAuthFailed("Password authentication failed") from err
    except (JvcProjectorError, OSError, TimeoutError) as err:
        await device.disconnect()
        raise ConfigEntryNotReady(f"Unable to connect to {device.host}: {err}") from err
    except BaseException:
        await device.disconnect()
        raise

    coordinator = entry.runtime_data = JvcProjectorDataUpdateCoordinator(
        hass, device, config_entry=entry
    )
    try:
        await coordinator.async_config_entry_first_refresh()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_shutdown()
        raise

    async def disconnect_on_stop(event: Event) -> None:
        """Close the connection before Home Assistant stops."""
        await coordinator.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, disconnect_on_stop)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JVCConfigEntry) -> bool:
    """Unload platforms before awaiting transport cleanup."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
        return True
    return False
