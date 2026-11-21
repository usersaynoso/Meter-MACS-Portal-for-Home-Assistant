from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_SELECTED_METERS,
    CONF_SESSION_TOKEN,
)
from .api import Meter, MeterApi, MeterMacsClient, AuthError, normalize_session_token
from .helpers import format_meter_display_name
from .intervals import (
    resolve_scan_interval_seconds,
    scan_interval_seconds_to_minutes,
    validate_scan_interval_minutes,
)

_LOGGER = logging.getLogger(__name__)


def _validate_interval(value: int) -> int:
    try:
        return validate_scan_interval_minutes(value)
    except ValueError as err:
        raise vol.Invalid(str(err)) from err


class MeterMacsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _async_check_session(self, raw_token: str) -> tuple[Optional[MeterMacsClient], Dict[str, str]]:
        errors: Dict[str, str] = {}
        token = normalize_session_token(raw_token)
        if not token:
            return None, {"base": "invalid_session"}
        session = async_get_clientsession(self.hass)
        client = MeterMacsClient(session=session, session_token=token)
        try:
            await client.ensure_logged_in()
        except AuthError:
            errors["base"] = "invalid_session"
        except Exception:  # noqa: BLE001
            errors["base"] = "cannot_connect"
        return (None if errors else client), errors

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is not None:
            client, errors = await self._async_check_session(user_input.get(CONF_SESSION_TOKEN, ""))
            if client is not None:
                email = client.user_email or ""
                # Email is the unique id, the same as entries made before sessions were used.
                await self.async_set_unique_id(email or None)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Meter MACS",
                    data={"email": email, CONF_SESSION_TOKEN: client.session_token},
                )

        data_schema = vol.Schema({
            vol.Required(CONF_SESSION_TOKEN): str,
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}
        current = self._get_reauth_entry()
        expected_email = (current.data.get("email") or "") if isinstance(current, ConfigEntry) else ""

        if user_input is not None:
            client, errors = await self._async_check_session(user_input.get(CONF_SESSION_TOKEN, ""))
            if client is not None:
                email = client.user_email or expected_email
                if expected_email and email and email.lower() != expected_email.lower():
                    errors["base"] = "wrong_account"
                elif isinstance(current, ConfigEntry):
                    # Drop any password saved by older versions; it can no longer be used.
                    new_data = {"email": email, CONF_SESSION_TOKEN: client.session_token}
                    self.hass.config_entries.async_update_entry(current, data=new_data)
                    await self.hass.config_entries.async_reload(current.entry_id)
                    return self.async_abort(reason="reauth_successful")
                else:
                    return self.async_abort(reason="reauth_successful")

        data_schema = vol.Schema({
            vol.Required(CONF_SESSION_TOKEN): str,
        })
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"email": expected_email or "your account"},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MeterMacsOptionsFlowHandler:
        return MeterMacsOptionsFlowHandler(config_entry)


class MeterMacsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}
        available_meters = await self._async_get_available_meters()
        meter_choices = {
            meter.meter_id: format_meter_display_name(
                meter.name,
                getattr(meter, "asset_id", None),
                getattr(meter, "site_id", None),
            )
            for meter in available_meters
        }
        current_selected_meters = self._config_entry.options.get(
            CONF_SELECTED_METERS,
            [meter.meter_id for meter in available_meters],
        )
        current_selected_meters = [
            meter_id for meter_id in current_selected_meters if meter_id in meter_choices
        ]

        if user_input is not None:
            try:
                minutes = _validate_interval(user_input[CONF_SCAN_INTERVAL_MINUTES])
            except vol.Invalid:
                errors["base"] = "invalid_interval"
            else:
                data = {CONF_SCAN_INTERVAL_MINUTES: minutes}
                if meter_choices:
                    data[CONF_SELECTED_METERS] = list(user_input.get(CONF_SELECTED_METERS, []))
                elif CONF_SELECTED_METERS in self._config_entry.options:
                    data[CONF_SELECTED_METERS] = list(
                        self._config_entry.options.get(CONF_SELECTED_METERS, [])
                    )
                return self.async_create_entry(title="Options", data=data)

        minutes = scan_interval_seconds_to_minutes(
            resolve_scan_interval_seconds(self._config_entry.options)
        )
        schema_dict: dict = {
            vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=minutes): int,
        }
        if meter_choices:
            schema_dict[
                vol.Optional(
                    CONF_SELECTED_METERS,
                    default=current_selected_meters,
                )
            ] = cv.multi_select(meter_choices)

        data_schema = vol.Schema(schema_dict)
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)

    async def _async_get_available_meters(self) -> list[Meter]:
        data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id, {})
        coordinator = data.get("coordinator")
        if coordinator and getattr(coordinator, "all_meters", None):
            return list(coordinator.all_meters)

        session = async_get_clientsession(self.hass)
        client = MeterMacsClient(
            session=session,
            session_token=self._config_entry.data.get(CONF_SESSION_TOKEN, ""),
        )
        api = MeterApi(client)
        try:
            return await api.fetch_meters()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Unable to fetch meters for options flow", exc_info=True)
            return []
