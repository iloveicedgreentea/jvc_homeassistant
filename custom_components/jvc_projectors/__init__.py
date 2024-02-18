"""The JVC Projector integration."""

from __future__ import annotations
from jvc_projector.jvc_projector import JVCProjectorCoordinator, JVCInput
import logging
import asyncio
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORM_SCHEMA

_LOGGER = logging.getLogger("JVC_projectors")


async def async_setup_entry(hass, entry):
    """Set up JVC Projector from a config entry."""
    host = entry.data.get(CONF_HOST)
    password = entry.data.get(CONF_PASSWORD)

    timeout = entry.data.get(CONF_TIMEOUT, 3)
    port = 20554
    _LOGGER.debug(f"Setting up JVC Projector with host: {host}")
    options = JVCInput(host, password, port, timeout)
    # Create a coordinator or directly set up your entities with the provided information
    coordinator = JVCProjectorCoordinator(options, _LOGGER)
    _LOGGER.debug("Set up coordinator")
    # Store the coordinator in hass.data for use by your platform (e.g., remote)
    hass.data[DOMAIN] = coordinator
    # Forward the setup to the platform, e.g., remote
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, Platform.REMOTE)
    )
    _LOGGER.debug(hass.data[DOMAIN])
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload JVC Projector configuration entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the component from configuration.yaml."""
    if DOMAIN not in config:
        return True
    for conf in config[DOMAIN]:
        # Check if an entry for this configuration already exists
        if any(
            entry.data.get(PLATFORM_SCHEMA) == conf[PLATFORM_SCHEMA]
            for entry in hass.config_entries.async_entries(DOMAIN)
        ):
            continue

        # If the entry does not exist, create a new config entry
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf
            )
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unloading of JVC Projector integration."""
    # Unload your integration's platforms (e.g., 'remote', 'sensor', etc.)
    _LOGGER.debug("Unloading JVC Projector integration")
    try:
        coordinator: JVCProjectorCoordinator = hass.data[DOMAIN]
        await coordinator.close_connection()
    except Exception as e:
        _LOGGER.error("Error closing JVC Projector connection - %s", e)
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, Platform.REMOTE)

    # If you have other resources to unload (listeners, services, etc.), do it here
    _LOGGER.debug("Unloaded JVC Projector integration")
    # Return True if unload was successful
    try:
        hass.data.pop(DOMAIN)
    except KeyError:
        pass
    return unload_ok
