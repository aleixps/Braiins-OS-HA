# custom_components/braiins_os_plus/api.py

import logging
import asyncio
import aiohttp
import time
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)

class BraiinsAPI:
    """A class for handling API calls and token renewal."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, session: aiohttp.ClientSession):
        """Initialize the API object."""
        self._hass = hass
        self._entry = entry
        self._session = session
        self._base_url = f"http://{self._entry.data['miner_ip']}/api/v1"
        self._token = self._entry.data["token"]
        self._headers = {"Authorization": self._token}
        self._lock = asyncio.Lock()

    async def async_relogin(self) -> bool:
        """Perform a login to get a new token. Raises UpdateFailed on connection error."""
        # ### THE FIX IS HERE: The premature log message has been removed. ###
        url = f"{self._base_url}/auth/login"
        payload = {
            "username": self._entry.data["username"],
            "password": self._entry.data["password"],
        }
        try:
            async with asyncio.timeout(10):
                async with self._session.post(url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    new_token = data["token"]
                    new_timeout = data.get("timeout_s", 3600)
                    new_expires_at = time.time() + new_timeout - 60

                    # We now only log a message after a successful re-authentication.
                    _LOGGER.info("Successfully re-authenticated with Braiins OS+ and got a new token.")
                    
                    self._token = new_token
                    self._headers = {"Authorization": self._token}

                    new_data = {**self._entry.data, "token": new_token, "expires_at": new_expires_at}
                    self._hass.config_entries.async_update_entry(self._entry, data=new_data)
                    
                    return True
        
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            # We raise UpdateFailed, and the coordinator handles the error logging.
            raise UpdateFailed(f"Failed to re-authenticate with Braiins OS+: {err}") from err
        except Exception as err:
            # This will catch other unexpected errors during relogin
            _LOGGER.error("An unexpected error occurred during re-authentication: %s", err)
            return False

    async def _is_token_valid_and_renew(self) -> bool:
        """Helper to check token validity and renew if needed."""
        async with self._lock:
            if time.time() > self._entry.data["expires_at"]:
                return await self.async_relogin()
        return True

    async def _make_get_request(self, endpoint: str) -> dict[str, Any]:
        """Make a GET request and return the JSON response. Raises UpdateFailed on connection error."""
        if not await self._is_token_valid_and_renew():
            raise UpdateFailed("Token is invalid and could not be renewed.")
        
        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug("Sending GET request to %s", url)
        try:
            async with asyncio.timeout(10):
                async with self._session.get(url, headers=self._headers) as response:
                    response.raise_for_status()
                    return await response.json()
        
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Failed to get data from {url}: {err}") from err
        except Exception as err:
            _LOGGER.exception("An unexpected error occurred while getting data from %s", url)
            raise UpdateFailed(f"An unexpected error occurred while getting data: {err}") from err

    async def async_update_data(self) -> dict[str, Any]:
        """Fetch data from all endpoints and combine them."""
        results = await asyncio.gather(
            self._make_get_request("miner/hw/hashboards"),
            self._make_get_request("miner/stats")
        )
        
        hashboard_data, stats_data = results
        
        combined_data = {}
        if hashboard_data:
            combined_data.update(hashboard_data)
        if stats_data:
            combined_data.update(stats_data)

        if not combined_data:
            raise UpdateFailed("Failed to fetch any data from the miner.")

        return combined_data

    async def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> bool:
        """Make a PUT or PATCH request for button presses."""
        if not await self._is_token_valid_and_renew():
            return False
        
        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug("Sending %s request to %s with data: %s", method.upper(), url, data)
        try:
            async with asyncio.timeout(10):
                async with self._session.request(method, url, headers=self._headers, json=data) as response:
                    if response.status == 422:
                        response_text = await response.text()
                        _LOGGER.error("Unprocessable Entity for %s. Miner Response: %s", url, response_text)
                    response.raise_for_status()
                    _LOGGER.info("Successfully sent command to %s", url)
                    return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to send command to %s: %s", url, err)
            return False
        except Exception as err:
            _LOGGER.exception("An unexpected error occurred while sending command to %s", url)
            return False

    async def increment_power_target(self, value: int = 250) -> bool:
        return await self._make_request("patch", "performance/power-target/increment", {"watt": value})

    async def decrement_power_target(self, value: int = 250) -> bool:
        return await self._make_request("patch", "performance/power-target/decrement", {"watt": value})

    async def pause_mining(self) -> bool:
        return await self._make_request("put", "actions/pause")

    async def resume_mining(self) -> bool:
        return await self._make_request("put", "actions/resume")