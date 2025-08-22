# custom_components/braiins_os_plus/config_flow.py

import voluptuous as vol
import logging
import asyncio
import aiohttp

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class BraiinsOSPlusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Braiins OS+ config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            miner_ip = user_input["miner_ip"]
            username = user_input["username"]
            # Get the password, which could be None if the field is empty
            password = user_input.get("password")

            if not username:
                errors["base"] = "missing_info"
            else:
                try:
                    url = f"http://{miner_ip}/api/v1/auth/login"

                    # ### THE FIX IS HERE ###
                    # Always include the password key. If the password is None or empty,
                    # send an empty string.
                    payload = {
                        "username": username,
                        "password": password or ""
                    }
                    _LOGGER.debug("Sending login payload: %s", payload)

                    session = async_get_clientsession(self.hass)

                    async with asyncio.timeout(10):
                        async with session.post(url, json=payload) as response:
                            if response.status == 200:
                                data = await response.json()
                                token = data.get("token")

                                await self.async_set_unique_id(miner_ip)
                                self._abort_if_unique_id_configured()

                                return self.async_create_entry(
                                    title=miner_ip,
                                    data={
                                        "miner_ip": miner_ip,
                                        "username": username,
                                        "token": token,
                                    },
                                )
                            elif response.status == 401:
                                errors["base"] = "invalid_auth"
                            else:
                                response_text = await response.text()
                                _LOGGER.warning(
                                    "Login failed with status code %s: %s",
                                    response.status,
                                    response_text,
                                )
                                errors["base"] = "cannot_connect"

                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    _LOGGER.error("Failed to connect to miner at %s: %s", miner_ip, err)
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("An unexpected error occurred")
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("miner_ip"): str,
                    vol.Required("username"): str,
                    vol.Optional("password"): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_create_entry(title="", data={})