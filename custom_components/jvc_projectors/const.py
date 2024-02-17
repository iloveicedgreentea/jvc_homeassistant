"""Constants for the JVC Projector integration."""
import voluptuous as vol
from homeassistant.components.remote import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers import config_validation as cv
DOMAIN = "jvc_projectors"

# Services
INFO_COMMAND = "info"
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_TIMEOUT): cv.positive_int,
    }
)