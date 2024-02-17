"""The JVC Projector integration."""

from __future__ import annotations
from jvc_projector.jvc_projector import JVCProjectorCoordinator, JVCInput
import logging
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORM_SCHEMA
_LOGGER = logging.getLogger("JVC_projectors")
# PLATFORMS: list[Platform] = [Platform.REMOTE]


async def async_setup_entry(hass, entry):
    """Set up JVC Projector from a config entry."""
    host = entry.data.get(CONF_HOST)
    password = entry.data.get(CONF_PASSWORD)
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL)
    timeout = entry.data.get(CONF_TIMEOUT, 3)
    port = 20554

    options = JVCInput(host, password, port, timeout)
    # Create a coordinator or directly set up your entities with the provided information
    coordinator = JVCProjectorCoordinator(options, _LOGGER)

    # Store the coordinator in hass.data for use by your platform (e.g., remote)
    hass.data[DOMAIN] = coordinator

    # Forward the setup to the platform, e.g., remote
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "remote")
    )

    return True

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the component from configuration.yaml."""
    if DOMAIN not in config:
        return True

    for conf in config[DOMAIN]:
        # Check if an entry for this configuration already exists
        if any(entry.data.get(PLATFORM_SCHEMA) == conf[PLATFORM_SCHEMA] for entry in hass.config_entries.async_entries(DOMAIN)):
            continue

        # If the entry does not exist, create a new config entry
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf
            )
        )

    return True