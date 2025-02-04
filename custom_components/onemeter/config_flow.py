import logging

import voluptuous as vol
import traceback

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import OnemeterApi
from .const import (
    CONF_APIKEY,
    CONF_DEVICE,
    CONF_SYNC_INTERVAL,
    DEFAULT_SYNC_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


class OnemeterFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        self._errors = {}

    async def async_step_apikey(self, user_input=None):
        self._errors = {}

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_input(
                user_input[CONF_APIKEY], user_input[CONF_DEVICE]
            )
            if valid:
                return self.async_create_entry(
                    title=user_input[CONF_APIKEY], data=user_input
                )
            else:
                self._errors["base"] = "auth"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_APIKEY): str, vol.Required(CONF_DEVICE): str}
            ),
            errors=self._errors,
        )

    async def _test_input(self, apikey, device):
        try:
            api = OnemeterApi(apikey, device)
            await self.hass.async_add_executor_job(api.get_device)
            return True
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error(
                f"{DOMAIN} Exception in input test : %s - traceback: %s",
                ex,
                traceback.format_exc(),
            )
        return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OnemeterOptionsFlowHandler(config_entry)


class OnemeterOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        return await self.async_step_apikey()

    async def async_step_apikey(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SYNC_INTERVAL,
                        default=self.options.get(
                            CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int))
                }
            ),
        )

    async def _update_options(self):
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_SYNC_INTERVAL), data=self.options
        )
