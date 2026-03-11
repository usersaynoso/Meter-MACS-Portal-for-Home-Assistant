from __future__ import annotations

from typing import Iterable


ENTITY_UNIQUE_ID_SUFFIXES: tuple[str, ...] = (
    "cost_per_kwh",
    "balance",
    "supply",
)


def format_meter_display_name(
    name: str,
    asset_id: str | int | None = None,
    site_id: str | None = None,
) -> str:
    """Return a stable display name that distinguishes duplicate asset names."""
    detail = str(asset_id) if asset_id is not None else site_id
    if not detail:
        return name
    return f"{name} ({detail})"


def build_meter_device_key(entry_id: str, meter_id: str) -> str:
    return f"{entry_id}_{meter_id}"


def extract_meter_id_from_unique_id(entry_id: str, unique_id: str) -> str | None:
    prefix = f"{entry_id}_"
    if not unique_id.startswith(prefix):
        return None

    remainder = unique_id[len(prefix) :]
    for suffix in ENTITY_UNIQUE_ID_SUFFIXES:
        token = f"_{suffix}"
        if remainder.endswith(token):
            meter_id = remainder[: -len(token)]
            return meter_id or None
    return None


def selected_meter_ids_from_options(options: dict) -> set[str] | None:
    if "selected_meters" not in options:
        return None
    return {str(value) for value in options.get("selected_meters", [])}


def filter_meter_ids(
    meter_ids: Iterable[str],
    selected_meter_ids: set[str] | None,
) -> list[str]:
    if selected_meter_ids is None:
        return list(meter_ids)
    return [meter_id for meter_id in meter_ids if meter_id in selected_meter_ids]
