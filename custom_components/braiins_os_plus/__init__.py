# custom_components/braiins_os_plus/__init__.py  # noqa: D104

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BraiinsAPI
from .const import DOMAIN

# Define the platform that your integration will support
PLATFORMS = ["button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Braiins OS+ from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create an API instance for the entry
    session = async_get_clientsession(hass)
    token = entry.data["token"]
    miner_ip = entry.data["miner_ip"]
    api = BraiinsAPI(miner_ip, token, session)

    # Store the API instance in hass.data for the platform to use
    hass.data[DOMAIN][entry.entry_id] = api

    # Forward the setup to the button platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload the platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove the API instance from hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
