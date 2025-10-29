from __future__ import annotations

from typing import Any, List, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MeterMacsCoordinator
from .api import Meter


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: MeterMacsCoordinator = data["coordinator"]

    sensors_balance: List[MeterMacsBalanceSensor] = []
    sensors_cost: List[MeterMacsCostPerKwhSensor] = []
    for meter in coordinator.data or []:
        sensors_balance.append(MeterMacsBalanceSensor(entry, coordinator, meter))
        sensors_cost.append(MeterMacsCostPerKwhSensor(entry, coordinator, meter))

    async_add_entities(sensors_balance + sensors_cost)


class MeterMacsBalanceSensor(CoordinatorEntity[MeterMacsCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry, coordinator: MeterMacsCoordinator, meter: Meter) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._meter_id = meter.meter_id
        self._name = meter.name
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_balance"
        self._attr_name = f"Meter MACS {meter.name} Balance"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Meter MACS",
            "manufacturer": "Meter MACS",
            "model": "Portal",
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
            "site_id": getattr(meter, "site_id", None) if meter else None,
        }


class MeterMacsCostPerKwhSensor(CoordinatorEntity[MeterMacsCoordinator], SensorEntity):
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry, coordinator: MeterMacsCoordinator, meter: Meter) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._meter_id = meter.meter_id
        self._name = meter.name
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_cost_per_kwh"
        self._attr_name = f"Meter MACS {meter.name} Electricity Cost Per kWh"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Meter MACS",
            "manufacturer": "Meter MACS",
            "model": "Portal",
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
            "site_id": getattr(meter, "site_id", None) if meter else None,
            "uplift_applied": 0.05,
        }


