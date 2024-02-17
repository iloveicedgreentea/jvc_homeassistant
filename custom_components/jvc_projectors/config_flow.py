import voluptuous as vol
import logging
from homeassistant import config_entries, core
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_TIMEOUT, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN  # Import the domain constant

_LOGGER = logging.getLogger(__name__)

class JVCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for JVC Projector."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # TODO: Implement actual validation of user input
            valid = True  # Replace with actual validation logic

            if valid:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

            errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PASSWORD): str,
            vol.Optional(CONF_TIMEOUT, default=3): int,
            vol.Required(CONF_SCAN_INTERVAL): cv.time_period,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_import(self, import_config):
        """Handle the import of a configuration from YAML."""
        unique_id = import_config.get(CONF_HOST)
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=import_config.get(CONF_NAME, "JVC Projector"), data=import_config)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return JVCOptionsFlow(config_entry)

class JVCOptionsFlow(config_entries.OptionsFlow):
    """Handle JVC options."""

    def __init__(self, config_entry):
        """Initialize JVC options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(CONF_TIMEOUT, default=self.config_entry.options.get(CONF_TIMEOUT, 3)): int,
            vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL)): cv.time_period,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
