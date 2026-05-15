# custom_components/braiins_os_plus/button.py
"""Braiins OS+ integration button entities."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BraiinsAPI
from .const import (
    CONF_HASHRATE_STEP,
    CONF_POWER_STEP,
    DEFAULT_HASHRATE_STEP,
    DEFAULT_POWER_STEP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Braiins OS+ button entities from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    api = data["api"]
    coordinator = data["coordinator"]

    buttons = [
        IncrementPowerButton(api, config_entry, coordinator),
        DecrementPowerButton(api, config_entry, coordinator),
        IncrementHashrateButton(api, config_entry, coordinator),
        DecrementHashrateButton(api, config_entry, coordinator),
        PauseMinerButton(api, config_entry, coordinator),
        ResumeMinerButton(api, config_entry, coordinator),
    ]
    async_add_entities(buttons)


class BraiinsButton(CoordinatorEntity, ButtonEntity):
    """Base button entity for a Braiins OS+ miner."""

    def __init__(self, api, config_entry, coordinator) -> None:
        """Initialize the base Braiins OS+ button."""
        super().__init__(coordinator)
        self._api = api
        self._config_entry = config_entry
        # self.coordinator = coordinator
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


class IncrementPowerButton(BraiinsButton):
    """Button entity to increment the power target."""

    _attr_name = "Increment Power Target"
    _attr_icon = "mdi:arrow-up-bold"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry, coordinator) -> None:
        """Initialize the increment power button."""
        super().__init__(api, config_entry, coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_increment_power_target"

    @property
    def available(self) -> bool:
        """Only show power target buttons when in Power Target mode."""
        return (
            super().available
            and self.coordinator.data.get("performance_mode") == "Power Target"
        )

    async def async_press(self) -> None:
        """Handle the button press with dynamic step and Optimistic UI."""
        step = self._config_entry.options.get(CONF_POWER_STEP, DEFAULT_POWER_STEP)
        success = await self._api.increment_power_target(step)

        if success and self.coordinator.data:
            current_watt = self.coordinator.data.get("power_target", 0)
            new_watt = current_watt + step

            new_data = dict(self.coordinator.data)
            new_data["power_target"] = new_watt
            self.coordinator.async_set_updated_data(new_data)


class DecrementPowerButton(BraiinsButton):
    """Button entity to decrement the power target."""

    _attr_name = "Decrement Power Target"
    _attr_icon = "mdi:arrow-down-bold"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry, coordinator) -> None:
        """Initialize the decrement power button."""
        super().__init__(api, config_entry, coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_decrement_power_target"

    @property
    def available(self) -> bool:
        """Only show decrement power target button when in Power Target mode."""
        return (
            super().available
            and self.coordinator.data.get("performance_mode") == "Power Target"
        )

    async def async_press(self) -> None:
        """Handle the button press with dynamic step and Optimistic UI."""
        step = self._config_entry.options.get(CONF_POWER_STEP, DEFAULT_POWER_STEP)
        success = await self._api.decrement_power_target(step)

        if success and self.coordinator.data:
            current_watt = self.coordinator.data.get("power_target", 0)
            new_watt = max(0, current_watt - step)

            new_data = dict(self.coordinator.data)
            new_data["power_target"] = new_watt
            self.coordinator.async_set_updated_data(new_data)


class IncrementHashrateButton(BraiinsButton):
    """Button entity to increment the hashrate target."""

    _attr_name = "Increment Hashrate Target"
    _attr_icon = "mdi:trending-up"

    def __init__(self, api, config_entry, coordinator) -> None:
        """Initialize the increment hashrate button."""
        super().__init__(api, config_entry, coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_increment_hashrate_target"

    @property
    def available(self) -> bool:
        """Only show increment hashrate target button when in Hashrate Target mode."""
        return (
            super().available
            and self.coordinator.data.get("performance_mode") == "Hashrate Target"
        )

    async def async_press(self) -> None:
        """Handle the button press to increment the hashrate target."""
        step = int(
            self._config_entry.options.get(CONF_HASHRATE_STEP, DEFAULT_HASHRATE_STEP)
        )
        success = await self._api.increment_hashrate_target(step)
        if success and self.coordinator.data:
            current = self.coordinator.data.get("hashrate_target", 0)
            new_data = dict(self.coordinator.data)
            new_data["hashrate_target"] = int(current + step)
            self.coordinator.async_set_updated_data(new_data)


class DecrementHashrateButton(BraiinsButton):
    """Button entity to decrement the hashrate target."""

    _attr_name = "Decrement Hashrate Target"
    _attr_icon = "mdi:trending-down"

    def __init__(self, api, config_entry, coordinator) -> None:
        """Initialize the decrement hashrate button."""
        super().__init__(api, config_entry, coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_decrement_hashrate_target"

    @property
    def available(self) -> bool:
        """Only show decrement hashrate target button when in Hashrate Target mode."""
        return (
            super().available
            and self.coordinator.data.get("performance_mode") == "Hashrate Target"
        )

    async def async_press(self) -> None:
        """Handle the button press to decrement the hashrate target."""
        step = int(
            self._config_entry.options.get(CONF_HASHRATE_STEP, DEFAULT_HASHRATE_STEP)
        )
        success = await self._api.decrement_hashrate_target(step)
        if success and self.coordinator.data:
            current = self.coordinator.data.get("hashrate_target", 0)
            new_data = dict(self.coordinator.data)
            new_data["hashrate_target"] = int(max(0, current - step))
            self.coordinator.async_set_updated_data(new_data)


class PauseMinerButton(BraiinsButton):
    """Button entity to pause miner operation."""

    _attr_name = "Pause Miner"
    _attr_icon = "mdi:pause"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry, coordinator) -> None:
        """Initialize the pause miner button."""
        super().__init__(api, config_entry, coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_pause_miner"

    async def async_press(self) -> None:
        """Handle the button press to pause mining."""
        await self._api.pause_mining()


class ResumeMinerButton(BraiinsButton):
    """Button entity to resume miner operation."""

    _attr_name = "Resume Miner"
    _attr_icon = "mdi:play"

    def __init__(self, api: BraiinsAPI, config_entry: ConfigEntry, coordinator) -> None:
        """Initialize the resume miner button."""
        super().__init__(api, config_entry, coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_resume_miner"

    async def async_press(self) -> None:
        """Handle the button press to resume mining."""
        await self._api.resume_mining()
