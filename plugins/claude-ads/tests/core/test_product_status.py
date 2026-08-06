from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from claude_ads_core.cli import main
from claude_ads_core.product_status import ProductStatusError, RELEASE_CHECK_IDS, evaluate_product_status


def _artifact_root(tmp_path: Path, repo_root: Path) -> Path:
    root = tmp_path / "repo"
    target = root / "control-plane" / "manifests"
    target.parent.mkdir(parents=True)
    shutil.copytree(repo_root / "control-plane" / "manifests", target)
    return root


def test_current_repository_status_has_one_declared_next_blocker(repo_root: Path):
    result = evaluate_product_status(repo_root, as_of=date(2026, 7, 11))
    assert result["maturity"]["current"] == "domain-integrated"
    assert result["evidence"]["stale_load_bearing_claims"] == []
    assert len(result["scoring_profiles"]["disabled"]) == 12
    assert result["next_blocker"]["kind"] == "maturity-blocker"
    assert result["next_blocker"]["id"] == "maturity-blocker-001"
    assert result["next_blocker"]["evidence_paths"] == [
        "control-plane/manifests/maturity-status.json"
    ]


def test_stale_load_bearing_claim_deterministically_overrides_declared_blocker(
    tmp_path: Path, repo_root: Path
):
    root = _artifact_root(tmp_path, repo_root)
    path = root / "control-plane" / "manifests" / "claim-ledger.json"
    claims = json.loads(path.read_text(encoding="utf-8"))
    claims["claims"][0]["refresh_due"] = "2026-07-10"
    path.write_text(json.dumps(claims), encoding="utf-8")
    result = evaluate_product_status(root, as_of=date(2026, 7, 11))
    assert result["next_blocker"]["kind"] == "stale-load-bearing-claim"
    assert result["next_blocker"]["id"] == claims["claims"][0]["id"]


def test_missing_required_maturity_input_fails_closed(tmp_path: Path, repo_root: Path):
    root = _artifact_root(tmp_path, repo_root)
    path = root / "control-plane" / "manifests" / "maturity-status.json"
    maturity = json.loads(path.read_text(encoding="utf-8"))
    maturity.pop("blockers")
    path.write_text(json.dumps(maturity), encoding="utf-8")
    with pytest.raises(ProductStatusError, match="unsupported or missing fields"):
        evaluate_product_status(root, as_of=date(2026, 7, 11))


def test_optional_release_gate_is_validated_and_summarized(tmp_path: Path, repo_root: Path):
    checks = [
        ({"id": check_id, "status": "fail", "error": "model evidence missing"}
         if check_id == "canonical-model-evaluation"
         else {"id": check_id, "status": "pass", "evidence": {}})
        for check_id in RELEASE_CHECK_IDS
    ]
    report = {
        "schema_version": "1.0.0",
        "evidence_class": "release-gate-assessment",
        "evaluated_at": "2026-07-11T00:00:00Z",
        "subject": {"commit_sha": "a" * 40, "tree_sha": "b" * 40},
        "checks": checks,
        "release_gate_satisfied": False,
    }
    path = tmp_path / "gate.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    result = evaluate_product_status(repo_root, as_of=date(2026, 7, 11), release_gate_path=path)
    assert result["release_gate"]["failed_checks"] == [
        {"id": "canonical-model-evaluation", "error": "model evidence missing"}
    ]
    assert result["release_gate"]["evidence_path"] == "external-release-gate-report"


def test_repository_status_and_next_cli_are_machine_readable(repo_root: Path, capsys):
    assert main(["status", "--root", str(repo_root), "--as-of", "2026-07-11"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["evidence_class"] == "repository-artifact-status"
    assert main(["next", "--root", str(repo_root), "--as-of", "2026-07-11"]) == 0
    next_output = json.loads(capsys.readouterr().out)
    assert set(next_output) == {"schema_version", "as_of", "selection_policy", "next_blocker"}
    assert next_output["next_blocker"] == status["next_blocker"]
