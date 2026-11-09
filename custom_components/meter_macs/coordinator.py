from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import MeterMacsClient, MeterApi, parse_dashboard_for_meters, AuthError, Meter
from .const import DOMAIN
from .helpers import filter_meter_ids

_LOGGER = logging.getLogger(__name__)


class MeterMacsCoordinator(DataUpdateCoordinator[List[Meter]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: MeterMacsClient,
        update_interval: timedelta,
        selected_meter_ids: set[str] | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._client = client
        self._api = MeterApi(client)
        self._selected_meter_ids = selected_meter_ids
        self.all_meters: List[Meter] = []
        self.last_refresh_time: datetime | None = None
        self._last_readings: Dict[str, tuple[float, datetime | None]] = {}

    def _keep_last_reading(self, meters: List[Meter]) -> List[Meter]:
        """Hold the last real meter reading while the portal has no current session.

        Between sessions the portal reports the reading as 0 (or not at all).
        Passing that on makes a total_increasing sensor look like a meter reset,
        which adds the whole meter total to the Energy dashboard when the next
        real reading arrives.
        """
        kept: List[Meter] = []
        for meter in meters:
            reading = meter.imported_energy_kwh
            if reading is not None and reading > 0:
                self._last_readings[meter.meter_id] = (reading, meter.balance_reading_date)
            else:
                last = self._last_readings.get(meter.meter_id)
                meter = replace(
                    meter,
                    imported_energy_kwh=last[0] if last else None,
                    balance_reading_date=meter.balance_reading_date or (last[1] if last else None),
                )
            kept.append(meter)
        return kept

    async def _async_update_data(self) -> List[Meter]:
        try:
            # Prefer JSON API if available
            try:
                meters = await self._api.fetch_meters(self._selected_meter_ids)
            except AuthError:
                raise
            except Exception:
                # Fallback to HTML parsing if API is not available
                html = await self._client.fetch_dashboard()
                meters = parse_dashboard_for_meters(html)
            meters = self._keep_last_reading(meters)
            self.all_meters = meters
            if self._selected_meter_ids is not None:
                selected_ids = set(
                    filter_meter_ids(
                        (meter.meter_id for meter in meters),
                        self._selected_meter_ids,
                    )
                )
                meters = [meter for meter in meters if meter.meter_id in selected_ids]
            if not meters:
                _LOGGER.debug("No meters parsed from dashboard HTML")
            self.last_refresh_time = datetime.now(timezone.utc)
            return meters
        except AuthError as err:
            raise ConfigEntryAuthFailed from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
