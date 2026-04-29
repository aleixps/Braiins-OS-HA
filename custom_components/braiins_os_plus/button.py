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
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]

    buttons = [
        IncrementPowerButton(api, config_entry),
        DecrementPowerButton(api, config_entry),
        PauseMinerButton(api, config_entry),
        ResumeMinerButton(api, config_entry),
    ]
    async_add_entities(buttons)


class BraiinsButton(ButtonEntity):

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry):
        self._api = api
        self._config_entry = config_entry
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=f"Braiins OS+ Miner ({self._config_entry.data['miner_ip']})",
            manufacturer="Braiins",
            model="Miner with Braiins OS+",
        )

class IncrementPowerButton(BraiinsButton):
    _attr_name = "Increment Power Target"
    _attr_icon = "mdi:arrow-up-bold"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry):
        super().__init__(api, config_entry)
        # Unique ID now includes the entry_id to allow multiple miners
        self._attr_unique_id = f"{config_entry.entry_id}_increment_power_target"

    async def async_press(self) -> None:
        await self._api.increment_power_target()

class DecrementPowerButton(BraiinsButton):
    _attr_name = "Decrement Power Target"
    _attr_icon = "mdi:arrow-down-bold"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry):
        super().__init__(api, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_decrement_power_target"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.decrement_power_target()

class PauseMinerButton(BraiinsButton):
    _attr_name = "Pause Miner"
    _attr_icon = "mdi:pause"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry):
        super().__init__(api, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_pause_miner"

    async def async_press(self) -> None:
        await self._api.pause_mining()

class ResumeMinerButton(BraiinsButton):
    _attr_name = "Resume Miner"
    _attr_icon = "mdi:play"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry):
        super().__init__(api, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_resume_miner"

    async def async_press(self) -> None:
        await self._api.resume_mining()