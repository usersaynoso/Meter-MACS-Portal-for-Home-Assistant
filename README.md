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
9. Paste your portal session cookie (see [Getting your portal session cookie](#getting-your-portal-session-cookie)).

If HACS cached an older invalid version before these repository changes, remove the custom repository entry and add it again so HACS refreshes the metadata and available versions.

## What This Integration Does

- Connects to the Meter MACS portal using a session you sign in to in your own browser
- Discovers electricity meters from the account session API when available
- Falls back to dashboard HTML scraping if the JSON API is unavailable
- Creates Home Assistant entities for meter balance, imported energy, balance update time, integration refresh time, and electricity cost per kWh
- Exposes an electricity supply switch when the required site and asset identifiers are available
- Groups each Meter MACS asset as its own Home Assistant device
- Lets you choose which discovered assets are enabled from the integration options
- Supports reauthentication through the normal Home Assistant config flow
- Provides integration diagnostics with redacted credentials

## Current Behavior

The integration currently uses a coordinator-based polling model.

Authentication flow:
- The portal's sign-in form is protected by Cloudflare Turnstile, so the integration does not sign in by itself and does not store your password
- You sign in in your browser and give the integration the portal session cookie
- The integration sends that cookie with each request and checks the session with `/api/auth/get-session` every few hours, which also stops the portal expiring an in-use session
- If the portal sends back a refreshed session cookie, it is saved automatically
- If the session stops working (expired, or you signed out of every device), Home Assistant shows a re-authenticate prompt asking for a fresh cookie
- With a working session, it collects meter data from known Meter MACS API endpoints
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
| Energy imported from grid | `Meter MACS Home Energy Imported From Grid` | Cumulative kWh reading derived from the portal `reading` / total-used data so Home Assistant Energy can use it |
| Balance updated | `Meter MACS Home Balance Updated` | Time-only sensor derived from the asset `readingDate` returned by the Meter MACS API |
| Last updated | `Meter MACS Home Last Updated` | Timestamp sensor showing when the integration last refreshed successfully |
| Electricity cost per kWh | `Meter MACS Home Electricity Cost Per kWh` | Derived from the portal tariff/session data using the VAT implied by the portal's incl/excl VAT cost fields (currently 0%) |

Balance sensor attributes:
- `meter_id`
- `meter_name`
- `site_id`

Energy imported from grid sensor attributes:
- `meter_id`
- `meter_name`
- `site_id`
- `reading_date`

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
7. Paste your portal session cookie (see [Getting your portal session cookie](#getting-your-portal-session-cookie)).

## Configuration

### Initial setup

The config flow asks for one thing: your portal session cookie. The integration reads your account email from the portal and uses it as the unique identifier, so the same account cannot be added twice.

### Getting your portal session cookie

1. Sign in at [portal.meter-macs.com](https://portal.meter-macs.com) in a desktop browser. Tick "remember me" if the form offers it.
2. Open the developer tools (`F12`, or `Cmd+Option+I` on a Mac).
3. Go to **Application -> Cookies** in Chrome or Edge, or **Storage -> Cookies** in Firefox and Safari, and select `https://portal.meter-macs.com`.
4. Find the cookie named `__Secure-meter-macs.session_token` and copy its value.
5. Paste it into Home Assistant.

You can also paste the whole cookie line or `name=value` pair; the integration picks out the session value. Signing out of the portal in that browser ends the session, so close the tab instead of signing out. If you added the integration before this change, Home Assistant asks you to re-authenticate once with a session cookie, and the old saved password is removed.

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
- Redacted account indicators, plus whether a session cookie or an old password is saved
- Integration version, selected meter options, and scan interval context
- Login/session status, including whether Meter MACS auth cookies are present
- Coordinator refresh times and the latest captured exception
- Current and discovered meter counts
- A small sample of detected meter data, including site/asset IDs, reading dates, socket state, and session type

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
- The integration cannot get past the portal's Cloudflare Turnstile check, so it never signs in by itself. When a session ends you need to paste a fresh cookie.
- Meter MACS is a UK service, and the integration is currently marked for `GB` in `hacs.json` for HACS publication.
- Balance currency is not always available from the JSON API path. In those cases Home Assistant may not show a unit for the balance sensor.
- The cost-per-kWh sensor currently reports `GBP/kWh` in code, even if the upstream account data is for a different region or currency.
- The cost-per-kWh value uses the VAT implied by the portal's incl/excl VAT cost fields, with no fixed uplift.
- The electricity supply switch does not yet confirm the true remote state after a toggle request.
- This repository includes a small automated test suite for repository metadata and core parsing/control helpers.

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`custom_components/meter_macs/__init__.py`](custom_components/meter_macs/__init__.py) | Integration setup and config entry lifecycle |
| [`custom_components/meter_macs/config_flow.py`](custom_components/meter_macs/config_flow.py) | UI setup, reauthentication, and options flow |
| [`custom_components/meter_macs/api.py`](custom_components/meter_macs/api.py) | Portal session handling, API access, HTML fallback parsing, and supply control |
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
