"""Implement JVC component."""
from collections.abc import Iterable
import logging
import time
from jvc_projector.jvc_projector import JVCProjector
import voluptuous as vol

from homeassistant.components.remote import PLATFORM_SCHEMA, RemoteEntity
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
)
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
        vol.Required(CONF_SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_TIMEOUT): cv.positive_int,
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
        connect_timeout=int(config.get(CONF_TIMEOUT, 3)),
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
        # used when its ready to accept commands
        self._is_ready = False
        self._is_updating = False
        self._command_running = False
        # attributes

        self._state = False
        self._lowlatency_enabled = False
        self._installation_mode = ""
        self._picture_mode = ""
        self._input_mode = ""
        self._laser_mode = ""
        self._eshift = ""
        self._color_mode = ""
        self._input_level = ""
        self._content_type = ""
        self._hdr_processing = ""
        self._lamp_power = ""
        self._hdr_data = ""
        self._theater_optimizer = ""
        self._laser_power = ""
        self._aspect_ratio = ""

        self.jvc_client = jvc_client
        self._model_family = self.jvc_client.model_family

    @property
    def should_poll(self):
        """Poll."""
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
        # Separate views for models to be cleaner

        # make sensors or automations based on these
        if "NZ" in self._model_family:
            return {
                "power_state": self._state,
                "picture_mode": self._picture_mode,
                "laser_power": self._laser_power,
                "content_type": self._content_type,
                "hdr_data": self._hdr_data,
                "hdr_processing": self._hdr_processing,
                "theater_optimizer": "on" in self._theater_optimizer,
                "low_latency": self._lowlatency_enabled,
                "input_mode": self._input_mode,
                "laser_mode": self._laser_mode,
                "input_level": self._input_level,
                "color_mode": self._color_mode,
                "installation_mode": self._installation_mode,
                "aspect_ratio": self._aspect_ratio,
                "eshift": self._eshift,
                "model": self._model_family,
            }

        if "NX" in self._model_family:
            return {
                "power_state": self._state,
                "picture_mode": self._picture_mode,
                "hdr_data": self._hdr_data,
                "low_latency": self._lowlatency_enabled,
                "input_mode": self._input_mode,
                "lamp_power": self._lamp_power,
                "input_level": self._input_level,
                "installation_mode": self._installation_mode,
                "aspect_ratio": self._aspect_ratio,
                "color_mode": self._color_mode,
                "eshift": self._eshift,
                "model": self._model_family,
            }

        # for stuff like np-5
        return {
            "power_state": self._state,
            "picture_mode": self._picture_mode,
            "low_latency": self._lowlatency_enabled,
            "input_mode": self._input_mode,
            "lamp_power": self._lamp_power,
            "input_level": self._input_level,
            "color_mode": self._color_mode,
            "installation_mode": self._installation_mode,
            "aspect_ratio": self._aspect_ratio,
            "model": self._model_family,
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
        # Im not doing it in the lib because HA tends to do whatever it wants wrt locking
        # don't update if a command is running, will clash
        if self._command_running is False:
            self._is_updating = True
            self._state = self.jvc_client.is_on()

            if self._state:
                # if its connected, on, and we are updating, its safe to mark it as ready
                self._is_ready = True
                # Common attributes
                self._lowlatency_enabled = self.jvc_client.is_ll_on()
                self._installation_mode = self.jvc_client.get_install_mode()
                self._aspect_ratio = self.jvc_client.get_aspect_ratio()
                self._input_mode = self.jvc_client.get_input_mode()
                self._color_mode = self.jvc_client.get_color_mode()
                self._input_level = self.jvc_client.get_input_level()
                self._picture_mode = self.jvc_client.get_picture_mode()

                # NZ specifics
                if "NZ" in self._model_family:
                    # Only NZ has the content type command
                    self._content_type = self.jvc_client.get_content_type()
                    self._laser_mode = self.jvc_client.get_laser_mode()
                    self._laser_power = self.jvc_client.get_laser_power()
                    # only check HDR if the content type matches else timeout
                    if any(x in self._content_type for x in ["hdr", "hlg"]):
                        self._hdr_processing = self.jvc_client.get_hdr_processing()
                        self._hdr_data = self.jvc_client.get_hdr_data()
                        try:
                            self._theater_optimizer = (
                                self.jvc_client.get_theater_optimizer_state()
                            )
                        except TimeoutError:
                            self._theater_optimizer = "not set"

                # Get lamp power if not NZ
                if not "NZ" in self._model_family:
                    self._lamp_power = self.jvc_client.get_lamp_power()

                # Eshift for NX and NZ only
                if any(x in self._model_family for x in ["NX", "NZ"]):
                    self._eshift = self.jvc_client.get_eshift_mode()

                # NX and NZ process things diff
                if "NX" in self._model_family:
                    try:
                        self._hdr_data = self.jvc_client.get_hdr_data()
                    except TypeError:
                        pass

            self._is_updating = False

    def send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        retry = 0

        while retry < 10:
            # don't send command until update is done
            if self._is_updating is True:
                time.sleep(1)
                retry += 1
                continue

            # set cmd running flag, run cmd, then break
            self._command_running = True
            self.jvc_client.exec_command(command)
            self._command_running = False
            break
