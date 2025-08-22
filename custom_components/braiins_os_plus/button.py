# custom_components/braiins_os_plus/button.py

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .api import BraiinsAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Braiins OS+ buttons from a config entry."""
    api = hass.data[DOMAIN][config_entry.entry_id]

    buttons = [
        IncrementPowerButton(api, config_entry),
        DecrementPowerButton(api, config_entry),
        PauseMinerButton(api, config_entry),
        ResumeMinerButton(api, config_entry),
    ]
    async_add_entities(buttons)


class BraiinsButton(ButtonEntity):
    """Base class for a Braiins OS+ button."""

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry):
        self._api = api
        self._config_entry = config_entry
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the buttons."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=f"Braiins OS+ Miner ({self._config_entry.data['miner_ip']})",
            manufacturer="Braiins",
            model="Miner with Braiins OS+",
        )


class IncrementPowerButton(BraiinsButton):
    """Button to increment the power target."""

    _attr_name = "Increment Power Target"
    _attr_unique_id = "increment_power_target"
    _attr_icon = "mdi:arrow-up-bold"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.increment_power_target()


class DecrementPowerButton(BraiinsButton):
    """Button to decrement the power target."""

    _attr_name = "Decrement Power Target"
    _attr_unique_id = "decrement_power_target"
    _attr_icon = "mdi:arrow-down-bold"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.decrement_power_target()


class PauseMinerButton(BraiinsButton):
    """Button to pause the miner."""

    _attr_name = "Pause Miner"
    _attr_unique_id = "pause_miner"
    _attr_icon = "mdi:pause"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.pause_mining()


class ResumeMinerButton(BraiinsButton):
    """Button to resume the miner."""

    _attr_name = "Resume Miner"
    _attr_unique_id = "resume_miner"
    _attr_icon = "mdi:play"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.resume_mining()
