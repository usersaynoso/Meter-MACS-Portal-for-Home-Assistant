# Repository Instructions

- Before every `git commit` or `git push`, bump the integration version in `custom_components/meter_macs/manifest.json`.
- Use semantic versioning and default to a patch bump unless the change clearly requires a minor or major bump.
- Do not leave the repo in a state where code changes are committed or pushed without a matching manifest version bump.
- If the change is intended for HACS users, create a matching Git tag/release after the commit/push so Home Assistant can actually receive the new version.

