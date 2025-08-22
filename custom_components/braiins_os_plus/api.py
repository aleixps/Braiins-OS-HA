# custom_components/braiins_os_plus/api.py

import logging
import asyncio
import aiohttp

_LOGGER = logging.getLogger(__name__)

class BraiinsAPI:
    """A class for handling API calls to the Braiins OS+ miner."""

    def __init__(self, miner_ip: str, token: str, session: aiohttp.ClientSession):
        """Initialize the API object."""
        self._miner_ip = miner_ip
        self._token = token
        self._session = session
        self._base_url = f"http://{self._miner_ip}/api/v1"

        # ### THE FINAL FIX IS HERE ###
        # The API expects the header to be "Authorization: <token>"
        # without the "Bearer " prefix.
        self._headers = {"Authorization": self._token}

    async def _make_put_request(self, endpoint: str) -> bool:
        """Make a PUT request to a given endpoint."""
        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug("Sending PUT request to %s", url)
        try:
            async with asyncio.timeout(10):
                async with self._session.put(url, headers=self._headers) as response:
                    response.raise_for_status()
                    _LOGGER.info("Successfully sent command to %s", url)
                    return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to send command to %s: %s", url, err)
            return False
        except Exception as err:
            _LOGGER.exception("An unexpected error occurred while sending command to %s", url)
            return False

    async def _make_patch_request(self, endpoint: str, data: dict) -> bool:
        """Make a PATCH request to a given endpoint."""
        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug("Sending PATCH request to %s with data: %s", url, data)
        try:
            async with asyncio.timeout(10):
                async with self._session.patch(url, headers=self._headers, json=data) as response:
                    if response.status == 422:
                        response_text = await response.text()
                        _LOGGER.error(
                            "Unprocessable Entity error for %s. Miner Response: %s",
                            url,
                            response_text
                        )
                    response.raise_for_status()
                    _LOGGER.info("Successfully sent command to %s", url)
                    return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to send command to %s: %s", url, err)
            return False
        except Exception as err:
            _LOGGER.exception("An unexpected error occurred while sending command to %s", url)
            return False

    # --- Methods using PATCH ---
    async def increment_power_target(self, value: int = 250) -> bool:
        """Increment the power target by a given value."""
        payload = {"watt": value}
        return await self._make_patch_request("performance/power-target/increment", payload)

    async def decrement_power_target(self, value: int = 250) -> bool:
        """Decrement the power target by a given value."""
        payload = {"watt": value}
        return await self._make_patch_request("performance/power-target/decrement", payload)

    # --- Methods using PUT ---
    async def pause_mining(self) -> bool:
        """Pause the mining operation."""
        return await self._make_put_request("actions/pause")

    async def resume_mining(self) -> bool:
        """Resume the mining operation."""
        return await self._make_put_request("actions/resume")