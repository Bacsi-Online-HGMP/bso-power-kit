"""Fail-closed release checks for the repository and fork review ledger."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest


RELEASE_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "release.py"
SPEC = importlib.util.spec_from_file_location("claude_ads_repository_release_gate", RELEASE_SCRIPT)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release
SPEC.loader.exec_module(release)

ReleaseError = release.ReleaseError
check_repository_review_ledger = release._check_repository_review_ledger


def _contract_copy(tmp_path: Path, repo_root: Path) -> Path:
    root = tmp_path / "repo"
    (root / "control-plane" / "schemas").mkdir(parents=True)
    (root / "control-plane" / "manifests").mkdir(parents=True)
    shutil.copy2(
        repo_root / "control-plane/schemas/repository-review-ledger.schema.json",
        root / "control-plane/schemas/repository-review-ledger.schema.json",
    )
    shutil.copy2(
        repo_root / "control-plane/manifests/repository-review-ledger.json",
        root / "control-plane/manifests/repository-review-ledger.json",
    )
    return root


def _mutate(root: Path, operation) -> None:
    path = root / "control-plane/manifests/repository-review-ledger.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    operation(document)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_repository_review_gate_accepts_complete_clean_room_ledger(repo_root):
    evidence = check_repository_review_ledger(repo_root)
    assert evidence == {
        "repository_count": 33,
        "fork_count": 17,
        "paginated_fork_count": 1026,
        "external_repository_count": 16,
        "concept_count": 41,
        "adopted_concept_count": 7,
        "unlicensed_repository_count": 4,
        "tracker_item_count": 14,
        "critical_blocker_count": 0,
    }


def test_repository_review_gate_requires_schema_and_manifest(tmp_path: Path, repo_root):
    root = _contract_copy(tmp_path, repo_root)
    (root / "control-plane/schemas/repository-review-ledger.schema.json").unlink()
    with pytest.raises(ReleaseError, match="cannot read repository review schema"):
        check_repository_review_ledger(root)


def test_repository_review_gate_rejects_bad_fork_arithmetic(tmp_path: Path, repo_root):
    root = _contract_copy(tmp_path, repo_root)
    _mutate(root, lambda doc: doc["fork_survey"].__setitem__("ancestor_or_equal_count", 1008))
    with pytest.raises(ReleaseError, match="required complete census|arithmetic"):
        check_repository_review_ledger(root)


def test_repository_review_gate_rejects_missing_disposition(tmp_path: Path, repo_root):
    root = _contract_copy(tmp_path, repo_root)
    _mutate(root, lambda doc: doc["repositories"][0].pop("primary_disposition"))
    with pytest.raises(ReleaseError, match="violates schema fields"):
        check_repository_review_ledger(root)


def test_repository_review_gate_rejects_unlicensed_adoption(tmp_path: Path, repo_root):
    root = _contract_copy(tmp_path, repo_root)

    def adopt_unlicensed(document: dict) -> None:
        review = next(
            item for item in document["repositories"] if item["license_spdx"] == "NOASSERTION"
        )
        review["primary_disposition"] = "adopt"

    _mutate(root, adopt_unlicensed)
    with pytest.raises(ReleaseError, match="unlicensed repository is not fail-closed"):
        check_repository_review_ledger(root)


def test_repository_review_gate_rejects_incomplete_tracker_scope(tmp_path: Path, repo_root):
    root = _contract_copy(tmp_path, repo_root)
    _mutate(root, lambda doc: doc["tracker_scopes"][0]["item_ids"].pop())
    with pytest.raises(ReleaseError, match="scope arithmetic|complete 14-item review"):
        check_repository_review_ledger(root)


def test_repository_review_gate_rejects_open_critical_blocker(tmp_path: Path, repo_root):
    root = _contract_copy(tmp_path, repo_root)

    def add_blocker(document: dict) -> None:
        document["critical_blockers"].append(
            {
                "id": "REPO-BLK-001",
                "severity": "critical",
                "status": "open",
                "summary": "A critical repository review has no safe disposition.",
                "evidence_paths": [],
            }
        )

    _mutate(root, add_blocker)
    with pytest.raises(ReleaseError, match="critical repository review blockers remain open"):
        check_repository_review_ledger(root)


def test_repository_review_gate_rejects_resolved_blocker_without_evidence(
    tmp_path: Path, repo_root
):
    root = _contract_copy(tmp_path, repo_root)

    def add_blocker(document: dict) -> None:
        document["critical_blockers"].append(
            {
                "id": "REPO-BLK-001",
                "severity": "critical",
                "status": "resolved",
                "summary": "A critical repository review was resolved.",
                "evidence_paths": [],
            }
        )

    _mutate(root, add_blocker)
    with pytest.raises(ReleaseError, match="resolved repository blocker lacks evidence"):
        check_repository_review_ledger(root)


def test_repository_review_gate_rejects_blocker_evidence_path_escape(
    tmp_path: Path, repo_root
):
    root = _contract_copy(tmp_path, repo_root)
    (tmp_path / "outside.json").write_text("{}", encoding="utf-8")

    def add_blocker(document: dict) -> None:
        document["critical_blockers"].append(
            {
                "id": "REPO-BLK-001",
                "severity": "critical",
                "status": "resolved",
                "summary": "A critical repository review was resolved.",
                "evidence_paths": ["../outside.json"],
            }
        )

    _mutate(root, add_blocker)
    with pytest.raises(ReleaseError, match="evidence path is missing"):
        check_repository_review_ledger(root)
