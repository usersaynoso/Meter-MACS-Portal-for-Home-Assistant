# Repository Instructions

- Before every `git commit` or `git push`, bump the integration version in `custom_components/meter_macs/manifest.json`.
- Use semantic versioning and default to a patch bump unless the change clearly requires a minor or major bump.
- Do not leave the repo in a state where code changes are committed or pushed without a matching manifest version bump.
- HACS does not treat a manifest bump or pushed tag by itself as a new downloadable version once the repo is using GitHub Releases. Publish a matching GitHub Release for the same `vX.Y.Z` tag every time, or HACS can keep showing the previous version.
- After pushing the commit and matching tag, verify the release is live by checking `https://api.github.com/repos/usersaynoso/Meter-MACS-Portal-for-Home-Assistant/releases/latest` and confirming its `tag_name` matches the manifest version.
