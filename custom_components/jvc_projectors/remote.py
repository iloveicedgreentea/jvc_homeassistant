"""Implement JVC component."""
from collections.abc import Iterable
import logging

from jvc_projector.jvc_projector import JVCProjector
import voluptuous as vol

from homeassistant.components.remote import PLATFORM_SCHEMA, RemoteEntity
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    INFO_COMMAND,
)

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_TIMEOUT): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Set up platform."""
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    password = config.get(CONF_PASSWORD)
    jvc_client = JVCProjector(
        host=host,
        password=password,
        logger=_LOGGER,
        connect_timeout=config.get(CONF_TIMEOUT),
    )
    # create a long lived connection
    jvc_client.open_connection()
    add_entities(
        [
            JVCRemote(name, host, jvc_client),
        ]
    )

class JVCRemote(RemoteEntity):
    """Implements the interface for JVC Remote in HA."""

    def __init__(
        self,
        name: str,
        host: str,
        jvc_client: JVCProjector = None,
    ) -> None:
        """JVC Init."""
        self._name = name
        self._host = host
        # use 5 second timeout, try to prevent error loops
        self._state = False
        self._lowlatency_enabled = False
        self._installation_mode = ""
        self._input_mode = ""
        self._laser_mode = ""
        self._eshift = ""
        self._color_mode = ""
        self._input_level = ""
        # Because we can only have one connection at a time, we need to lock every command
        # otherwise JVC's server implementation will cancel the running command
        # and just confuse everything, then cause HA to freak out
        self.jvc_client = jvc_client

    @property
    def should_poll(self):
        """Poll."""
#       
        # Polling is disabled as it is unreliable and will lock up commands at the moment
        # Requires adding stronger locking and command buffering
        return True

    @property
    def name(self):
        """Name."""
        return self._name

    @property
    def host(self):
        """Host."""
        return self._host

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        # These are bools. Useful for making sensors
        return {
            "power_state": self._state,
            "installation_mode": self._installation_mode,
            "input_mode": self._input_mode,
            "laser_mode": self._laser_mode, 
            "eshift": self._eshift, 
            "color_mode": self._color_mode,
            "input_level": self._input_level,
            "low_latency": self._lowlatency_enabled
        }

    @property
    def is_on(self):
        """Return the last known state of the projector."""

        return self._state

    def turn_on(self, **kwargs):
        """Send the power on command."""

        self.jvc_client.power_on()
        self._state = True

    def turn_off(self, **kwargs):
        """Send the power off command."""

        self.jvc_client.power_off()
        self._state = False

    def update(self):
        """Retrieve latest state."""
        self._state = self.jvc_client.is_on()

        if self._state:
            self._lowlatency_enabled = self.jvc_client.is_ll_on()()
        
            self._installation_mode = self.jvc_client.get_install_mode()
        
            self._input_mode = self.jvc_client.get_input_mode()
        
            self._laser_mode = self.jvc_client.get_laser_mode()
        
            self._eshift = self.jvc_client.get_eshift_mode()
        
            self._color_mode = self.jvc_client.get_color_mode()
        
            self._input_level = self.jvc_client.get_input_level()  

    def send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""

        self.jvc_client.exec_command(command)

    def service_info(self) -> None:
        """Bring up the info screen."""

        self.jvc_client.info()
