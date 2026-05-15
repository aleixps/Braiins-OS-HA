# custom_components/braiins_os_plus/api.py
"""Braiins OS+ integration API client for token management and miner control."""

import asyncio
import logging
import time
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)


class BraiinsAPI:
    """A class for handling API calls and token renewal."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, session: aiohttp.ClientSession
    ) -> None:
        """Initialize the API object."""
        self._hass = hass
        self._entry = entry
        self._session = session
        self._base_url = f"http://{self._entry.data['miner_ip']}/api/v1"
        self._token = self._entry.data["token"]
        self._headers = {"Authorization": self._token}
        self._lock = asyncio.Lock()
        self._last_data = {}

    def get_cached_value(self, key: str) -> Any:
        """Public method to get a value from the internal cache."""
        return self._last_data.get(key)

    def update_last_data(self, key: str, value: Any) -> None:
        """Public method to update the internal cache for optimistic UI updates."""
        if self._last_data is not None:
            self._last_data[key] = value

    async def async_relogin(self) -> bool:
        """Perform a login to get a new token."""
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

                    _LOGGER.info(
                        "Successfully re-authenticated with Braiins OS+ and got a new token"
                    )

                    self._token = new_token
                    self._headers = {"Authorization": self._token}

                    new_data = {
                        **self._entry.data,
                        "token": new_token,
                        "expires_at": new_expires_at,
                    }
                    self._hass.config_entries.async_update_entry(
                        self._entry, data=new_data
                    )

                    return True

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.warning("Failed to re-authenticate with Braiins OS+: %s", err)
            return False
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "An unexpected error occurred during re-authentication: %s", err
            )
            return False

    async def _is_token_valid_and_renew(self) -> bool:
        """Helper to check token validity and renew if needed."""
        async with self._lock:
            if time.time() > self._entry.data["expires_at"]:
                _LOGGER.info("Token expired based on time, attempting re-login")
                return await self.async_relogin()
        return True

    async def _make_get_request(self, endpoint: str) -> dict[str, Any] | None:
        """Make a GET request and return the JSON response, or None on failure."""
        if not await self._is_token_valid_and_renew():
            return None

        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug("Sending GET request to %s", url)
        try:
            async with asyncio.timeout(10):
                async with self._session.get(url, headers=self._headers) as response:
                    if response.status == 401:
                        _LOGGER.info(
                            "Token rejected by miner (401), attempting re-login"
                        )
                        async with self._lock:
                            if await self.async_relogin():
                                _LOGGER.info(
                                    "Re-login successful, retrying request for %s", url
                                )
                                async with self._session.get(
                                    url, headers=self._headers
                                ) as retry_response:
                                    retry_response.raise_for_status()
                                    return await retry_response.json()

                            _LOGGER.warning(
                                "Re-login failed after 401, aborting request for %s",
                                url,
                            )
                            return None

                    if response.status == 500:
                        _LOGGER.debug(
                            "Miner returned 500 at %s (likely reconfiguring)", endpoint
                        )
                        return None

                    response.raise_for_status()
                    return await response.json()

        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.warning("Failed to get data from %s: %s", url, err)
            return None
        except Exception as err:  # noqa: F841
            _LOGGER.exception(
                "An unexpected error occurred while getting data from %s", url
            )
            return None

    async def async_update_data(self) -> dict[str, Any]:
        """Fetch data from all endpoints and combine them. Raise UpdateFailed only if all fail."""
        results = await asyncio.gather(
            self._make_get_request("miner/details"),
            self._make_get_request("configuration/constraints"),
            self._make_get_request("miner/hw/hashboards"),
            self._make_get_request("miner/stats"),
            self._make_get_request("performance/mode"),
            self._make_get_request("cooling/state"),
        )

        details, constraints, hashboards_raw, stats, mode, cooling = results

        # If all heavy endpoints return 500, the miner is reconfiguring.
        # Return the last successful data to prevent the UI from reverting.
        if mode is None and stats is None and hashboards_raw is None:
            if self._last_data:
                _LOGGER.info(
                    "Miner is reconfiguring; using cached data to prevent UI revert"
                )
                return self._last_data
            raise UpdateFailed("Miner is busy and no cached data is available.")

        if not any([details, constraints, hashboards_raw, stats, mode, cooling]):
            raise UpdateFailed("Failed to fetch any data from the miner.")

        combined_data = {
            "details": details or self._last_data.get("details", {}),
            "constraints": constraints or self._last_data.get("constraints", {}),
            "cooling": cooling or self._last_data.get("cooling", {}),
            "hashboards": (hashboards_raw.get("hashboards") if hashboards_raw else None)
            or self._last_data.get("hashboards", []),
            "stats": stats or self._last_data.get("stats", {}),
            "performance_mode": self._last_data.get("performance_mode"),
            "power_target": self._last_data.get("power_target"),  # From Cache
            "hashrate_target": self._last_data.get("hashrate_target"),  # From Cache
        }

        if mode:
            try:
                tuner_target = mode.get("tunermode", {}).get("target", {})

                # Detect the active mode bucket
                if "powertarget" in tuner_target:
                    combined_data["performance_mode"] = "Power Target"
                    watt = (
                        tuner_target.get("powertarget", {})
                        .get("power_target", {})
                        .get("watt")
                    )
                    if watt is not None:
                        combined_data["power_target"] = int(
                            watt
                        )  # Overwrite Cache with Fresh

                elif "hashratetarget" in tuner_target:
                    combined_data["performance_mode"] = "Hashrate Target"
                    th = (
                        tuner_target.get("hashratetarget", {})
                        .get("hashrate_target", {})
                        .get("terahash_per_second")
                    )
                    if th is not None:
                        combined_data["hashrate_target"] = int(
                            th
                        )  # Overwrite Cache with Fresh

                # Extract Power Target
                watt = (
                    tuner_target.get("powertarget", {})
                    .get("power_target", {})
                    .get("watt")
                )
                if watt is not None:
                    combined_data["power_target"] = watt

                # Extract Hashrate Target
                th = (
                    tuner_target.get("hashratetarget", {})
                    .get("hashrate_target", {})
                    .get("terahash_per_second")
                )
                if th is not None:
                    combined_data["hashrate_target"] = th
            except KeyError, AttributeError:
                pass

        self._last_data = combined_data
        return combined_data

    async def _make_request(
        self, method: str, endpoint: str, data: dict | None = None
    ) -> bool:
        """Make a PUT or PATCH request for button presses."""
        if not await self._is_token_valid_and_renew():
            return False

        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug(
            "Sending %s request to %s with data: %s", method.upper(), url, data
        )
        try:
            async with asyncio.timeout(10):
                async with self._session.request(
                    method, url, headers=self._headers, json=data
                ) as response:
                    if response.status == 401:
                        _LOGGER.info(
                            "Token rejected by miner (401) for command, attempting re-login"
                        )
                        async with self._lock:
                            if await self.async_relogin():
                                _LOGGER.info(
                                    "Re-login successful, retrying command for %s", url
                                )
                                async with self._session.request(
                                    method, url, headers=self._headers, json=data
                                ) as retry_response:
                                    if retry_response.status == 422:
                                        response_text = await retry_response.text()
                                        _LOGGER.error(
                                            "Unprocessable Entity on retry for %s. Miner Response: %s",
                                            url,
                                            response_text,
                                        )
                                    retry_response.raise_for_status()
                                    _LOGGER.info(
                                        "Successfully sent command to %s on retry", url
                                    )
                                    return True

                            _LOGGER.error(
                                "Re-login failed after 401, aborting command for %s",
                                url,
                            )
                            return False

                    if response.status == 422:
                        response_text = await response.text()
                        _LOGGER.error(
                            "Unprocessable Entity for %s. Miner Response: %s",
                            url,
                            response_text,
                        )
                    response.raise_for_status()
                    _LOGGER.info("Successfully sent command to %s", url)
                    return True
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Failed to send command to %s: %s", url, err)
            return False
        except Exception as err:  # noqa: F841
            _LOGGER.exception(
                "An unexpected error occurred while sending command to %s", url
            )
            return False

    async def set_hashrate_target(self, th: int) -> bool:
        """Set the miner hashrate target."""
        return await self._make_request(
            "put", "performance/hashrate-target", {"terahash_per_second": th}
        )

    async def increment_hashrate_target(self, value: int) -> bool:
        """Increase the miner hashrate target."""
        return await self._make_request(
            "patch",
            "performance/hashrate-target/increment",
            {"terahash_per_second": value},
        )

    async def decrement_hashrate_target(self, value: int) -> bool:
        """Decrease the miner hashrate target."""
        return await self._make_request(
            "patch",
            "performance/hashrate-target/decrement",
            {"terahash_per_second": value},
        )

    async def increment_power_target(self, value: int) -> bool:
        """Increase the miner power target by the given watt value."""
        return await self._make_request(
            "patch", "performance/power-target/increment", {"watt": value}
        )

    async def decrement_power_target(self, value: int) -> bool:
        """Decrease the miner power target by the given watt value."""
        return await self._make_request(
            "patch", "performance/power-target/decrement", {"watt": value}
        )

    async def set_power_target(self, watt: int) -> bool:
        """Set the miner power target to the specified watt value."""
        return await self._make_request(
            "put", "performance/power-target", {"watt": watt}
        )

    async def pause_mining(self) -> bool:
        """Pause mining on the miner."""
        return await self._make_request("put", "actions/pause")

    async def resume_mining(self) -> bool:
        """Resume mining on the miner."""
        return await self._make_request("put", "actions/resume")

    async def set_performance_mode(self, mode: str, value: float) -> bool:
        """Switch mode and send a specific target value."""
        if mode == "Power Target":
            payload = {
                "tunermode": {
                    "target": {"powertarget": {"power_target": {"watt": int(value)}}}
                }
            }
        else:
            payload = {
                "tunermode": {
                    "target": {
                        "hashratetarget": {
                            "hashrate_target": {"terahash_per_second": float(value)}
                        }
                    }
                }
            }

        return await self._make_request("put", "performance/mode", payload)
