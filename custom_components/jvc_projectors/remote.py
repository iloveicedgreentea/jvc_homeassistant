from homeassistant.components.remote import RemoteEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.helpers import entity_platform, config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from jvc_projector import JVCProjector
import logging
import voluptuous as vol
import asyncio

from .const import (
    INFO_COMMAND,
    HDR_MODE_COMMAND,
    SDR_MODE_COMMAND,
    GAMING_MODE_HDR_COMMAND,
    GAMING_MODE_SDR_COMMAND,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """
    Set up platform.
    """
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    password = config.get(CONF_PASSWORD)
    # IF this is not high enough connections will start tripping over each other
    # TODO: implement some kind of global locking
    SCAN_INTERVAL = config.get(CONF_SCAN_INTERVAL)
    # Have HA fetch data first with True
    async_add_entities(
        [
            JVCRemote(name, host, password),
        ]
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        INFO_COMMAND, {}, f"service_async_{INFO_COMMAND}"
    )
    platform.async_register_entity_service(
        GAMING_MODE_HDR_COMMAND, {}, f"service_async_{GAMING_MODE_HDR_COMMAND}"
    )
    platform.async_register_entity_service(
        GAMING_MODE_SDR_COMMAND, {}, f"service_async_{GAMING_MODE_SDR_COMMAND}"
    )
    platform.async_register_entity_service(
        HDR_MODE_COMMAND, {}, f"service_async_{HDR_MODE_COMMAND}"
    )
    platform.async_register_entity_service(
        SDR_MODE_COMMAND, {}, f"service_async_{SDR_MODE_COMMAND}"
    )


class JVCRemote(RemoteEntity):
    """
    Implements the interface for JVC Remote in HA
    """

    def __init__(self, name: str, host: str, password: str) -> None:
        self._name = name
        self._host = host
        self.password = password
        self.jvc_client = JVCProjector(host=host, password=password, logger=_LOGGER)
        self._state = None
        self._ll_state = None
        # Because we can only have one connection at a time, we need to lock every command
        self._lock = asyncio.Lock()

    @property
    def should_poll(self):
        # poll the device so we know if it was state changed
        # via an external method, like the physical remote
        return True

    @property
    def name(self):
        return self._name

    @property
    def host(self):
        return self._host

    @property
    def extra_state_attributes(self):
        """
        Return extra state attributes.
        """

        return {"power_state": self._state, "low_latency": self._ll_state}

    @property
    def is_on(self):
        """
        Return the last known state of the projector
        """

        return self._state

    async def async_turn_on(self, **kwargs):
        """Send the power on command."""

        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")
            
        async with self._lock:
            return await self.jvc_client.async_power_on()

    async def async_turn_off(self, **kwargs):
        """Send the power off command."""

        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            return await self.jvc_client.async_power_off()

    async def _async_collect_updates(self):
        """
        Run each update sequentially. Attributes to update should be added here
        """

        async def run_updates():
            self._state = await self.jvc_client.async_is_on()
            self._ll_state = await self.jvc_client.async_get_low_latency_state()

        loop = asyncio.get_event_loop()
        task = loop.create_task(run_updates())

        await task

    async def async_update(self):
        """Retrieve latest state."""
        # lock to prevent concurrent connections
        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            await self._async_collect_updates()

    async def async_send_command(self, command: list[str], **kwargs):
        """Send commands to a device."""
        # Wait until unlocked so commmands dont cause a failure loop
        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            return await self.jvc_client.async_exec_command(command)

    async def service_async_info(self) -> None:
        """
        Brings up the info screen
        """
        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            return await self.jvc_client.async_info()

    async def service_async_gaming_mode_hdr(self) -> None:
        """
        Sets optimal gaming modes
        """
        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            return await self.jvc_client.async_gaming_mode_hdr()

    async def service_async_gaming_mode_sdr(self) -> None:
        """
        Sets optimal gaming modes
        """
        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            return await self.jvc_client.async_gaming_mode_sdr()

    async def service_async_hdr_picture_mode(self) -> None:
        """
        Sets optimal HDR modes
        """
        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            return await self.jvc_client.async_hdr_picture_mode()

    async def service_async_sdr_picture_mode(self) -> None:
        """
        Sets optimal SDR modes
        """
        while self._lock.locked():
            _LOGGER.debug("State is locked. Waiting to run command")

        async with self._lock:
            return await self.jvc_client.async_sdr_picture_mode()
