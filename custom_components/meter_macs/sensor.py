from __future__ import annotations

from typing import Any, List, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MeterMacsCoordinator
from .api import Meter
from .helpers import build_meter_device_key, format_meter_display_name


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: MeterMacsCoordinator = data["coordinator"]

    sensors_balance: List[MeterMacsBalanceSensor] = []
    sensors_cost: List[MeterMacsCostPerKwhSensor] = []
    sensors_last_updated: List[MeterMacsLastUpdatedSensor] = []
    sensors_safety_tripped: List[MeterMacsSafetyTrippedSensor] = []
    for meter in coordinator.data or []:
        sensors_balance.append(MeterMacsBalanceSensor(entry, coordinator, meter))
        sensors_cost.append(MeterMacsCostPerKwhSensor(entry, coordinator, meter))
        sensors_last_updated.append(MeterMacsLastUpdatedSensor(entry, coordinator, meter))
        sensors_safety_tripped.append(MeterMacsSafetyTrippedSensor(entry, coordinator, meter))

    async_add_entities(sensors_balance + sensors_cost + sensors_last_updated + sensors_safety_tripped)


class MeterMacsBalanceSensor(CoordinatorEntity[MeterMacsCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry, coordinator: MeterMacsCoordinator, meter: Meter) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._meter_id = meter.meter_id
        self._name = meter.name
        self._display_name = format_meter_display_name(
            meter.name,
            getattr(meter, "asset_id", None),
            getattr(meter, "site_id", None),
        )
        self._site_id = getattr(meter, "site_id", None)
        self._asset_id = getattr(meter, "asset_id", None)
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_balance"
        self._attr_name = f"Meter MACS {self._display_name} Balance"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, build_meter_device_key(self._entry.entry_id, self._meter_id))},
            "name": f"Meter MACS {self._display_name}",
            "manufacturer": "Meter MACS",
            "model": "Electricity Asset",
            "serial_number": str(self._asset_id or self._meter_id),
        }

    @property
    def native_value(self) -> Optional[float]:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return meter.balance if meter else None

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return meter.currency if meter else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return {
            "meter_id": self._meter_id,
            "meter_name": self._name,
            "site_id": getattr(meter, "site_id", None) if meter else self._site_id,
            "asset_id": getattr(meter, "asset_id", None) if meter else self._asset_id,
            "socket_area": getattr(meter, "socket_area", None) if meter else None,
            "socket_location": getattr(meter, "socket_location", None) if meter else None,
            "session_type": getattr(meter, "session_type", None) if meter else None,
        }


class MeterMacsCostPerKwhSensor(CoordinatorEntity[MeterMacsCoordinator], SensorEntity):
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry, coordinator: MeterMacsCoordinator, meter: Meter) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._meter_id = meter.meter_id
        self._name = meter.name
        self._display_name = format_meter_display_name(
            meter.name,
            getattr(meter, "asset_id", None),
            getattr(meter, "site_id", None),
        )
        self._site_id = getattr(meter, "site_id", None)
        self._asset_id = getattr(meter, "asset_id", None)
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_cost_per_kwh"
        self._attr_name = f"Meter MACS {self._display_name} Electricity Cost Per kWh"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, build_meter_device_key(self._entry.entry_id, self._meter_id))},
            "name": f"Meter MACS {self._display_name}",
            "manufacturer": "Meter MACS",
            "model": "Electricity Asset",
            "serial_number": str(self._asset_id or self._meter_id),
        }

    @property
    def native_value(self) -> Optional[float]:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return getattr(meter, "cost_per_kwh", None) if meter else None

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        # Price per kWh; currency not exposed in all APIs; assume GBP for now
        return "GBP/kWh"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return {
            "meter_id": self._meter_id,
            "meter_name": self._name,
            "site_id": getattr(meter, "site_id", None) if meter else self._site_id,
            "asset_id": getattr(meter, "asset_id", None) if meter else self._asset_id,
            "socket_area": getattr(meter, "socket_area", None) if meter else None,
            "socket_location": getattr(meter, "socket_location", None) if meter else None,
            "session_type": getattr(meter, "session_type", None) if meter else None,
            "uplift_applied": 0.05,
        }


class MeterMacsLastUpdatedSensor(CoordinatorEntity[MeterMacsCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, entry: ConfigEntry, coordinator: MeterMacsCoordinator, meter: Meter) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._meter_id = meter.meter_id
        self._name = meter.name
        self._display_name = format_meter_display_name(
            meter.name,
            getattr(meter, "asset_id", None),
            getattr(meter, "site_id", None),
        )
        self._site_id = getattr(meter, "site_id", None)
        self._asset_id = getattr(meter, "asset_id", None)
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_last_updated"
        self._attr_name = f"Meter MACS {self._display_name} Last Updated"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, build_meter_device_key(self._entry.entry_id, self._meter_id))},
            "name": f"Meter MACS {self._display_name}",
            "manufacturer": "Meter MACS",
            "model": "Electricity Asset",
            "serial_number": str(self._asset_id or self._meter_id),
        }

    @property
    def native_value(self):
        return (
            getattr(self.coordinator, "last_refresh_time", None)
            or getattr(self.coordinator, "last_update_success_time", None)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return {
            "meter_id": self._meter_id,
            "meter_name": self._name,
            "site_id": getattr(meter, "site_id", None) if meter else self._site_id,
            "asset_id": getattr(meter, "asset_id", None) if meter else self._asset_id,
            "socket_area": getattr(meter, "socket_area", None) if meter else None,
            "socket_location": getattr(meter, "socket_location", None) if meter else None,
            "session_type": getattr(meter, "session_type", None) if meter else None,
        }


class MeterMacsSafetyTrippedSensor(CoordinatorEntity[MeterMacsCoordinator], SensorEntity):
    _attr_icon = "mdi:shield-alert"

    def __init__(self, entry: ConfigEntry, coordinator: MeterMacsCoordinator, meter: Meter) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._meter_id = meter.meter_id
        self._name = meter.name
        self._display_name = format_meter_display_name(
            meter.name,
            getattr(meter, "asset_id", None),
            getattr(meter, "site_id", None),
        )
        self._site_id = getattr(meter, "site_id", None)
        self._asset_id = getattr(meter, "asset_id", None)
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_safety_tripped"
        self._attr_name = f"Meter MACS {self._display_name} Safety Tripped"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, build_meter_device_key(self._entry.entry_id, self._meter_id))},
            "name": f"Meter MACS {self._display_name}",
            "manufacturer": "Meter MACS",
            "model": "Electricity Asset",
            "serial_number": str(self._asset_id or self._meter_id),
        }

    @property
    def native_value(self) -> str:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return "yes" if getattr(meter, "socket_state", None) == 1 else "no"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meter = next((m for m in (self.coordinator.data or []) if m.meter_id == self._meter_id), None)
        return {
            "meter_id": self._meter_id,
            "meter_name": self._name,
            "site_id": getattr(meter, "site_id", None) if meter else self._site_id,
            "asset_id": getattr(meter, "asset_id", None) if meter else self._asset_id,
            "socket_area": getattr(meter, "socket_area", None) if meter else None,
            "socket_location": getattr(meter, "socket_location", None) if meter else None,
            "socket_state": getattr(meter, "socket_state", None) if meter else None,
            "session_type": getattr(meter, "session_type", None) if meter else None,
        }
