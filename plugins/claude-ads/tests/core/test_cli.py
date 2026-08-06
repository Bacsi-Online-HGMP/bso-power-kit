from __future__ import annotations

import json
from pathlib import Path

from claude_ads_core.cli import main
from tests.core.test_contracts import account_snapshot, report_bundle


def write_json(tmp_path, name: str, payload) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_validate_command_emits_machine_readable_success(tmp_path, capsys):
    path = write_json(tmp_path, "snapshot.json", account_snapshot())
    assert main(["validate", "account-snapshot", path]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"contract": "account-snapshot", "path": path, "status": "valid"}


def test_validate_command_returns_two_and_json_error(tmp_path, capsys):
    path = write_json(tmp_path, "snapshot.json", {"schema_version": "1.0.0"})
    assert main(["validate", "account-snapshot", path]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["status"] == "invalid"
    assert "missing required" in error["error"]


def test_status_command_reports_bundle_status(tmp_path, capsys):
    path = write_json(tmp_path, "report.json", report_bundle())
    assert main(["status", path]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "run_id": "run-20260711-001",
        "completeness": "complete",
        "health_score": 100.0,
        "evidence_coverage": 100.0,
        "status": "normal",
    }


def test_score_command_uses_json_inputs(tmp_path, capsys):
    from tests.core.test_scoring_engine import control, finding

    controls = write_json(tmp_path, "controls.json", [control("C-1", "tracking", "critical")])
    findings = write_json(tmp_path, "findings.json", [finding("C-1", "pass")])
    weights = write_json(tmp_path, "weights.json", {"tracking": 100})
    assert main(["score", "--controls", controls, "--findings", findings, "--weights", weights]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["health_score"] == 100.0
    assert output["status"] == "normal"


def test_ingest_export_command_emits_normalized_snapshot(capsys):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "exports" / "google.csv"
    assert main(["ingest-export", "--platform", "google", str(fixture)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "1.0.0"
    assert output["account"]["platform"] == "google"
    assert output["spend"] == 42.5
