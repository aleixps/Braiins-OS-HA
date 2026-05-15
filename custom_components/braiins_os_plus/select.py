# custom_components/braiins_os_plus/select.py
"""Braiins OS+ integration select entities."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up select entities for Braiins OS+ from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [BraiinsPerformanceModeSelect(data["coordinator"], data["api"], entry)]
    )


class BraiinsPerformanceModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity to choose between Power Target and Hashrate Target modes."""

    _attr_has_entity_name = True
    _attr_name = "Performance Mode"
    _attr_options = ["Power Target", "Hashrate Target"]
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator, api, entry) -> None:
        """Initialize the performance mode select entity."""
        super().__init__(coordinator)
        self.api = api
        self._attr_unique_id = f"{entry.entry_id}_performance_mode"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}

    @property
    def current_option(self) -> str | None:
        """Return the currently active performance mode."""
        return self.coordinator.data.get("performance_mode")

    async def async_select_option(self, option: str) -> None:
        """Handle option selection to switch performance modes on the miner."""
        data = self.coordinator.data
        if not data:
            return

        target_value = None

        if option == "Power Target":
            # 1. Try last known value
            target_value = data.get("power_target") or self.api.get_cached_value(
                "power_target"
            )
            # 2. Fallback to constraints default
            if target_value is None:
                try:
                    target_value = data["constraints"]["tuner_constraints"][
                        "power_target"
                    ]["default"]["watt"]
                except KeyError, TypeError:
                    target_value = 2700  # Last resort fallback

        else:  # Hashrate Target
            # 1. Try last known value
            target_value = data.get("hashrate_target") or self.api.get_cached_value(
                "hashrate_target"
            )

            # 2. Fallback to constraints default
            if target_value is None:
                try:
                    target_value = data["constraints"]["tuner_constraints"][
                        "hashrate_target"
                    ]["default"]["terahash_per_second"]
                except KeyError, TypeError:
                    target_value = 100  # Last resort fallback

        if await self.api.set_performance_mode(option, target_value):
            new_data = dict(self.coordinator.data)
            new_data["performance_mode"] = option

            if option == "Power Target":
                new_data["power_target"] = int(target_value)
                self.api.update_last_data("power_target", int(target_value))
            else:
                new_data["hashrate_target"] = int(target_value)
                self.api.update_last_data("hashrate_target", int(target_value))

            # Keep both the state and the cache in sync
            self.api.update_last_data("performance_mode", option)
            self.coordinator.async_set_updated_data(new_data)
