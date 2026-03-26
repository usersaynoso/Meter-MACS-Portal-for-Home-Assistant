from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from enum import Enum
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "meter_macs"


def _load_module():
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    if not hasattr(homeassistant, "__path__"):
        homeassistant.__path__ = []

    ha_const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
    if not hasattr(ha_const, "Platform"):
        class Platform(str, Enum):
            SENSOR = "sensor"
            SWITCH = "switch"

        ha_const.Platform = Platform

    ha_config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    if not hasattr(ha_config_entries, "ConfigEntry"):
        class ConfigEntry:
            pass

        ha_config_entries.ConfigEntry = ConfigEntry

    ha_core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    if not hasattr(ha_core, "HomeAssistant"):
        class HomeAssistant:
            pass

        ha_core.HomeAssistant = HomeAssistant

    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    if not hasattr(helpers, "__path__"):
        helpers.__path__ = []

    config_validation = sys.modules.setdefault(
        "homeassistant.helpers.config_validation",
        types.ModuleType("homeassistant.helpers.config_validation"),
    )
    if not hasattr(config_validation, "config_entry_only_config_schema"):
        config_validation.config_entry_only_config_schema = lambda domain: domain

    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    if not hasattr(aiohttp_client, "async_get_clientsession"):
        aiohttp_client.async_get_clientsession = lambda hass: object()

    device_registry = sys.modules.setdefault(
        "homeassistant.helpers.device_registry",
        types.ModuleType("homeassistant.helpers.device_registry"),
    )
    if not hasattr(device_registry, "async_get"):
        device_registry.async_get = lambda hass: object()
    if not hasattr(device_registry, "async_entries_for_config_entry"):
        device_registry.async_entries_for_config_entry = lambda registry, entry_id: []

    entity_registry = sys.modules.setdefault(
        "homeassistant.helpers.entity_registry",
        types.ModuleType("homeassistant.helpers.entity_registry"),
    )
    if not hasattr(entity_registry, "async_get"):
        entity_registry.async_get = lambda hass: object()
    if not hasattr(entity_registry, "async_entries_for_config_entry"):
        entity_registry.async_entries_for_config_entry = lambda registry, entry_id: []

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

    api_module = types.ModuleType("custom_components.meter_macs.api")

    class MeterMacsClient:
        def __init__(self, session, email: str, password: str) -> None:
            self.session = session
            self.email = email
            self.password = password

    api_module.MeterMacsClient = MeterMacsClient
    sys.modules["custom_components.meter_macs.api"] = api_module

    coordinator_module = types.ModuleType("custom_components.meter_macs.coordinator")

    class MeterMacsCoordinator:
        instances: list["MeterMacsCoordinator"] = []

        def __init__(self, hass, client, update_interval, selected_meter_ids=None) -> None:
            self.hass = hass
            self.client = client
            self.update_interval = update_interval
            self.selected_meter_ids = selected_meter_ids
            self.refresh_calls = 0
            self.all_meters = []
            MeterMacsCoordinator.instances.append(self)

        async def async_config_entry_first_refresh(self) -> None:
            self.refresh_calls += 1

    coordinator_module.MeterMacsCoordinator = MeterMacsCoordinator
    sys.modules["custom_components.meter_macs.coordinator"] = coordinator_module

    full_name = "custom_components.meter_macs.__init__"
    spec = importlib.util.spec_from_file_location(full_name, PACKAGE_ROOT / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module, coordinator_module.MeterMacsCoordinator, api_module.MeterMacsClient


MODULE, MeterMacsCoordinator, MeterMacsClient = _load_module()


class _DummyConfigEntries:
    def __init__(self) -> None:
        self.forwarded = []

    async def async_forward_entry_setups(self, entry, platforms) -> None:
        self.forwarded.append((entry.entry_id, list(platforms)))


class _DummyHass:
    def __init__(self) -> None:
        self.data = {}
        self.config_entries = _DummyConfigEntries()


class _DummyEntry:
    def __init__(self, options: dict) -> None:
        self.entry_id = "entry-1"
        self.data = {"email": "user@example.com", "password": "secret"}
        self.options = options


def test_async_setup_entry_uses_default_interval_and_refreshes_immediately(monkeypatch) -> None:
    hass = _DummyHass()
    entry = _DummyEntry({})

    async def _async_sync_asset_registries(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(MODULE, "_async_sync_asset_registries", _async_sync_asset_registries)
    MeterMacsCoordinator.instances.clear()

    result = asyncio.run(MODULE.async_setup_entry(hass, entry))

    assert result is True
    assert len(MeterMacsCoordinator.instances) == 1
    coordinator = MeterMacsCoordinator.instances[0]
    assert coordinator.update_interval.total_seconds() == 60
    assert coordinator.refresh_calls == 1
    assert hass.data[MODULE.DOMAIN][entry.entry_id]["coordinator"] is coordinator


def test_async_setup_entry_uses_minutes_option_override(monkeypatch) -> None:
    hass = _DummyHass()
    entry = _DummyEntry({"scan_interval_minutes": 5})

    async def _async_sync_asset_registries(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(MODULE, "_async_sync_asset_registries", _async_sync_asset_registries)
    MeterMacsCoordinator.instances.clear()

    asyncio.run(MODULE.async_setup_entry(hass, entry))

    assert MeterMacsCoordinator.instances[0].update_interval.total_seconds() == 300
