# custom_components/braiins_os_plus/switch.py
"""Braiins OS+ integration switch entities."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BraiinsAPI
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Braiins OS+ switches from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    api = data["api"]
    coordinator = data["coordinator"]

    async_add_entities([LocateLedSwitch(api, config_entry, coordinator)])


class BraiinsSwitch(CoordinatorEntity, SwitchEntity):
    """Base switch entity for a Braiins OS+ miner."""

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry, coordinator) -> None:
        """Initialize the base Braiins OS+ switch."""
        super().__init__(coordinator)
        self._api = api
        self._config_entry = config_entry
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this miner."""
        data = self.coordinator.data.get("details", {})
        ident = data.get("miner_identity", {})

        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=data.get("hostname")
            or f"Braiins OS+ Miner ({self._config_entry.data['miner_ip']})",
            manufacturer="Braiins",
            model=ident.get("miner_model") or "Miner with Braiins OS+",
            sw_version=data.get("bos_version", {}).get("current"),
        )


class LocateLedSwitch(BraiinsSwitch):
    """Switch entity for the miner locate LED blinking state."""

    _attr_name = "Device Locate LED Blinking"
    _attr_icon = "mdi:led-on"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry, coordinator) -> None:
        """Initialize the locate LED switch."""
        super().__init__(api, config_entry, coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_locate_led_blinking"

    @property
    def is_on(self) -> bool | None:
        """Return whether locate LED blinking is enabled."""
        return self.coordinator.data.get("locate_status")

    async def async_turn_on(self, **kwargs) -> None:
        """Enable locate LED blinking."""
        if await self._api.set_locate_status(True):
            new_data = dict(self.coordinator.data)
            new_data["locate_status"] = True
            self.coordinator.async_set_updated_data(new_data)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable locate LED blinking."""
        if await self._api.set_locate_status(False):
            new_data = dict(self.coordinator.data)
            new_data["locate_status"] = False
            self.coordinator.async_set_updated_data(new_data)
