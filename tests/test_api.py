from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from enum import Enum


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "meter_macs"


def _load_module(module_name: str):
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    if not hasattr(homeassistant, "__path__"):
        homeassistant.__path__ = []
    ha_const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
    if not hasattr(ha_const, "Platform"):
        class Platform(str, Enum):
            SENSOR = "sensor"
            SWITCH = "switch"

        ha_const.Platform = Platform

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

MeterApi = API.MeterApi
SupplyActionError = API.SupplyActionError


class _DummyClient:
    def __init__(self) -> None:
        self._base_url = "https://portal.meter-macs.com"


def test_turn_on_treats_async_arrive_as_success(monkeypatch) -> None:
    api = MeterApi(_DummyClient())
    responses = iter(
        [
            {"data": {"success": False, "message": "Failed to arrive customer - socket is unplugged"}},
            {"type": "previous"},
            {"type": "current"},
        ]
    )

    async def fake_post_server_action(action_id: str, payload: list[dict]) -> dict:
        assert action_id == "407e0ac91d042bb320d46f439aaf2fc8d474cdba7d"
        assert payload[0]["siteId"] == "CRT_WM"
        assert payload[0]["assetId"] == 3378
        return next(responses)

    async def fake_fetch_asset_session(site_id: str, asset_id: str | int):
        assert site_id == "CRT_WM"
        assert asset_id == 3378
        return next(responses)

    async def fake_sleep(_: float) -> None:
        return None

    async def fake_fetch_current_socket_state(site_id: str, asset_id: str | int):
        assert site_id == "CRT_WM"
        assert asset_id == 3378
        return None

    monkeypatch.setattr(api, "_post_server_action", fake_post_server_action)
    monkeypatch.setattr(api, "fetch_asset_session", fake_fetch_asset_session)
    monkeypatch.setattr(api, "_fetch_current_socket_state", fake_fetch_current_socket_state)
    monkeypatch.setattr(API.asyncio, "sleep", fake_sleep)

    asyncio.run(
        api.set_supply_state(
            "CRT_WM",
            3378,
            "on",
            site_db_id="site_db",
            asset_name="The Architeuthis",
            socket_site="Blackwall Basin",
            socket_area="BWB Bollard 12",
            socket_location="1202",
        )
    )


def test_turn_on_still_raises_when_session_never_becomes_current(monkeypatch) -> None:
    api = MeterApi(_DummyClient())

    async def fake_post_server_action(action_id: str, payload: list[dict]) -> dict:
        return {"data": {"success": False, "message": "Failed to arrive customer - socket is unplugged"}}

    async def fake_fetch_asset_session(site_id: str, asset_id: str | int):
        return {"type": "previous"}

    async def fake_sleep(_: float) -> None:
        return None

    async def fake_fetch_current_socket_state(site_id: str, asset_id: str | int):
        assert site_id == "CRT_WM"
        assert asset_id == 3378
        return None

    monkeypatch.setattr(api, "_post_server_action", fake_post_server_action)
    monkeypatch.setattr(api, "fetch_asset_session", fake_fetch_asset_session)
    monkeypatch.setattr(api, "_fetch_current_socket_state", fake_fetch_current_socket_state)
    monkeypatch.setattr(API.asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(
            api.set_supply_state(
                "CRT_WM",
                3378,
                "on",
                site_db_id="site_db",
                asset_name="The Architeuthis",
                socket_site="Blackwall Basin",
                socket_area="BWB Bollard 12",
                socket_location="1202",
            )
        )
    except SupplyActionError as err:
        assert str(err) == "Failed to arrive customer - socket is unplugged"
    else:
        raise AssertionError("SupplyActionError was not raised")


def test_turn_off_uses_toggle_socket_instead_of_vacate(monkeypatch) -> None:
    api = MeterApi(_DummyClient())
    calls: list[tuple[str, list[dict], str]] = []

    async def fake_fetch_asset_session(site_id: str, asset_id: str | int):
        return {"type": "current", "socketState": 7}

    async def fake_post_server_action(action_id: str, payload: list[dict], *, content_type: str = "application/json") -> dict:
        calls.append((action_id, payload, content_type))
        return {"data": {"success": True}}

    monkeypatch.setattr(api, "fetch_asset_session", fake_fetch_asset_session)
    monkeypatch.setattr(api, "_post_server_action", fake_post_server_action)

    asyncio.run(
        api.set_supply_state(
            "CRT_WM",
            3378,
            "off",
            site_db_id="site_db",
            asset_name="The Architeuthis",
            socket_site="Blackwall Basin",
            socket_area="BWB Bollard 12",
            socket_location="1202",
        )
    )

    assert calls == [
        (
            "40331886541f8254292f6757c1b29bf9b2b98eb432",
            [
                {
                    "siteId": "CRT_WM",
                    "assetId": 3378,
                    "state": "off",
                },
                {
                    "client": "$T",
                    "meta": "$undefined",
                    "mutationKey": ["toggleSocket"],
                },
            ],
            "text/plain;charset=UTF-8",
        )
    ]


def test_turn_on_returns_without_request_when_asset_is_already_powered_on(monkeypatch) -> None:
    api = MeterApi(_DummyClient())
    calls: list[tuple[str, list[dict], str]] = []

    async def fake_fetch_asset_session(site_id: str, asset_id: str | int):
        return {"type": "current", "socketState": 7}

    async def fake_post_server_action(action_id: str, payload: list[dict], *, content_type: str = "application/json") -> dict:
        calls.append((action_id, payload, content_type))
        return {"data": {"success": True}}

    monkeypatch.setattr(api, "fetch_asset_session", fake_fetch_asset_session)
    monkeypatch.setattr(api, "_post_server_action", fake_post_server_action)

    asyncio.run(
        api.set_supply_state(
            "CRT_WM",
            3378,
            "on",
            site_db_id="site_db",
            asset_name="The Architeuthis",
            socket_site="Blackwall Basin",
            socket_area="BWB Bollard 12",
            socket_location="1202",
        )
    )

    assert calls == []
