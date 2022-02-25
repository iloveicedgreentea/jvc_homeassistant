from homeassistant.components.remote import RemoteEntity, PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.helpers import entity_platform, config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from async_timeout import timeout
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
    # Maybe make this user supplied in the future
    # timeout = config.get(CONF_TIMEOUT)
    # IF this is not high enough connections will start tripping over each other
    SCAN_INTERVAL = config.get(CONF_SCAN_INTERVAL)
    async_add_entities(
        [
            JVCRemote(name, host, password),
        ]
    )

    platform = entity_platform.async_get_current_platform()
    # Register the services
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

    def __init__(
        self, name: str, host: str, password: str, timeout: str = None
    ) -> None:
        self._name = name
        self._host = host
        # Timeout for connections. Everything takes less than 3 seconds to run
        if timeout is None:
            self.timeout = 5
        else:
            self.timeout = int(timeout)
        # use 5 second timeout, try to prevent error loops
        self.jvc_client = JVCProjector(
            host=host, password=password, logger=_LOGGER, connect_timeout=self.timeout
        )
        self._state = None
        self._ll_state = None
        # Because we can only have one connection at a time, we need to lock every command
        # otherwise JVC's server implementation will cancel the running command
        # and just confuse everything, then cause HA to freak out
        self._lock = asyncio.Lock()

    @property
    def should_poll(self):
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
        # These are bools. Useful for making sensors
        return {
            "power_state": self._state,
            "low_latency": self._ll_state,
            "host_ip": self._host,
            "timeout": self.timeout,
            # "command_in_flight": self._lock.locked(),
        }

    @property
    def is_on(self):
        """
        Return the last known state of the projector
        """

        return self._state

    async def async_turn_on(self, **kwargs):
        """Send the power on command."""

        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            _, success = await self.jvc_client.async_power_on()
            if success:
                self._state = True
            else:
                self._state = None

    async def async_turn_off(self, **kwargs):
        """Send the power off command."""

        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            _, success = await self.jvc_client.async_power_off()
            if success:
                self._state = False
            else:
                self._state = None

    async def _async_collect_updates(self):
        """
        Run each update sequentially. Attributes to update should be added here
        """
        # Okay clearly not enough locking
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to get power state")
        #     await asyncio.sleep(3)

        async with self._lock:
            # Try to make it so if something is hanging, just end the connection
            # otherwise it can just lock up the entire integration
            try:
                async with timeout(5):
                    self._state = await self.jvc_client.async_is_on()
            except asyncio.TimeoutError:
                _LOGGER.error("Timed out getting power state")
                return
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to get low latency state")
        #     await asyncio.sleep(3)

        async with self._lock:
            try:
                async with timeout(5):
                    self._ll_state = await self.jvc_client.async_get_low_latency_state()
            except asyncio.TimeoutError:
                _LOGGER.error("Timed out getting low latency state")
                return

    async def async_update(self):
        """Retrieve latest state."""
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run update")
        #     await asyncio.sleep(3)

        # await self._async_collect_updates()
        self._state = await self.jvc_client.async_is_on()
        # self._ll_state = await self.jvc_client.async_get_low_latency_state()

    async def async_send_command(self, command: list[str], **kwargs):
        """Send commands to a device."""
        # Wait until unlocked so commmands dont cause a failure loop
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            _, success = await self.jvc_client.async_exec_command(command)
            if success:
                if "power" in command and "on" in command:
                    self._state = True
                if "power" in command and "off" in command:
                    self._state = False

    async def service_async_info(self) -> None:
        """
        Brings up the info screen
        """
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            return await self.jvc_client.async_info()

    async def service_async_gaming_mode_hdr(self) -> None:
        """
        Sets optimal gaming modes
        """
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            return await self.jvc_client.async_gaming_mode_hdr()

    async def service_async_gaming_mode_sdr(self) -> None:
        """
        Sets optimal gaming modes
        """
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            return await self.jvc_client.async_gaming_mode_sdr()

    async def service_async_hdr_picture_mode(self) -> None:
        """
        Sets optimal HDR modes
        """
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            return await self.jvc_client.async_hdr_picture_mode()

    async def service_async_sdr_picture_mode(self) -> None:
        """
        Sets optimal SDR modes
        """
        # if self._lock.locked():
        #     _LOGGER.debug("State is locked. Waiting to run command")
        #     await asyncio.sleep(3)

        async with self._lock:
            return await self.jvc_client.async_sdr_picture_mode()
