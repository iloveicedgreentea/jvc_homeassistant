"""Implement JVC component."""

from collections.abc import Iterable
import logging
import threading
from jvc_projector.jvc_projector import JVCProjector
import voluptuous as vol

from homeassistant.components.remote import PLATFORM_SCHEMA, RemoteEntity
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
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
    s = jvc_client.open_connection()
    if not s:
        _LOGGER.error("Failed to connect to the projector")
        return
    add_entities(
        [
            JVCRemote(name, host, jvc_client),
        ]
    )
    _LOGGER.debug("JVC platform loaded")


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
        self.jvc_client = jvc_client
        self.lock = threading.Lock()

        # attributes
        self._state = False
        self._model_family = self.jvc_client.model_family
        self._attributes = {
            "power_state": self._state,
            "model": self._model_family,
        }

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        _LOGGER.info("JVCRemote entity added to hass: %s", self._name)

    async def async_will_remove_from_hass(self):
        """Call when entity will be removed from hass."""
        _LOGGER.info("JVCRemote entity will be removed from hass: %s", self._name)
        self.jvc_client.close_connection()

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

        return self._attributes

    @property
    def is_on(self):
        """Return the last known state of the projector."""

        return self._state

    def turn_on(self, **kwargs):
        """Send the power on command."""

        with self.lock:
            try:
                self.jvc_client.power_on()
                self._state = True
                self._attributes["power_state"] = self._state
            except Exception as e:
                _LOGGER.error("Failed to turn on the projector: %s", e)

    def turn_off(self, **kwargs):
        """Send the power off command."""

        with self.lock:
            try:
                self.jvc_client.power_off()
                self._state = False
                self._attributes["power_state"] = self._state
            except Exception as e:
                _LOGGER.error("Failed to turn off the projector: %s", e)

    def update(self):
        """Retrieve latest state."""
        with self.lock:
            try:
                self._state = self.jvc_client.is_on()
                self._attributes["power_state"] = self._state

                if self._state:
                    self._update_common_attributes()
                    self._update_model_specific_attributes()
                    self._update_hdr_attributes()

            except Exception as e:
                _LOGGER.error("Failed to update the projector state: %s", e)

    def _update_common_attributes(self):
        """Update common attributes."""
        try:
            self._attributes.update(
                {
                    "low_latency": self.jvc_client.is_ll_on(),
                    "picture_mode": self.jvc_client.get_picture_mode(),
                    "input_mode": self.jvc_client.get_input_mode(),
                }
            )
        except Exception as e:
            _LOGGER.error("Failed to update common attributes: %s", e)

    def _update_model_specific_attributes(self):
        """Update model-specific attributes."""
        try:
            if "Unsupported" not in self._model_family:
                self._attributes.update(
                    {
                        "installation_mode": self.jvc_client.get_install_mode(),
                        "aspect_ratio": self.jvc_client.get_aspect_ratio(),
                        "color_mode": self.jvc_client.get_color_mode(),
                        "input_level": self.jvc_client.get_input_level(),
                        "mask_mode": self.jvc_client.get_mask_mode(),
                        "signal_status": self.jvc_client.get_source_status(),
                    }
                )
                if self._attributes.get("signal_status") == "signal":
                    self._attributes.update(
                        {
                            "content_type": self.jvc_client.get_content_type(),
                            "content_type_trans": self.jvc_client.get_content_type_trans(),
                        }
                    )
            if "NX9" in self._model_family or "NZ" in self._model_family:
                self._attributes["eshift"] = self.jvc_client.get_eshift_mode()
            if "NZ" in self._model_family:
                self._attributes.update(
                    {
                        "laser_mode": self.jvc_client.get_laser_mode(),
                        "laser_power": self.jvc_client.get_laser_power(),
                    }
                )
            else:
                self._attributes["lamp_power"] = self.jvc_client.get_lamp_power()
        except TimeoutError as e:
            _LOGGER.error("Timeout while updating model-specific attributes: %s", e)
        except Exception as e:
            _LOGGER.error("Failed to update model-specific attributes: %s", e)

    def _update_hdr_attributes(self):
        """Update HDR-related attributes."""
        try:
            if any(x in self._attributes.get("content_type_trans") for x in ["hdr", "hlg"]):
                if "NZ" in self._model_family:
                    self._attributes["theater_optimizer"] = (
                        self.jvc_client.get_theater_optimizer_state()
                    )
                self._attributes.update(
                    {
                        "hdr_processing": self.jvc_client.get_hdr_processing(),
                        "hdr_level": self.jvc_client.get_hdr_level(),
                        "hdr_data": self.jvc_client.get_hdr_data(),
                    }
                )
        except TimeoutError as e:
            _LOGGER.error("Timeout while updating HDR attributes: %s", e)
        except Exception as e:
            _LOGGER.error("Failed to update HDR attributes: %s", e)

    def send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        with self.lock:
            try:
                self.jvc_client.exec_command(command)
            except Exception as e:
                _LOGGER.error("Failed to send command %s: %s", command, e)
