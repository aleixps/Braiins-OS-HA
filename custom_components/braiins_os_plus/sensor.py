# custom_components/braiins_os_plus/sensor.py

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TERAHASH_PER_SECOND = "TH/s"
JOULE_PER_TERAHASH = "J/TH"

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Braiins OS+ sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    sensors = []

    # Create sensors for each hashboard if data is available
    if coordinator.data and "hashboards" in coordinator.data:
        for board in coordinator.data.get("hashboards", []):
            board_id = board.get("id")
            sensors.extend([
                HashboardChipTempSensor(coordinator, board_id),
                HashboardBoardTempSensor(coordinator, board_id),
                HashboardHashrateSensor(coordinator, board_id),
            ])
    
    # Create aggregate and stats sensors
    sensors.extend([
        TotalHashrateSensor(coordinator),
        HighestChipTempSensor(coordinator),
        HighestBoardTempSensor(coordinator),
        MinerConsumptionSensor(coordinator),
        MinerEfficiencySensor(coordinator),
    ])

    async_add_entities(sensors)


class BraiinsSensor(CoordinatorEntity, SensorEntity):
    """Base class for a Braiins OS+ sensor."""

    def __init__(self, coordinator, entity_suffix: str):
        super().__init__(coordinator)
        self._config_entry = coordinator.config_entry
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._config_entry.entry_id}_{entity_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the sensors."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=f"Braiins OS+ Miner ({self._config_entry.data['miner_ip']})",
            manufacturer="Braiins",
            model="Miner with Braiins OS+",
        )
    
    @property
    def available(self) -> bool:
        """Return True if the coordinator has data."""
        return super().available and self.coordinator.data is not None


# --- Aggregate and Stats Sensors ---

class MinerConsumptionSensor(BraiinsSensor):
    """Sensor for the miner's power consumption."""
    def __init__(self, coordinator):
        super().__init__(coordinator, "miner_consumption")
        self._attr_name = "Miner Consumption"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    @property
    def native_value(self) -> int | None:
        """Return the power consumption in Watts."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("power_stats", {}).get("approximated_consumption", {}).get("watt")

class MinerEfficiencySensor(BraiinsSensor):
    """Sensor for the miner's efficiency."""
    def __init__(self, coordinator):
        super().__init__(coordinator, "miner_efficiency")
        self._attr_name = "Miner Efficiency"
        self._attr_native_unit_of_measurement = JOULE_PER_TERAHASH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:flash"

    @property
    def native_value(self) -> float | None:
        """Return the efficiency in J/TH."""
        if not self.coordinator.data:
            return None
        efficiency = self.coordinator.data.get("power_stats", {}).get("efficiency", {}).get("joule_per_terahash")
        return round(efficiency, 2) if efficiency is not None else None

class TotalHashrateSensor(BraiinsSensor):
    """Sensor for the total real hashrate of all boards."""
    def __init__(self, coordinator):
        super().__init__(coordinator, "total_hashrate")
        self._attr_name = "Total Hashrate"
        self._attr_native_unit_of_measurement = TERAHASH_PER_SECOND
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float | None:
        """Return the total hashrate in TH/s."""
        if not self.coordinator.data or "hashboards" not in self.coordinator.data:
            return None
        
        total_ghs = sum(
            board.get("stats", {}).get("real_hashrate", {}).get("last_5s", {}).get("gigahash_per_second", 0)
            for board in self.coordinator.data["hashboards"]
        )
        return round(total_ghs / 1000, 2)

class HighestChipTempSensor(BraiinsSensor):
    """Sensor for the highest chip temperature across all boards."""
    def __init__(self, coordinator):
        super().__init__(coordinator, "highest_chip_temp")
        self._attr_name = "Chip Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the highest chip temperature."""
        if not self.coordinator.data or "hashboards" not in self.coordinator.data:
            return None
            
        temps = [
            board.get("highest_chip_temp", {}).get("temperature", {}).get("degree_c")
            for board in self.coordinator.data["hashboards"]
        ]
        valid_temps = [temp for temp in temps if temp is not None]
        return max(valid_temps) if valid_temps else None

class HighestBoardTempSensor(BraiinsSensor):
    """Sensor for the highest board temperature across all boards."""
    def __init__(self, coordinator):
        super().__init__(coordinator, "highest_board_temp")
        self._attr_name = "Board Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the highest board temperature."""
        if not self.coordinator.data or "hashboards" not in self.coordinator.data:
            return None
        
        temps = [
            board.get("board_temp", {}).get("degree_c")
            for board in self.coordinator.data["hashboards"]
        ]
        valid_temps = [temp for temp in temps if temp is not None]
        return max(valid_temps) if valid_temps else None


# --- Per-Hashboard Sensors ---

class HashboardSensor(BraiinsSensor):
    """Base class for a sensor tied to a specific hashboard."""
    def __init__(self, coordinator, board_id: str, entity_suffix: str):
        super().__init__(coordinator, f"board_{board_id}_{entity_suffix}")
        self.board_id = board_id

    @property
    def board_data(self) -> dict[str, Any] | None:
        """Return the data for this specific hashboard."""
        if not self.coordinator.data or "hashboards" not in self.coordinator.data:
            return None
        
        for board in self.coordinator.data["hashboards"]:
            if board.get("id") == self.board_id:
                return board
        return None

    @property
    def available(self) -> bool:
        """Return True if the board data is available."""
        return super().available and self.board_data is not None


class HashboardChipTempSensor(HashboardSensor):
    """Sensor for a single hashboard's highest chip temperature."""
    # ### THE FIX IS HERE: __init__ method is present ###
    def __init__(self, coordinator, board_id: str):
        super().__init__(coordinator, board_id, "chip_temp")
        self._attr_name = f"Hashboard {board_id} Chip Temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        if not self.board_data:
            return None
        return self.board_data.get("highest_chip_temp", {}).get("temperature", {}).get("degree_c")


class HashboardBoardTempSensor(HashboardSensor):
    """Sensor for a single hashboard's board temperature."""
    # ### THE FIX IS HERE: __init__ method is present ###
    def __init__(self, coordinator, board_id: str):
        super().__init__(coordinator, board_id, "board_temp")
        self._attr_name = f"Hashboard {board_id} Board Temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        if not self.board_data:
            return None
        return self.board_data.get("board_temp", {}).get("degree_c")


class HashboardHashrateSensor(HashboardSensor):
    """Sensor for a single hashboard's hashrate."""
    # ### THE FIX IS HERE: __init__ method is present ###
    def __init__(self, coordinator, board_id: str):
        super().__init__(coordinator, board_id, "hashrate")
        self._attr_name = f"Hashboard {board_id} Hashrate"
        self._attr_native_unit_of_measurement = TERAHASH_PER_SECOND
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float | None:
        """Return the hashrate in TH/s."""
        if not self.board_data:
            return None
        
        hashrate_ghs = self.board_data.get("stats", {}).get("real_hashrate", {}).get("last_5s", {}).get("gigahash_per_second")
        if hashrate_ghs is None:
            return None
        
        return round(hashrate_ghs / 1000, 2)