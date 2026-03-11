from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "custom_components" / "meter_macs" / "manifest.json"
HACS_PATH = REPO_ROOT / "hacs.json"
BRAND_DIR = REPO_ROOT / "custom_components" / "meter_macs" / "brand"


def test_hacs_json_exists_and_has_name() -> None:
    data = json.loads(HACS_PATH.read_text(encoding="utf-8"))

    assert data["name"] == "Meter MACS"


def test_manifest_has_github_metadata_and_real_codeowner() -> None:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert data["documentation"].startswith(
        "https://github.com/usersaynoso/Meter-MACS-Portal-for-Home-Assistant"
    )
    assert data["issue_tracker"].endswith("/issues")
    assert data["codeowners"] == ["@usersaynoso"]
    assert data["version"] == "0.1.2"


def test_local_brand_assets_exist() -> None:
    expected_files = {
        "icon.png",
        "dark_icon.png",
        "logo.png",
        "dark_logo.png",
    }

    assert BRAND_DIR.is_dir()
    assert expected_files.issubset({path.name for path in BRAND_DIR.iterdir()})
