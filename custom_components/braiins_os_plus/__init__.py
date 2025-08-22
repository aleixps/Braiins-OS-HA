# custom_components/braiins_os_plus/__init__.py

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .api import BraiinsAPI

PLATFORMS = ["button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Braiins OS+ from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    session = async_get_clientsession(hass)

    # ### THE FIX IS HERE ###
    # The API class now needs hass and the entry to manage token renewal
    api = BraiinsAPI(hass, entry, session)

    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok