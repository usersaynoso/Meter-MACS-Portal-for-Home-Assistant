from __future__ import annotations

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

    components = sys.modules.setdefault(
        "homeassistant.components",
        types.ModuleType("homeassistant.components"),
    )
    if not hasattr(components, "__path__"):
        components.__path__ = []

    ha_switch = sys.modules.setdefault(
        "homeassistant.components.switch",
        types.ModuleType("homeassistant.components.switch"),
    )
    if not hasattr(ha_switch, "SwitchEntity"):
        class SwitchEntity:
            def async_write_ha_state(self) -> None:
                return None

        ha_switch.SwitchEntity = SwitchEntity

    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    if not hasattr(config_entries, "ConfigEntry"):
        class ConfigEntry:
            def __init__(self, entry_id: str) -> None:
                self.entry_id = entry_id

        config_entries.ConfigEntry = ConfigEntry

    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    if not hasattr(core, "HomeAssistant"):
        class HomeAssistant:
            pass

        core.HomeAssistant = HomeAssistant

    exceptions = sys.modules.setdefault(
        "homeassistant.exceptions",
        types.ModuleType("homeassistant.exceptions"),
    )
    if not hasattr(exceptions, "HomeAssistantError"):
        class HomeAssistantError(Exception):
            pass

        exceptions.HomeAssistantError = HomeAssistantError

    update_coordinator = sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator",
        types.ModuleType("homeassistant.helpers.update_coordinator"),
    )
    if not hasattr(update_coordinator, "CoordinatorEntity"):
        class CoordinatorEntity:
            def __init__(self, coordinator) -> None:
                self.coordinator = coordinator

            def __class_getitem__(cls, _item):
                return cls

        update_coordinator.CoordinatorEntity = CoordinatorEntity


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

    coordinator_module = sys.modules.setdefault(
        "custom_components.meter_macs.coordinator",
        types.ModuleType("custom_components.meter_macs.coordinator"),
    )
    if not hasattr(coordinator_module, "MeterMacsCoordinator"):
        class MeterMacsCoordinator:
            def __init__(self, data=None) -> None:
                self.data = data or []

            async def async_request_refresh(self) -> None:
                return None

        coordinator_module.MeterMacsCoordinator = MeterMacsCoordinator

    full_name = f"custom_components.meter_macs.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, PACKAGE_ROOT / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


API = _load_module("api")
SWITCH = _load_module("switch")

Meter = API.Meter
MeterMacsSupplySwitch = SWITCH.MeterMacsSupplySwitch


class _DummyEntry:
    def __init__(self, entry_id: str = "entry-1") -> None:
        self.entry_id = entry_id


class _DummyCoordinator:
    def __init__(self, data) -> None:
        self.data = data

    async def async_request_refresh(self) -> None:
        return None


class _DummyApi:
    async def set_supply_state(self, *args, **kwargs) -> None:
        return None


def test_supply_switch_keeps_last_known_on_state_when_refresh_omits_state_fields() -> None:
    initial_meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=12.34,
        currency="GBP",
        site_id="CRT_WM",
        asset_id=3378,
        socket_state=8,
        session_type="current",
    )
    coordinator = _DummyCoordinator([initial_meter])
    supply_switch = MeterMacsSupplySwitch(_DummyEntry(), coordinator, _DummyApi(), initial_meter)

    assert supply_switch.is_on is True

    coordinator.data = [
        Meter(
            meter_id="CRT_WM_3378",
            name="The Architeuthis",
            balance=12.34,
            currency="GBP",
            site_id="CRT_WM",
            asset_id=3378,
            socket_state=None,
            session_type=None,
        )
    ]

    assert supply_switch.is_on is True


def test_supply_switch_keeps_last_known_current_session_when_refresh_omits_state_fields() -> None:
    initial_meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=12.34,
        currency="GBP",
        site_id="CRT_WM",
        asset_id=3378,
        socket_state=None,
        session_type="current",
    )
    coordinator = _DummyCoordinator([initial_meter])
    supply_switch = MeterMacsSupplySwitch(_DummyEntry(), coordinator, _DummyApi(), initial_meter)

    assert supply_switch.is_on is True


def test_supply_switch_treats_current_session_socket_state_7_as_on() -> None:
    meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=12.34,
        currency="GBP",
        site_id="CRT_WM",
        asset_id=3378,
        socket_state=7,
        session_type="current",
    )
    coordinator = _DummyCoordinator([meter])
    supply_switch = MeterMacsSupplySwitch(_DummyEntry(), coordinator, _DummyApi(), meter)

    assert supply_switch.is_on is True

    coordinator.data = [
        Meter(
            meter_id="CRT_WM_3378",
            name="The Architeuthis",
            balance=12.34,
            currency="GBP",
            site_id="CRT_WM",
            asset_id=3378,
            socket_state=None,
            session_type=None,
        )
    ]

    assert supply_switch.is_on is True


def test_supply_switch_explicit_off_state_overrides_stale_assumed_on() -> None:
    initial_meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=12.34,
        currency="GBP",
        site_id="CRT_WM",
        asset_id=3378,
        socket_state=7,
        session_type="current",
    )
    coordinator = _DummyCoordinator([initial_meter])
    supply_switch = MeterMacsSupplySwitch(_DummyEntry(), coordinator, _DummyApi(), initial_meter)
    supply_switch._assumed_on = True

    coordinator.data = [
        Meter(
            meter_id="CRT_WM_3378",
            name="The Architeuthis",
            balance=12.34,
            currency="GBP",
            site_id="CRT_WM",
            asset_id=3378,
            socket_state=0,
            session_type="current",
        )
    ]

    assert supply_switch.is_on is False
