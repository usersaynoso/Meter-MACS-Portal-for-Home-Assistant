from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    diag: dict[str, Any] = {
        "email": "***",
        "meters": 0,
    }
    if data:
        coordinator = data.get("coordinator")
        if coordinator and coordinator.data is not None:
            diag["meters"] = len(coordinator.data)
            diag["sample"] = [
                {
                    "meter_id": m.meter_id,
                    "name": m.name,
                    "balance": m.balance,
                    "currency": m.currency,
                }
                for m in coordinator.data[:3]
            ]
    return diag


