from __future__ import annotations

import json
from typing import Iterable


ENTITY_UNIQUE_ID_SUFFIXES: tuple[str, ...] = (
    "cost_per_kwh",
    "balance",
    "supply",
)

CONNECTED_SOCKET_STATES: frozenset[int] = frozenset({4, 7, 8})
POWERED_OFF_SOCKET_STATES: frozenset[int] = frozenset({0})
POWERED_ON_SOCKET_STATES: frozenset[int] = frozenset({4, 7, 8})


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


def parse_next_action_payload(response_text: str) -> dict:
    """Extract the first JSON data record from a Next.js server action response."""
    for line in response_text.splitlines():
        if not line.startswith("1:"):
            continue
        payload = line[2:]
        return json.loads(payload)
    raise ValueError("No action payload found in response")


def normalize_socket_state(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def socket_is_connected(socket_state: int | None, session_type: str | None = None) -> bool:
    if session_type == "current":
        return True
    if session_type == "previous":
        return False
    if socket_state in CONNECTED_SOCKET_STATES:
        return True
    return False


def infer_socket_power_state(socket_state: int | None, session_type: str | None = None) -> bool | None:
    """Infer whether the relay is currently powered on.

    Prefer an explicit off socket state when the portal reports one. Some live
    responses keep the session marked as current even after the relay has been
    switched off, while a previous session still means the asset is no longer
    actively powered even if a stale socket state lingers.
    """
    if socket_state in POWERED_OFF_SOCKET_STATES:
        return False
    if session_type == "previous":
        return False
    if socket_state in POWERED_ON_SOCKET_STATES:
        return True
    if session_type == "current":
        return True
    return None


def socket_is_powered_on(socket_state: int | None, session_type: str | None = None) -> bool:
    return infer_socket_power_state(socket_state, session_type) is True


def socket_location_from_values(
    site_name: str | None,
    area_name: str | None,
    socket_name: str | None,
) -> dict[str, str] | None:
    site = (site_name or "").strip()
    area = (area_name or "").strip()
    socket = (socket_name or "").strip()
    invalid_values = {"", "vacant", "none", "null"}
    if site.lower() in invalid_values or area.lower() in invalid_values or socket.lower() in invalid_values:
        return None
    return {
        "site": site,
        "area": area,
        "socket": socket,
    }
