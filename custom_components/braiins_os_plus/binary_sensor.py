# custom_components/braiins_os_plus/binary_sensor.py
"""Braiins OS+ integration binary sensor entities."""

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _safe_id(value: Any) -> str:
    """Return a stable unique-id fragment for Braiins-provided IDs."""
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Braiins OS+ binary sensors from a config entry."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = domain_data["coordinator"]
    api = domain_data["api"]

    sensors = [HeartbeatBinarySensor(coordinator, api)]
    if coordinator.data and "hashboards" in coordinator.data:
        for board in coordinator.data.get("hashboards", []):
            board_id = board.get("id")
            if board_id is not None:
                sensors.append(HashboardEnabledBinarySensor(coordinator, board_id))

    if coordinator.data and "pools" in coordinator.data:
        pool_index = 1
        for group in coordinator.data.get("pools", []):
            group_uid = group.get("uid")
            for pool in group.get("pools", []):
                pool_uid = pool.get("uid")
                if group_uid is not None and pool_uid is not None:
                    sensors.extend(
                        [
                            PoolEnabledBinarySensor(
                                coordinator, group_uid, pool_uid, pool_index
                            ),
                            PoolAliveBinarySensor(
                                coordinator, group_uid, pool_uid, pool_index
                            ),
                            PoolActiveBinarySensor(
                                coordinator, group_uid, pool_uid, pool_index
                            ),
                        ]
                    )
                    pool_index += 1

    async_add_entities(sensors)


class BraiinsBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for a Braiins OS+ binary sensor."""

    def __init__(self, coordinator, entity_suffix: str) -> None:
        """Initialize the Braiins OS+ binary sensor."""
        super().__init__(coordinator)
        self._config_entry = coordinator.config_entry
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._config_entry.entry_id}_{entity_suffix}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

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

    @property
    def available(self) -> bool:
        """Return True if the coordinator has data."""
        return super().available and self.coordinator.data is not None


class HeartbeatBinarySensor(BraiinsBinarySensor):
    """Binary sensor for coordinator/API heartbeat state."""

    def __init__(self, coordinator, api) -> None:
        """Initialize the heartbeat binary sensor."""
        super().__init__(coordinator, "heartbeat")
        self._api = api
        self._attr_name = "API Heartbeat"
        self._attr_icon = "mdi:heart-pulse"

    @property
    def available(self) -> bool:
        """Keep heartbeat available so connection loss shows as off, not unavailable."""
        return True

    @property
    def is_on(self) -> bool:
        """Return whether the latest poll hit the miner live."""
        return bool(self._api.last_live_reachability)


class HashboardEnabledBinarySensor(BraiinsBinarySensor):
    """Binary sensor for a hashboard's direct Braiins enabled state."""

    def __init__(self, coordinator, board_id: str) -> None:
        """Initialize the hashboard enabled binary sensor."""
        super().__init__(coordinator, f"board_{board_id}_enabled")
        self.board_id = board_id
        self._attr_name = f"Hashboard {board_id} Enabled"
        self._attr_icon = "mdi:expansion-card"

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

    @property
    def is_on(self) -> bool | None:
        """Return whether the hashboard is enabled."""
        if self.board_data is None:
            return None
        return self.board_data.get("enabled")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return selected hashboard details."""
        board = self.board_data or {}
        return {
            "board_name": board.get("board_name"),
            "model": board.get("model"),
            "serial_number": board.get("serial_number"),
            "chip_type": board.get("chip_type"),
            "chips_count": board.get("chips_count"),
        }


class PoolBinarySensor(BraiinsBinarySensor):
    """Base class for a direct Braiins pool binary sensor."""

    pool_field: str

    def __init__(
        self,
        coordinator,
        group_uid: str,
        pool_uid: str,
        pool_index: int,
        entity_suffix: str,
    ) -> None:
        """Initialize the pool binary sensor."""
        safe_group_uid = _safe_id(group_uid)
        safe_pool_uid = _safe_id(pool_uid)
        super().__init__(
            coordinator, f"pool_{safe_group_uid}_{safe_pool_uid}_{entity_suffix}"
        )
        self.group_uid = group_uid
        self.pool_uid = pool_uid
        self.pool_index = pool_index
        self._attr_icon = "mdi:server-network"

    @property
    def pool_data(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Return the Braiins pool group and pool data for this sensor."""
        pool_groups = self.coordinator.data.get("pools", [])
        if not isinstance(pool_groups, list):
            return None, None

        for group in pool_groups:
            if group.get("uid") != self.group_uid:
                continue
            for pool in group.get("pools", []):
                if pool.get("uid") == self.pool_uid:
                    return group, pool
        return None, None

    @property
    def available(self) -> bool:
        """Return True if the pool data is available."""
        _, pool = self.pool_data
        return super().available and pool is not None

    @property
    def is_on(self) -> bool | None:
        """Return the pool boolean state from the direct Braiins field."""
        _, pool = self.pool_data
        if pool is None:
            return None
        return pool.get(self.pool_field)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return pool details."""
        group, pool = self.pool_data
        pool = pool or {}
        group = group or {}
        return {
            "group_uid": group.get("uid"),
            "group_name": group.get("name"),
            "pool_uid": pool.get("uid"),
            "pool_index": self.pool_index,
            "url": pool.get("url"),
            "user": pool.get("user"),
        }


class PoolEnabledBinarySensor(PoolBinarySensor):
    """Binary sensor for whether a pool is configured as enabled."""

    pool_field = "enabled"

    def __init__(
        self, coordinator, group_uid: str, pool_uid: str, pool_index: int
    ) -> None:
        """Initialize the pool enabled binary sensor."""
        super().__init__(coordinator, group_uid, pool_uid, pool_index, "enabled")
        self._attr_name = f"Pool {pool_index} Enabled"


class PoolAliveBinarySensor(PoolBinarySensor):
    """Binary sensor for whether a pool is alive/reachable."""

    pool_field = "alive"

    def __init__(
        self, coordinator, group_uid: str, pool_uid: str, pool_index: int
    ) -> None:
        """Initialize the pool alive binary sensor."""
        super().__init__(coordinator, group_uid, pool_uid, pool_index, "alive")
        self._attr_name = f"Pool {pool_index} Alive"


class PoolActiveBinarySensor(PoolBinarySensor):
    """Binary sensor for whether a pool is currently active."""

    pool_field = "active"

    def __init__(
        self, coordinator, group_uid: str, pool_uid: str, pool_index: int
    ) -> None:
        """Initialize the pool active binary sensor."""
        super().__init__(coordinator, group_uid, pool_uid, pool_index, "active")
        self._attr_name = f"Pool {pool_index} Active"
