# custom_components/braiins_os_plus/api.py

import logging
import asyncio
import aiohttp
import time
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

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
        self._lock = asyncio.Lock()  # To prevent multiple concurrent relogin attempts

    async def async_relogin(self) -> bool:
        """Perform a login to get a new token."""
        _LOGGER.info("Braiins OS+ token expired or is about to expire. Re-authenticating.")
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

                    _LOGGER.info("Successfully re-authenticated and got a new token.")
                    
                    # Update internal state
                    self._token = new_token
                    self._headers = {"Authorization": self._token}

                    # Update the config entry in Home Assistant to persist the new token
                    new_data = {**self._entry.data, "token": new_token, "expires_at": new_expires_at}
                    self._hass.config_entries.async_update_entry(self._entry, data=new_data)
                    
                    return True

        except Exception as err:
            _LOGGER.error("Failed to re-authenticate with Braiins OS+: %s", err)
            return False

    async def async_ensure_token_valid(self) -> None:
        """Check if the token is valid and renew it if necessary."""
        async with self._lock:
            if time.time() > self._entry.data["expires_at"]:
                await self.async_relogin()

    async def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> bool:
        """Make a generic request, ensuring the token is valid first."""
        await self.async_ensure_token_valid()
        
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
        except (aiohttp.ClientError, asyncio.TimeoutError, asyncio.CancelledError) as err:
            _LOGGER.error("Failed to send command to %s: %s", url, err)
            return False
        except Exception as err:
            _LOGGER.exception("An unexpected error occurred while sending command to %s", url)
            return False

    # --- Public API methods ---
    async def increment_power_target(self, value: int = 250) -> bool:
        """Increment the power target by a given value."""
        return await self._make_request("patch", "performance/power-target/increment", {"watt": value})

    async def decrement_power_target(self, value: int = 250) -> bool:
        """Decrement the power target by a given value."""
        return await self._make_request("patch", "performance/power-target/decrement", {"watt": value})

    async def pause_mining(self) -> bool:
        """Pause the mining operation."""
        return await self._make_request("put", "actions/pause")

    async def resume_mining(self) -> bool:
        """Resume the mining operation."""
        return await self._make_request("put", "actions/resume")