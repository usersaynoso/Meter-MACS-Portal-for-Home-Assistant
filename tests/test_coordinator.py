from __future__ import annotations

import asyncio
from datetime import timedelta
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

    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    if not hasattr(core, "HomeAssistant"):
        class HomeAssistant:
            pass

        core.HomeAssistant = HomeAssistant

    exceptions = sys.modules.setdefault(
        "homeassistant.exceptions",
        types.ModuleType("homeassistant.exceptions"),
    )
    if not hasattr(exceptions, "ConfigEntryAuthFailed"):
        class ConfigEntryAuthFailed(Exception):
            pass

        exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed

    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    if not hasattr(helpers, "__path__"):
        helpers.__path__ = []

    update_coordinator = sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator",
        types.ModuleType("homeassistant.helpers.update_coordinator"),
    )
    if not hasattr(update_coordinator, "DataUpdateCoordinator"):
        class DataUpdateCoordinator:
            def __init__(self, hass, logger, name, update_interval) -> None:
                self.hass = hass
                self.logger = logger
                self.name = name
                self.update_interval = update_interval

            def __class_getitem__(cls, _item):
                return cls

        class UpdateFailed(Exception):
            pass

        update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
        update_coordinator.UpdateFailed = UpdateFailed


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
COORDINATOR = _load_module("coordinator")
AuthError = API.AuthError
ConfigEntryAuthFailed = sys.modules["homeassistant.exceptions"].ConfigEntryAuthFailed


class _DummyClient:
    _base_url = "https://portal.meter-macs.com"

    async def fetch_dashboard(self) -> str:
        raise AssertionError("HTML fallback should not run for authentication failures")


def test_update_data_surfaces_auth_error_without_html_fallback(monkeypatch) -> None:
    coordinator = COORDINATOR.MeterMacsCoordinator(
        hass=types.SimpleNamespace(),
        client=_DummyClient(),
        update_interval=timedelta(seconds=60),
    )

    async def fake_fetch_meters(_selected_meter_ids=None):
        raise AuthError("expired session")

    monkeypatch.setattr(coordinator._api, "fetch_meters", fake_fetch_meters)

    try:
        asyncio.run(coordinator._async_update_data())
    except ConfigEntryAuthFailed:
        pass
    else:
        raise AssertionError("ConfigEntryAuthFailed was not raised")
