---
name: running-meter-macs-tests
description: "How to run the Meter MACS test suite (no pytest on system Python, no uvx) and its known pre-existing failures"
metadata:
  node_type: memory
  type: project
  originSessionId: 3bb5ba6e-a9c8-45b3-a43d-ac3cb91da674
  modified: 2026-11-09T14:47:08.850Z
---

System Python 3.14 has no pytest and `uvx` is not installed. Tests stub Home Assistant themselves (no `homeassistant` package needed), so a throwaway venv is enough:

`python3 -m venv "$TMPDIR/mmvenv" && "$TMPDIR/mmvenv/bin/pip" -q install pytest aiohttp beautifulsoup4 voluptuous && "$TMPDIR/mmvenv/bin/python" -m pytest -q tests`

Baseline as of 2026-11-09 (v0.1.33): 64 pass, 3 fail - `test_diagnostics_include_auth_and_meter_debug_data_without_secrets`, `test_manifest_has_github_metadata_and_real_codeowner`, `test_hacs_submission_workflows_exist` (expects a `gh release edit ... --latest` line removed from release.yml). Compare against that list instead of stashing the tree to check whether a failure is new. If they get fixed, update this note.

Each test file installs its own HA stubs via `sys.modules.setdefault`; a new HA import in integration code (e.g. `homeassistant.helpers.device_registry.DeviceInfo`) needs a matching stub in test_sensor.py and test_switch.py.

Related: [[release-needs-prerelease-flag-cleared]]
