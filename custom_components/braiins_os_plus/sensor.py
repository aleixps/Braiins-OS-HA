# custom_components/braiins_os_plus/sensor.py
"""Braiins OS+ integration sensor entities."""

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfTemperature
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

    # Create sensors for each hashboard if data is available on first load
    if coordinator.data and "hashboards" in coordinator.data:
        for board in coordinator.data.get("hashboards", []):
            board_id = board.get("id")
            if board_id is not None:
                sensors.extend(
                    [
                        HashboardChipTempSensor(coordinator, board_id),
                        HashboardBoardTempSensor(coordinator, board_id),
                        HashboardHashrateSensor(coordinator, board_id),
                    ]
                )

    # --- Per-Fan Sensors ---
    if coordinator.data and (cooling := coordinator.data.get("cooling")):
        for fan in cooling.get("fans", []):
            fan_pos = fan.get("position")
            if fan_pos is not None:
                sensors.append(MinerFanSensor(coordinator, fan_pos))
                sensors.append(MinerFanPercentSensor(coordinator, fan_pos))

    # Create aggregate and stats sensors
    sensors.extend(
        [
            TotalHashrateSensor(coordinator),
            HighestChipTempSensor(coordinator),
            HighestBoardTempSensor(coordinator),
            MinerConsumptionSensor(coordinator),
            MinerEfficiencySensor(coordinator),
        ]
    )

    async_add_entities(sensors)


class BraiinsSensor(CoordinatorEntity, SensorEntity):
    """Base class for a Braiins OS+ sensor."""

    def __init__(self, coordinator, entity_suffix: str) -> None:
        """Initialize the Braiins OS+ sensor."""
        super().__init__(coordinator)
        self._config_entry = coordinator.config_entry
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._config_entry.entry_id}_{entity_suffix}"

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
            hw_version=data.get("psu_info", {}).get("model_name"),
            configuration_url=f"http://{self._config_entry.data['miner_ip']}",
            connections={("mac", data.get("mac_address"))}
            if data.get("mac_address")
            else None,
        )

    @property
    def available(self) -> bool:
        """Return True if the coordinator has data."""
        return super().available and self.coordinator.data is not None


# --- Aggregate and Stats Sensors ---


class MinerConsumptionSensor(BraiinsSensor):
    """Sensor for the miner's power consumption."""

    def __init__(self, coordinator) -> None:
        """Initialize the miner consumption sensor."""
        super().__init__(coordinator, "miner_consumption")
        self._attr_name = "Miner Consumption"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    @property
    def native_value(self) -> int | None:
        """Return the power consumption in Watts."""
        stats = self.coordinator.data.get("stats", {})
        power_stats = stats.get("power_stats", {})
        if consumption := power_stats.get("approximated_consumption"):
            return consumption.get("watt", 0)
        return 0


class MinerEfficiencySensor(BraiinsSensor):
    """Sensor for the miner's efficiency."""

    def __init__(self, coordinator) -> None:
        """Initialize the miner efficiency sensor."""
        super().__init__(coordinator, "miner_efficiency")
        self._attr_name = "Miner Efficiency"
        self._attr_native_unit_of_measurement = JOULE_PER_TERAHASH
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:flash"

    @property
    def native_value(self) -> float | None:
        """Return the efficiency in J/TH."""
        stats = self.coordinator.data.get("stats", {})
        power_stats = stats.get("power_stats", {})

        efficiency_data = power_stats.get("efficiency")
        if efficiency_data:
            val = efficiency_data.get("joule_per_terahash")
            if val is not None:
                return round(float(val), 2)

        return 0.0


class TotalHashrateSensor(BraiinsSensor):
    """Sensor for the total real hashrate of all boards."""

    def __init__(self, coordinator) -> None:
        """Initialize the total hashrate sensor."""
        super().__init__(coordinator, "total_hashrate")
        self._attr_name = "Total Hashrate"
        self._attr_native_unit_of_measurement = TERAHASH_PER_SECOND
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float | None:
        """Return the total hashrate in TH/s."""
        if self.coordinator.data and (
            hashboards := self.coordinator.data.get("hashboards")
        ):
            total_ghs = sum(
                board.get("stats", {})
                .get("real_hashrate", {})
                .get("last_5s", {})
                .get("gigahash_per_second", 0)
                for board in hashboards
            )
            return round(total_ghs / 1000, 2)
        return None


class HighestChipTempSensor(BraiinsSensor):
    """Sensor for the highest chip temperature across all boards."""

    def __init__(self, coordinator) -> None:
        """Initialize the highest chip temperature sensor."""
        super().__init__(coordinator, "highest_chip_temp")
        self._attr_name = "Chip Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the highest chip temperature across all boards."""
        cooling = self.coordinator.data.get("cooling", {})
        return (
            cooling.get("highest_temperature", {})
            .get("temperature", {})
            .get("degree_c")
        )


class HighestBoardTempSensor(BraiinsSensor):
    """Sensor for the highest board temperature across all boards."""

    def __init__(self, coordinator) -> None:
        """Initialize the highest board temperature sensor."""
        super().__init__(coordinator, "highest_board_temp")
        self._attr_name = "Board Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the highest board temperature across all boards."""
        if not self.coordinator.data:
            return None

        hashboards = self.coordinator.data.get("hashboards")
        if not hashboards:
            return None

        temps = []
        for board in hashboards:
            # Defensive check: ensure board is not None and board_temp is not None
            if board and (bt := board.get("board_temp")):
                val = bt.get("degree_c")
                if val is not None:
                    temps.append(float(val))

        return max(temps) if temps else None


# --- Per-Hashboard Sensors ---


class HashboardSensor(BraiinsSensor):
    """Base class for a sensor tied to a specific hashboard."""

    def __init__(self, coordinator, board_id: str, entity_suffix: str) -> None:
        """Initialize a hashboard-level sensor."""
        super().__init__(coordinator, f"board_{board_id}_{entity_suffix}")
        self.board_id = board_id

    @property
    def board_data(self) -> dict[str, Any] | None:
        """Return the data for this specific hashboard."""
        if self.coordinator.data and (
            hashboards := self.coordinator.data.get("hashboards")
        ):
            for board in hashboards:
                if board.get("id") == self.board_id:
                    return board
        return None

    @property
    def available(self) -> bool:
        """Return True if the board data is available."""
        return super().available and self.board_data is not None


class HashboardChipTempSensor(HashboardSensor):
    """Sensor for a single hashboard's highest chip temperature."""

    def __init__(self, coordinator, board_id: str) -> None:
        """Initialize the hashboard chip temperature sensor."""
        super().__init__(coordinator, board_id, "chip_temp")
        self._attr_name = f"Hashboard {board_id} Chip Temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the highest chip temperature for this hashboard."""
        if self.board_data and (chip_temp := self.board_data.get("highest_chip_temp")):
            if temp := chip_temp.get("temperature"):
                return temp.get("degree_c")
        return None


class HashboardBoardTempSensor(HashboardSensor):
    """Sensor for a single hashboard's board temperature."""

    def __init__(self, coordinator, board_id: str) -> None:
        """Initialize the hashboard board temperature sensor."""
        super().__init__(coordinator, board_id, "board_temp")
        self._attr_name = f"Hashboard {board_id} Board Temp"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the board temperature for this hashboard."""
        if self.board_data and (board_temp := self.board_data.get("board_temp")):
            return board_temp.get("degree_c")
        return None


class HashboardHashrateSensor(HashboardSensor):
    """Sensor for a single hashboard's hashrate."""

    def __init__(self, coordinator, board_id: str) -> None:
        """Initialize the hashboard hashrate sensor."""
        super().__init__(coordinator, board_id, "hashrate")
        self._attr_name = f"Hashboard {board_id} Hashrate"
        self._attr_native_unit_of_measurement = TERAHASH_PER_SECOND
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float | None:
        """Return the hashrate in TH/s."""
        if self.board_data and (stats := self.board_data.get("stats")):
            if real_hash := stats.get("real_hashrate"):
                if last_5s := real_hash.get("last_5s"):
                    if (hashrate_ghs := last_5s.get("gigahash_per_second")) is not None:
                        return round(hashrate_ghs / 1000, 2)
        return None


class MinerFanSensor(BraiinsSensor):
    """Sensor for an individual miner fan speed."""

    def __init__(self, coordinator, fan_id: int) -> None:
        """Initialize the fan sensor."""
        super().__init__(coordinator, f"fan_{fan_id}")
        self.fan_id = fan_id
        self._attr_name = f"Fan {fan_id} Speed"
        self._attr_native_unit_of_measurement = "RPM"
        self._attr_icon = "mdi:fan"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the RPM of the fan."""
        fans = self.coordinator.data.get("cooling", {}).get("fans", [])
        for fan in fans:
            if fan.get("position") == self.fan_id:
                return fan.get("rpm")
        return None


class MinerFanPercentSensor(BraiinsSensor):
    """Sensor for an individual miner fan speed percentage."""

    def __init__(self, coordinator, fan_id: int) -> None:
        """Initialize the fan percentage sensor."""
        super().__init__(coordinator, f"fan_{fan_id}_percent")
        self.fan_id = fan_id
        self._attr_name = f"Fan {fan_id} Target Speed"
        self._attr_native_unit_of_measurement = "%"
        self._attr_icon = "mdi:fan-speed-1"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the speed percentage of the fan."""
        fans = self.coordinator.data.get("cooling", {}).get("fans", [])
        for fan in fans:
            if fan.get("position") == self.fan_id:
                ratio = fan.get("target_speed_ratio")
                if ratio is not None:
                    return round(float(ratio) * 100, 1)
        return None
