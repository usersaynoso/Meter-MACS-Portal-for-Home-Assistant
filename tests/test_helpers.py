from __future__ import annotations

import importlib.util
from pathlib import Path


HELPERS_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "meter_macs"
    / "helpers.py"
)
SPEC = importlib.util.spec_from_file_location("meter_macs_helpers", HELPERS_PATH)
HELPERS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(HELPERS)

build_meter_device_key = HELPERS.build_meter_device_key
extract_meter_id_from_unique_id = HELPERS.extract_meter_id_from_unique_id
filter_meter_ids = HELPERS.filter_meter_ids
format_meter_display_name = HELPERS.format_meter_display_name
selected_meter_ids_from_options = HELPERS.selected_meter_ids_from_options


def test_format_meter_display_name_uses_asset_id_when_available() -> None:
    assert (
        format_meter_display_name("The Architeuthis", asset_id="CRT_WM_3378")
        == "The Architeuthis (CRT_WM_3378)"
    )


def test_format_meter_display_name_falls_back_to_site_id() -> None:
    assert format_meter_display_name("The Architeuthis", site_id="CRT") == "The Architeuthis (CRT)"


def test_build_meter_device_key_is_stable() -> None:
    assert build_meter_device_key("entry123", "CRT_WM_3378") == "entry123_CRT_WM_3378"


def test_extract_meter_id_from_unique_id_handles_all_entity_suffixes() -> None:
    assert (
        extract_meter_id_from_unique_id("entry123", "entry123_CRT_WM_3378_balance")
        == "CRT_WM_3378"
    )
    assert (
        extract_meter_id_from_unique_id("entry123", "entry123_CRT_WM_3378_cost_per_kwh")
        == "CRT_WM_3378"
    )
    assert (
        extract_meter_id_from_unique_id("entry123", "entry123_CRT_WM_3378_supply")
        == "CRT_WM_3378"
    )


def test_selected_meter_ids_from_options_distinguishes_all_vs_none() -> None:
    assert selected_meter_ids_from_options({}) is None
    assert selected_meter_ids_from_options({"selected_meters": []}) == set()
    assert selected_meter_ids_from_options({"selected_meters": ["A", "B"]}) == {"A", "B"}


def test_filter_meter_ids_respects_selection() -> None:
    meter_ids = ["A", "B", "C"]

    assert filter_meter_ids(meter_ids, None) == ["A", "B", "C"]
    assert filter_meter_ids(meter_ids, {"B"}) == ["B"]
    assert filter_meter_ids(meter_ids, set()) == []
