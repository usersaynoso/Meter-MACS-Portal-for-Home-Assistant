from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .helpers import selected_meter_ids_from_options


def _integration_version() -> str | None:
    try:
        manifest = json.loads(
            (Path(__file__).with_name("manifest.json")).read_text(encoding="utf-8")
        )
    except Exception:  # noqa: BLE001
        return None
    version = manifest.get("version")
    return version if isinstance(version, str) else None


def _safe_isoformat(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return None
    return None


def _safe_exception(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    return {
        "type": type(value).__name__,
        "message": str(value),
    }


def _client_diagnostics(client: Any) -> dict[str, Any]:
    return {
        "base_url": getattr(client, "_base_url", None),
        "logged_in": getattr(client, "_logged_in", None),
        "auth_cookie_present": bool(getattr(client, "_auth_cookie_header", None)),
        "auth_cookie_names": sorted(getattr(client, "_auth_cookie_names", []) or []),
        "last_login_status": getattr(client, "last_login_status", None),
        "last_login_error": getattr(client, "last_login_error", None),
        "last_session_validated": getattr(client, "last_session_validated", None),
        "last_auth_failure": getattr(client, "last_auth_failure", None),
    }


def _meter_sample(meter: Any) -> dict[str, Any]:
    reading_date = getattr(meter, "balance_reading_date", None)
    return {
        "meter_id": getattr(meter, "meter_id", None),
        "name": getattr(meter, "name", None),
        "balance": getattr(meter, "balance", None),
        "currency": getattr(meter, "currency", None),
        "imported_energy_kwh": getattr(meter, "imported_energy_kwh", None),
        "balance_reading_date": _safe_isoformat(reading_date),
        "asset_id": getattr(meter, "asset_id", None),
        "site_id": getattr(meter, "site_id", None),
        "cost_per_kwh": getattr(meter, "cost_per_kwh", None),
        "site_db_id_present": bool(getattr(meter, "site_db_id", None)),
        "asset_db_id_present": bool(getattr(meter, "asset_db_id", None)),
        "socket_site": getattr(meter, "socket_site", None),
        "socket_area": getattr(meter, "socket_area", None),
        "socket_location": getattr(meter, "socket_location", None),
        "socket_state": getattr(meter, "socket_state", None),
        "session_type": getattr(meter, "session_type", None),
    }


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    selected_meter_ids = selected_meter_ids_from_options(entry.options)
    diag: dict[str, Any] = {
        "domain": DOMAIN,
        "version": _integration_version(),
        "email": "***",
        "has_password": bool(entry.data.get("password")),
        "options": {
            "selected_meters_mode": "all"
            if selected_meter_ids is None
            else "selected",
            "selected_meters": sorted(selected_meter_ids or []),
            "raw_keys": sorted(entry.options.keys()),
        },
        "coordinator": {
            "loaded": False,
            "meters": 0,
            "discovered_meters": 0,
        },
    }
    if data:
        client = data.get("client")
        if client is not None:
            diag["client"] = _client_diagnostics(client)

        coordinator = data.get("coordinator")
        if coordinator:
            current_meters = list(coordinator.data or [])
            all_meters = list(getattr(coordinator, "all_meters", []) or [])
            update_interval = getattr(coordinator, "update_interval", None)
            diag["coordinator"] = {
                "loaded": True,
                "meters": len(current_meters),
                "discovered_meters": len(all_meters),
                "last_refresh_time": _safe_isoformat(getattr(coordinator, "last_refresh_time", None)),
                "last_update_success_time": _safe_isoformat(
                    getattr(coordinator, "last_update_success_time", None)
                ),
                "last_exception": _safe_exception(getattr(coordinator, "last_exception", None)),
                "update_interval_seconds": update_interval.total_seconds()
                if hasattr(update_interval, "total_seconds")
                else None,
                "selected_meter_filter": sorted(
                    getattr(coordinator, "_selected_meter_ids", None) or []
                )
                if getattr(coordinator, "_selected_meter_ids", None) is not None
                else None,
            }
            diag["meters_sample"] = [_meter_sample(meter) for meter in current_meters[:5]]
            diag["all_meters_sample"] = [_meter_sample(meter) for meter in all_meters[:5]]
    return diag
