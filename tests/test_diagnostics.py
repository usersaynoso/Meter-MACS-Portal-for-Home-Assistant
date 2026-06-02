from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import importlib.util
import sys
import types
from enum import Enum
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "meter_macs"


def _install_homeassistant_stubs() -> None:
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    if not hasattr(homeassistant, "__path__"):
        homeassistant.__path__ = []

    ha_const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
    if not hasattr(ha_const, "Platform"):
        class Platform(str, Enum):
            SENSOR = "sensor"
            SWITCH = "switch"

        ha_const.Platform = Platform

    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    if not hasattr(config_entries, "ConfigEntry"):
        class ConfigEntry:
            pass

        config_entries.ConfigEntry = ConfigEntry

    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    if not hasattr(core, "HomeAssistant"):
        class HomeAssistant:
            pass

        core.HomeAssistant = HomeAssistant


def _load_module(module_name: str):
    _install_homeassistant_stubs()

    custom_components = sys.modules.setdefault(
        "custom_components",
        types.ModuleType("custom_components"),
    )
    if not hasattr(custom_components, "__path__"):
        custom_components.__path__ = [str(REPO_ROOT / "custom_components")]

    package = sys.modules.setdefault(
        "custom_components.meter_macs",
        types.ModuleType("custom_components.meter_macs"),
    )
    package.__path__ = [str(PACKAGE_ROOT)]

    full_name = f"custom_components.meter_macs.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, PACKAGE_ROOT / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


API = _load_module("api")
DIAGNOSTICS = _load_module("diagnostics")
Meter = API.Meter


class _DummyEntry:
    entry_id = "entry-1"
    data = {"email": "user@example.com", "password": "secret"}
    options = {
        "selected_meters": ["CRT_WM_3378"],
        "scan_interval_minutes": 5,
    }


class _DummyClient:
    _base_url = "https://portal.meter-macs.com"
    _logged_in = True
    _auth_cookie_header = "__Secure-meter-macs.session_token=secret"
    _auth_cookie_names = [
        "__Secure-meter-macs.session_token",
        "__Secure-meter-macs.session_data",
    ]
    last_login_status = 200
    last_login_error = None
    last_session_validated = True
    last_auth_failure = None


class _DummyCoordinator:
    def __init__(self, meters: list[Meter]) -> None:
        self.data = meters
        self.all_meters = meters
        self.last_refresh_time = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
        self.last_update_success_time = datetime(2026, 5, 30, 12, 1, tzinfo=timezone.utc)
        self.last_exception = RuntimeError("last failure")
        self.update_interval = timedelta(minutes=5)
        self._selected_meter_ids = {"CRT_WM_3378"}


def test_diagnostics_include_auth_and_meter_debug_data_without_secrets() -> None:
    meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=3.08,
        currency=None,
        imported_energy_kwh=13309.67,
        balance_reading_date=datetime(2026, 5, 30, 11, 50, tzinfo=timezone.utc),
        site_id="CRT_WM",
        asset_id=3378,
        cost_per_kwh=0.357,
        site_db_id="site-db",
        asset_db_id="asset-db",
        socket_site="Blackwall Basin",
        socket_area="BWB Bollard 12",
        socket_location="1202",
        socket_state=7,
        session_type="current",
    )
    entry = _DummyEntry()
    hass = types.SimpleNamespace(
        data={
            DIAGNOSTICS.DOMAIN: {
                entry.entry_id: {
                    "client": _DummyClient(),
                    "coordinator": _DummyCoordinator([meter]),
                }
            }
        }
    )

    diagnostics = asyncio.run(DIAGNOSTICS.async_get_config_entry_diagnostics(hass, entry))

    assert diagnostics["version"] == "0.1.29"
    assert diagnostics["email"] == "***"
    assert diagnostics["has_password"] is True
    assert "secret" not in str(diagnostics)
    assert diagnostics["client"]["auth_cookie_present"] is True
    assert diagnostics["client"]["auth_cookie_names"] == [
        "__Secure-meter-macs.session_data",
        "__Secure-meter-macs.session_token",
    ]
    assert diagnostics["coordinator"]["meters"] == 1
    assert diagnostics["coordinator"]["last_exception"] == {
        "type": "RuntimeError",
        "message": "last failure",
    }
    assert diagnostics["meters_sample"][0]["meter_id"] == "CRT_WM_3378"
    assert diagnostics["meters_sample"][0]["site_db_id_present"] is True
    assert diagnostics["meters_sample"][0]["asset_db_id_present"] is True
