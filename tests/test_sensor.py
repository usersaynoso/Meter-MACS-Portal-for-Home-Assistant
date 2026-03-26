from __future__ import annotations

import asyncio
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

    ha_sensor = sys.modules.setdefault(
        "homeassistant.components.sensor",
        types.ModuleType("homeassistant.components.sensor"),
    )
    if not hasattr(ha_sensor, "SensorEntity"):
        class SensorEntity:
            pass

        class SensorDeviceClass(str, Enum):
            MONETARY = "monetary"

        ha_sensor.SensorEntity = SensorEntity
        ha_sensor.SensorDeviceClass = SensorDeviceClass

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

        coordinator_module.MeterMacsCoordinator = MeterMacsCoordinator

    full_name = f"custom_components.meter_macs.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, PACKAGE_ROOT / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


API = _load_module("api")
SENSOR = _load_module("sensor")

Meter = API.Meter
MeterMacsSafetyTrippedSensor = SENSOR.MeterMacsSafetyTrippedSensor


class _DummyEntry:
    def __init__(self, entry_id: str = "entry-1") -> None:
        self.entry_id = entry_id


class _DummyCoordinator:
    def __init__(self, data) -> None:
        self.data = data


def test_async_setup_entry_adds_safety_tripped_sensor() -> None:
    meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=12.34,
        currency="GBP",
        site_id="CRT_WM",
        asset_id=3378,
        socket_state=1,
    )
    coordinator = _DummyCoordinator([meter])
    entry = _DummyEntry()
    hass = types.SimpleNamespace(
        data={
            SENSOR.DOMAIN: {
                entry.entry_id: {
                    "coordinator": coordinator,
                }
            }
        }
    )
    added_entities = []

    def _async_add_entities(entities) -> None:
        added_entities.extend(entities)

    asyncio.run(SENSOR.async_setup_entry(hass, entry, _async_add_entities))

    assert len(added_entities) == 3
    assert any(isinstance(entity, MeterMacsSafetyTrippedSensor) for entity in added_entities)


def test_safety_tripped_sensor_reports_yes_for_socket_state_1() -> None:
    meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=12.34,
        currency="GBP",
        site_id="CRT_WM",
        asset_id=3378,
        socket_state=1,
        session_type="current",
    )
    coordinator = _DummyCoordinator([meter])
    sensor = MeterMacsSafetyTrippedSensor(_DummyEntry(), coordinator, meter)

    assert sensor.native_value == "yes"
    assert sensor.extra_state_attributes["socket_state"] == 1


def test_safety_tripped_sensor_reports_no_for_other_socket_states() -> None:
    initial_meter = Meter(
        meter_id="CRT_WM_3378",
        name="The Architeuthis",
        balance=12.34,
        currency="GBP",
        site_id="CRT_WM",
        asset_id=3378,
        socket_state=1,
        session_type="current",
    )
    coordinator = _DummyCoordinator([initial_meter])
    sensor = MeterMacsSafetyTrippedSensor(_DummyEntry(), coordinator, initial_meter)

    assert sensor.native_value == "yes"

    coordinator.data = [
        Meter(
            meter_id="CRT_WM_3378",
            name="The Architeuthis",
            balance=12.34,
            currency="GBP",
            site_id="CRT_WM",
            asset_id=3378,
            socket_state=7,
            session_type="current",
        )
    ]

    assert sensor.native_value == "no"
