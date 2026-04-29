# custom_components/braiins_os_plus/number.py

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfPower

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Number platform for Braiins OS."""
    # Unpack the dictionary created in __init__.py
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = domain_data["coordinator"]
    api = domain_data["api"]
    
    async_add_entities([BraiinsPowerTargetNumber(coordinator, api, entry)])

class BraiinsPowerTargetNumber(CoordinatorEntity, NumberEntity):
    """Number entity to set the Braiins OS power target."""

    _attr_has_entity_name = True
    _attr_name = "Power Target"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:lightning-bolt"

    _attr_native_min_value = 780  # Minimum Watts 
    _attr_native_max_value = 6400  # Maximum Watts
    _attr_native_step = 10         # Allows adjustments in increments of 10W

    def __init__(self, coordinator, api, entry):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.api = api
        
        # Link this entity to the existing Braiins OS device in HA
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}
        }
        self._attr_unique_id = f"{entry.entry_id}_power_target"

    @property
    def native_value(self):
        """Return the current power target fetched from the miner."""
        if self.coordinator.data:
            return self.coordinator.data.get("power_target")
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Send the new power target to the miner."""
        watt_value = int(value)
        
        # Call the set_power_target method we added to api.py
        success = await self.api.set_power_target(watt_value)
        
        if success:
            # Force Home Assistant to instantly fetch updated data so the UI refreshes
            await self.coordinator.async_request_refresh()