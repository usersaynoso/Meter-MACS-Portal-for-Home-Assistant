from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .helpers import selected_meter_ids_from_options


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    diag: dict[str, Any] = {
        "email": "***",
        "meters": 0,
        "selected_meters": sorted(selected_meter_ids_from_options(entry.options) or []),
    }
    if data:
        coordinator = data.get("coordinator")
        if coordinator and coordinator.data is not None:
            diag["meters"] = len(coordinator.data)
            diag["discovered_meters"] = len(getattr(coordinator, "all_meters", []))
            diag["sample"] = [
                {
                    "meter_id": m.meter_id,
                    "name": m.name,
                    "balance": m.balance,
                    "currency": m.currency,
                    "asset_id": getattr(m, "asset_id", None),
                    "site_id": getattr(m, "site_id", None),
                    "socket_site": getattr(m, "socket_site", None),
                    "socket_area": getattr(m, "socket_area", None),
                    "socket_location": getattr(m, "socket_location", None),
                    "session_type": getattr(m, "session_type", None),
                }
                for m in coordinator.data[:3]
            ]
    return diag
