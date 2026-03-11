from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "custom_components" / "meter_macs" / "manifest.json"
HACS_PATH = REPO_ROOT / "hacs.json"
BRAND_DIR = REPO_ROOT / "custom_components" / "meter_macs" / "brand"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


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
    assert data["version"] == "0.1.3"


def test_local_brand_assets_exist() -> None:
    expected_files = {
        "icon.png",
        "dark_icon.png",
        "logo.png",
        "dark_logo.png",
    }

    assert BRAND_DIR.is_dir()
    assert expected_files.issubset({path.name for path in BRAND_DIR.iterdir()})


def test_hacs_submission_workflows_exist() -> None:
    validate_workflow = WORKFLOWS_DIR / "validate.yml"
    hassfest_workflow = WORKFLOWS_DIR / "hassfest.yml"

    assert validate_workflow.is_file()
    assert hassfest_workflow.is_file()
    assert "hacs/action@main" in validate_workflow.read_text(encoding="utf-8")
    assert "category: integration" in validate_workflow.read_text(encoding="utf-8")
    assert "home-assistant/actions/hassfest@master" in hassfest_workflow.read_text(
        encoding="utf-8"
    )
