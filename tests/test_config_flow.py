from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "meter_macs"


def _install_homeassistant_stubs() -> None:
    voluptuous = sys.modules.setdefault("voluptuous", types.ModuleType("voluptuous"))
    if not hasattr(voluptuous, "Invalid"):
        class Invalid(Exception):
            pass

        class Schema:
            def __init__(self, schema) -> None:
                self.schema = schema

        voluptuous.Invalid = Invalid
        voluptuous.Schema = Schema
        voluptuous.Required = lambda key, default=None: key
        voluptuous.Optional = lambda key, default=None: key

    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    if not hasattr(homeassistant, "__path__"):
        homeassistant.__path__ = []

    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries",
        types.ModuleType("homeassistant.config_entries"),
    )
    if not hasattr(config_entries, "ConfigEntry"):
        class ConfigEntry:
            def __init__(self, data=None, options=None, entry_id: str = "entry-1") -> None:
                self.data = data or {}
                self.options = options or {}
                self.entry_id = entry_id

        class ConfigFlow:
            def __init_subclass__(cls, **kwargs):
                return super().__init_subclass__()

        class OptionsFlow:
            def __init__(self) -> None:
                self.hass = None

            @property
            def config_entry(self):
                return getattr(self, "_config_entry", None)

        config_entries.ConfigEntry = ConfigEntry
        config_entries.ConfigFlow = ConfigFlow
        config_entries.OptionsFlow = OptionsFlow

    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    if not hasattr(core, "HomeAssistant"):
        class HomeAssistant:
            pass

        def callback(func):
            return func

        core.HomeAssistant = HomeAssistant
        core.callback = callback

    data_entry_flow = sys.modules.setdefault(
        "homeassistant.data_entry_flow",
        types.ModuleType("homeassistant.data_entry_flow"),
    )
    if not hasattr(data_entry_flow, "FlowResult"):
        data_entry_flow.FlowResult = dict

    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    if not hasattr(helpers, "__path__"):
        helpers.__path__ = []

    aiohttp_client = sys.modules.setdefault(
        "homeassistant.helpers.aiohttp_client",
        types.ModuleType("homeassistant.helpers.aiohttp_client"),
    )
    if not hasattr(aiohttp_client, "async_get_clientsession"):
        aiohttp_client.async_get_clientsession = lambda hass: object()

    config_validation = sys.modules.setdefault(
        "homeassistant.helpers.config_validation",
        types.ModuleType("homeassistant.helpers.config_validation"),
    )
    if not hasattr(config_validation, "multi_select"):
        config_validation.multi_select = lambda choices: choices


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

    api_module = sys.modules.setdefault(
        "custom_components.meter_macs.api",
        types.ModuleType("custom_components.meter_macs.api"),
    )
    if not hasattr(api_module, "AuthError"):
        class AuthError(Exception):
            pass

        class Meter:
            def __init__(self, meter_id: str = "m1", name: str = "Meter") -> None:
                self.meter_id = meter_id
                self.name = name

        class MeterApi:
            def __init__(self, client) -> None:
                self.client = client

            async def fetch_meters(self):
                return []

        class MeterMacsClient:
            def __init__(self, session, email: str, password: str) -> None:
                self.session = session
                self.email = email
                self.password = password

            async def ensure_logged_in(self) -> None:
                return None

        api_module.AuthError = AuthError
        api_module.Meter = Meter
        api_module.MeterApi = MeterApi
        api_module.MeterMacsClient = MeterMacsClient

    full_name = f"custom_components.meter_macs.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, PACKAGE_ROOT / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


CONFIG_FLOW = _load_module("config_flow")
ConfigEntry = sys.modules["homeassistant.config_entries"].ConfigEntry


def test_config_flow_registers_options_flow() -> None:
    entry = ConfigEntry(data={"email": "user@example.com", "password": "secret"}, options={})

    options_flow = CONFIG_FLOW.MeterMacsConfigFlow.async_get_options_flow(entry)

    assert isinstance(options_flow, CONFIG_FLOW.MeterMacsOptionsFlowHandler)
    assert options_flow.config_entry is entry
