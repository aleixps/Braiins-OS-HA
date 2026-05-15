# custom_components/braiins_os_plus/number.py
"""Braiins OS+ integration number entities."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HASHRATE_STEP,
    CONF_POWER_STEP,
    DEFAULT_HASHRATE_STEP,
    DEFAULT_POWER_STEP,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Number platform for Braiins OS."""
    # Unpack the dictionary created in __init__.py
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = domain_data["coordinator"]
    api = domain_data["api"]

    async_add_entities(
        [
            BraiinsPowerTargetNumber(coordinator, api, entry),
            BraiinsPowerStepNumber(coordinator, entry),
            BraiinsHashrateTargetNumber(coordinator, api, entry),
            BraiinsHashrateStepNumber(coordinator, entry),
        ]
    )


class BraiinsHashrateTargetNumber(CoordinatorEntity, NumberEntity):
    """Number entity to set the Braiins OS hashrate target."""

    _attr_has_entity_name = True
    _attr_name = "Hashrate Target"
    _attr_native_unit_of_measurement = "TH/s"
    _attr_icon = "mdi:speedometer"
    _attr_native_step = 1

    def __init__(self, coordinator, api, entry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_hashrate_target"
        # Use shared device info logic
        data = self.coordinator.data.get("details", {})
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": data.get("hostname", "Braiins Miner"),
        }

    @property
    def native_min_value(self) -> float:
        """Return min TH/s from tuner_constraints."""
        try:
            # We cast the constraint to int
            return float(
                int(
                    float(
                        self.coordinator.data["constraints"]["tuner_constraints"][
                            "hashrate_target"
                        ]["min"]["terahash_per_second"]
                    )
                )
            )
        except KeyError, TypeError:
            return 10.0

    @property
    def native_max_value(self) -> float:
        """Return max TH/s from tuner_constraints."""
        try:
            return float(
                int(
                    float(
                        self.coordinator.data["constraints"]["tuner_constraints"][
                            "hashrate_target"
                        ]["max"]["terahash_per_second"]
                    )
                )
            )
        except KeyError, TypeError:
            return 300.0

    @property
    def native_value(self) -> int | None:
        """Return the current hashrate target fetched from the miner."""
        val = self.coordinator.data.get("hashrate_target")
        return int(val) if val is not None else None

    @property
    def available(self) -> bool:
        """Only available if Hashrate Target mode is active."""
        return (
            super().available
            and self.coordinator.data.get("performance_mode") == "Hashrate Target"
        )

    async def async_set_native_value(self, value: float) -> None:
        """Send the new hashrate target to the miner."""
        target = int(value)
        success = await self.api.set_hashrate_target(target)
        if success and self.coordinator.data:
            new_data = dict(self.coordinator.data)
            new_data["hashrate_target"] = target
            self.coordinator.async_set_updated_data(new_data)


class BraiinsHashrateStepNumber(NumberEntity):
    """Local configuration entity to set the hashrate adjustment step."""

    _attr_has_entity_name = True
    _attr_name = "Hashrate Adjustment Step"
    _attr_native_unit_of_measurement = "TH/s"
    _attr_icon = "mdi:unfold-more-horizontal"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 100.0
    _attr_native_step = 10

    def __init__(self, coordinator, entry) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_hashrate_step_config"
        data = self.coordinator.data.get("details", {})
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": data.get("hostname", "Braiins Miner"),
        }

    @property
    def native_value(self) -> float:
        """Return the hashrate step value from integration options."""
        return int(self._entry.options.get(CONF_HASHRATE_STEP, DEFAULT_HASHRATE_STEP))

    async def async_set_native_value(self, value: float) -> None:
        """Update the internal hashrate step value in Config Entry options."""
        new_options = dict(self._entry.options)
        new_options[CONF_HASHRATE_STEP] = int(value)
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)


class BraiinsPowerStepNumber(NumberEntity):
    """Local configuration entity to set the increment/decrement step."""

    _attr_has_entity_name = True
    _attr_name = "Power Adjustment Step"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:unfold-more-horizontal"

    # Based on your dps_constraints: min 1, max 1000
    _attr_native_min_value = 1
    _attr_native_max_value = 1000
    _attr_native_step = 1

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_power_step_config"
        # Shared device info logic
        data = self.coordinator.data.get("details", {})
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": data.get("hostname", "Braiins Miner"),
        }

    @property
    def native_value(self) -> int:
        """Return the step value from integration options."""
        return self._entry.options.get(CONF_POWER_STEP, DEFAULT_POWER_STEP)

    async def async_set_native_value(self, value: float) -> None:
        """Update the internal step value in Config Entry options."""
        new_options = dict(self._entry.options)
        new_options[CONF_POWER_STEP] = int(value)
        # This saves the value permanently
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)


class BraiinsPowerTargetNumber(CoordinatorEntity, NumberEntity):
    """Number entity to set the Braiins OS power target."""

    _attr_has_entity_name = True
    _attr_name = "Power Target"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_icon = "mdi:lightning-bolt"

    _attr_native_min_value = 780  # Minimum Watts
    _attr_native_max_value = 6400  # Maximum Watts
    _attr_native_step = 1  # Allows adjustments in increments of 10W

    def __init__(self, coordinator, api, entry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.api = api

        # Link this entity to the existing Braiins OS device in HA
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}}
        self._attr_unique_id = f"{entry.entry_id}_power_target"

    @property
    def native_value(self):
        """Return the current power target fetched from the miner."""
        if self.coordinator.data:
            return self.coordinator.data.get("power_target")
        return None

    @property
    def available(self) -> bool:
        """Only available if Power Target mode is active."""
        return (
            super().available
            and self.coordinator.data.get("performance_mode") == "Power Target"
        )

    async def async_set_native_value(self, value: float) -> None:
        """Send the new power target to the miner."""
        watt_value = int(value)

        success = await self.api.set_power_target(watt_value)

        if success:
            # Optimistically update the coordinator data without a full API poll
            if self.coordinator.data is not None:
                new_data = dict(self.coordinator.data)
                new_data["power_target"] = watt_value

                self.coordinator.async_set_updated_data(new_data)

    @property
    def native_min_value(self) -> float:
        """Return min watts from tuner_constraints."""
        try:
            return float(
                self.coordinator.data["constraints"]["tuner_constraints"][
                    "power_target"
                ]["min"]["watt"]
            )
        except KeyError, TypeError:
            return 780.0

    @property
    def native_max_value(self) -> float:
        """Return max watts from tuner_constraints."""
        try:
            return float(
                self.coordinator.data["constraints"]["tuner_constraints"][
                    "power_target"
                ]["max"]["watt"]
            )
        except KeyError, TypeError:
            return 6500.0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this miner."""
        data = self.coordinator.data.get("details", {})
        ident = data.get("miner_identity", {})

        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name=data.get("hostname")
            or f"Braiins OS+ Miner ({self.coordinator.config_entry.data['miner_ip']})",
            manufacturer="Braiins",
            model=ident.get("miner_model") or "Miner with Braiins OS+",
            sw_version=data.get("bos_version", {}).get("current"),
        )
