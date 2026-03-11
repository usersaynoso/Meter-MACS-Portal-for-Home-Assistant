from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MeterMacsCoordinator
from .api import MeterApi, Meter
from .helpers import build_meter_device_key, format_meter_display_name


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: MeterMacsCoordinator = data["coordinator"]
    client = data["client"]

    api = MeterApi(client)

    switches: list[MeterMacsSupplySwitch] = []
    for meter in coordinator.data or []:
        # Only add switch when we have both site and asset identifiers
        if getattr(meter, "site_id", None) and getattr(meter, "asset_id", None) is not None:
            switches.append(MeterMacsSupplySwitch(entry, coordinator, api, meter))

    if switches:
        async_add_entities(switches)


class MeterMacsSupplySwitch(CoordinatorEntity[MeterMacsCoordinator], SwitchEntity):
    _attr_icon = "mdi:power-plug"

    def __init__(self, entry: ConfigEntry, coordinator: MeterMacsCoordinator, api: MeterApi, meter: Meter) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._api = api
        self._meter_id = meter.meter_id
        self._name = meter.name
        self._display_name = format_meter_display_name(
            meter.name,
            getattr(meter, "asset_id", None),
            getattr(meter, "site_id", None),
        )
        self._site_id: str = getattr(meter, "site_id", None) or ""
        self._asset_id = getattr(meter, "asset_id", None)
        self._assumed_on: Optional[bool] = None
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_supply"
        self._attr_name = f"Meter MACS {self._display_name} Electricity Supply Switch"

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
    def is_on(self) -> bool:
        # Optimistic state unless we implement a read-back from the API
        return bool(self._assumed_on)

    @property
    def assumed_state(self) -> bool:
        return True

    async def async_turn_on(self, **kwargs: Any) -> None:  # type: ignore[override]
        if not self._site_id or self._asset_id is None:
            return
        await self._api.set_supply_state(self._site_id, self._asset_id, "on")
        self._assumed_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:  # type: ignore[override]
        if not self._site_id or self._asset_id is None:
            return
        await self._api.set_supply_state(self._site_id, self._asset_id, "off")
        self._assumed_on = False
        self.async_write_ha_state()

