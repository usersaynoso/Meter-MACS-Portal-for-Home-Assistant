# Meter MACS for Home Assistant

A custom Home Assistant integration for Meter MACS prepaid electricity accounts.

![Meter MACS logo](custom_components/meter_macs/brand/logo.png)

This integration signs in to the Meter MACS portal, discovers available sites and assets, and exposes meter data inside Home Assistant. It is designed for users who want their prepaid electricity balance, tariff information, and basic supply controls available in dashboards, automations, and notifications.

## Install With HACS

Until this repository is accepted into the default HACS list, install it as a custom integration repository:

1. Open HACS in Home Assistant.
2. Go to the custom repositories view.
3. Add `https://github.com/usersaynoso/Meter-MACS-Portal-for-Home-Assistant` as an `Integration` repository.
4. Refresh the repository list if HACS does not show it immediately.
5. Install `Meter MACS` from HACS.
6. Restart Home Assistant.
7. Go to `Settings -> Devices & Services -> Add Integration`.
8. Search for `Meter MACS`.
9. Enter your Meter MACS portal email address and password.

If HACS cached an older invalid version before these repository changes, remove the custom repository entry and add it again so HACS refreshes the metadata and available versions.

## What This Integration Does

- Authenticates against the Meter MACS portal with your existing portal credentials
- Discovers electricity meters from the account session API when available
- Falls back to dashboard HTML scraping if the JSON API is unavailable
- Creates Home Assistant entities for meter balance, balance update time, integration refresh time, and electricity cost per kWh
- Exposes an electricity supply switch when the required site and asset identifiers are available
- Groups each Meter MACS asset as its own Home Assistant device
- Lets you choose which discovered assets are enabled from the integration options
- Supports reauthentication through the normal Home Assistant config flow
- Provides integration diagnostics with redacted credentials

## Current Behavior

The integration currently uses a coordinator-based polling model.

Authentication flow:
- It first attempts JSON sign-in against `/api/auth/sign-in/email`
- If that path fails, it falls back to detecting and submitting an HTML login form
- After login, it tries to collect meter data from known Meter MACS API endpoints
- If API discovery fails, it attempts to parse meter data from the web dashboard HTML

Refresh behavior:
- Default refresh interval is 120 seconds
- The minimum allowed refresh interval is 30 seconds
- The refresh interval is configurable from the integration options dialog after setup
- Reloading the integration triggers an immediate refresh instead of waiting for the next timer

Asset selection behavior:
- Each discovered asset is registered as its own Home Assistant device
- The integration options dialog lets you choose which assets should remain enabled
- Asset labels include the Meter MACS asset identifier when available so duplicate names are easier to distinguish

## Entities Created

The integration currently registers sensor and switch platforms.

### Sensors

| Entity type | Example name | Notes |
| --- | --- | --- |
| Meter balance | `Meter MACS Home Balance` | Monetary sensor populated from the portal balance data |
| Balance updated | `Meter MACS Home Balance Updated` | Time-only sensor derived from the asset `readingDate` returned by the Meter MACS API |
| Last updated | `Meter MACS Home Last Updated` | Timestamp sensor showing when the integration last refreshed successfully |
| Electricity cost per kWh | `Meter MACS Home Electricity Cost Per kWh` | Derived from the portal tariff/session data with a 5% uplift applied in code |

Balance sensor attributes:
- `meter_id`
- `meter_name`
- `site_id`

Balance updated sensor attributes:
- `meter_id`
- `meter_name`
- `site_id`
- `reading_date`

Cost per kWh sensor attributes:
- `meter_id`
- `meter_name`
- `site_id`
- `uplift_applied`

### Switches

| Entity type | Example name | Notes |
| --- | --- | --- |
| Electricity supply switch | `Meter MACS Home Electricity Supply Switch` | Only created when the integration can resolve both `site_id` and `asset_id` |

Important switch limitation:
- The switch is currently optimistic. It writes the requested on/off state and reflects that locally, but it does not yet read back the true remote supply state from the portal after each change.

## Manual Installation

This repository is currently structured for manual installation.

1. Copy the [`custom_components/meter_macs`](custom_components/meter_macs) folder into your Home Assistant configuration directory under `custom_components/`.
2. The final path should look like `config/custom_components/meter_macs/`.
3. Restart Home Assistant.
4. Open `Settings -> Devices & Services`.
5. Select `Add Integration`.
6. Search for `Meter MACS`.
7. Enter your Meter MACS portal email address and password.

## Configuration

### Initial setup

The config flow asks for:
- `email`
- `password`

The integration uses the account email as the unique identifier, so the same account cannot be added multiple times through the UI.

### Options

After setup, open the integration and configure:
- `scan_interval_minutes`
- `selected_meters`

Validation rules:
- Minimum value: `1`
- Default value: `1`

## Diagnostics and Logging

The integration includes a Home Assistant diagnostics handler.

Current diagnostics output includes:
- Redacted email value
- Number of discovered meters
- A small sample of up to three detected meters

To troubleshoot login or parsing problems, enable debug logging for:

```yaml
logger:
  default: info
  logs:
    custom_components.meter_macs: debug
```

## Limitations and Caveats

- This integration depends on private portal endpoints and dashboard markup that are outside Home Assistant's control.
- If Meter MACS changes its authentication flow, field names, API responses, or dashboard structure, the integration may stop working until it is updated.
- CAPTCHA, MFA, or additional interactive login checks are not supported.
- Meter MACS is a UK service, and the integration is currently marked for `GB` in `hacs.json` for HACS publication.
- Balance currency is not always available from the JSON API path. In those cases Home Assistant may not show a unit for the balance sensor.
- The cost-per-kWh sensor currently reports `GBP/kWh` in code, even if the upstream account data is for a different region or currency.
- The cost-per-kWh value currently applies a fixed `5%` uplift in code.
- The electricity supply switch does not yet confirm the true remote state after a toggle request.
- This repository includes a small automated test suite for repository metadata and core parsing/control helpers.

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`custom_components/meter_macs/__init__.py`](custom_components/meter_macs/__init__.py) | Integration setup and config entry lifecycle |
| [`custom_components/meter_macs/config_flow.py`](custom_components/meter_macs/config_flow.py) | UI setup, reauthentication, and options flow |
| [`custom_components/meter_macs/api.py`](custom_components/meter_macs/api.py) | Portal login, API access, HTML fallback parsing, and supply control |
| [`custom_components/meter_macs/coordinator.py`](custom_components/meter_macs/coordinator.py) | Shared polling coordinator |
| [`custom_components/meter_macs/sensor.py`](custom_components/meter_macs/sensor.py) | Balance and cost-per-kWh sensors |
| [`custom_components/meter_macs/switch.py`](custom_components/meter_macs/switch.py) | Electricity supply switch entity |
| [`custom_components/meter_macs/diagnostics.py`](custom_components/meter_macs/diagnostics.py) | Home Assistant diagnostics payload |

## Development Notes

If you are modifying this integration:

- Keep compatibility with existing config entries and stored credentials
- Avoid destructive changes to authentication and entity unique IDs unless migration is planned
- Prefer adding tests when behavior changes beyond documentation or metadata updates
- Validate Python syntax before pushing changes
- Publish a GitHub release for each user-facing version so HACS can install a real version instead of falling back to a commit hash

## Source

- Repository: [usersaynoso/Meter-MACS-Portal-for-Home-Assistant](https://github.com/usersaynoso/Meter-MACS-Portal-for-Home-Assistant)
- Meter MACS portal: [portal.meter-macs.com](https://portal.meter-macs.com/dashboard)
