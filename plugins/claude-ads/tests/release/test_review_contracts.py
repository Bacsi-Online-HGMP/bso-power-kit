from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "control-plane" / "schemas"
MANIFEST_DIR = ROOT / "control-plane" / "manifests"
REVIEW_SCRIPT = ROOT / "scripts" / "review_evidence.py"
SPEC = importlib.util.spec_from_file_location("claude_ads_review_evidence", REVIEW_SCRIPT)
assert SPEC and SPEC.loader
review_evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = review_evidence
SPEC.loader.exec_module(review_evidence)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _review_document(
    review_type: str,
    reviewer_id: str,
    key_id: str,
    commit_sha: str,
    tree_sha: str,
    reviewed_at: datetime,
) -> dict:
    return {
        "schema_version": "1.0.0",
        "review_id": f"REV-{review_type.upper()}-001",
        "review_type": review_type,
        "subject": {
            "repository": "https://github.com/AI-Marketing-Hub/claude-ads",
            "commit_sha": commit_sha,
            "tree_sha": tree_sha,
        },
        "reviewer": {
            "id": reviewer_id,
            "independence_basis": "Independent fresh-context review with no implementation role.",
            "conflict_disclosure": "None",
        },
        "reviewed_at": reviewed_at.isoformat().replace("+00:00", "Z"),
        "decision": "approved",
        "evidence_refs": [
            {
                "kind": "test-artifact",
                "locator": f"artifact:{review_type}-review",
                "sha256": "a" * 64,
            }
        ],
        "findings": [],
        "authentication": {
            "algorithm": "ed25519",
            "key_id": key_id,
            "signature_b64url": "",
        },
    }


def _sign_review(document: dict, private_key: Ed25519PrivateKey) -> None:
    unsigned = json.loads(json.dumps(document))
    unsigned["authentication"].pop("signature_b64url")
    payload = json.dumps(
        unsigned,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    document["authentication"]["signature_b64url"] = _b64url(private_key.sign(payload))


def _external_review_set(tmp_path: Path) -> tuple[Path, str, str, str, str, datetime]:
    now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    commit_sha = "1" * 40
    tree_sha = "2" * 40
    directory = tmp_path / "external-reviews"
    directory.mkdir(parents=True)
    reviewers = {
        "reviewer:alpha": Ed25519PrivateKey.generate(),
        "reviewer:beta": Ed25519PrivateKey.generate(),
    }
    assignments = {
        "code": "reviewer:alpha",
        "evidence": "reviewer:alpha",
        "security": "reviewer:beta",
        "privacy": "reviewer:beta",
        "licensing": "reviewer:beta",
    }
    keys = []
    for index, (reviewer_id, private_key) in enumerate(reviewers.items(), 1):
        key_id = f"review-key-{index}"
        allowed = [kind for kind, assigned in assignments.items() if assigned == reviewer_id]
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        keys.append(
            {
                "key_id": key_id,
                "public_key_b64url": _b64url(public_key),
                "reviewer_id": reviewer_id,
                "allowed_review_types": allowed,
                "valid_from": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "valid_until": (now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
                "revoked": False,
            }
        )
        for review_type in allowed:
            document = _review_document(
                review_type,
                reviewer_id,
                key_id,
                commit_sha,
                tree_sha,
                now - timedelta(hours=1),
            )
            _sign_review(document, private_key)
            (directory / f"{review_type}.json").write_text(
                json.dumps(document),
                encoding="utf-8",
            )
    trust_bundle = json.dumps({"schema_version": "1.0.0", "keys": keys})
    principals = json.dumps(["implementation:owner"])
    return directory, trust_bundle, principals, commit_sha, tree_sha, now


def test_review_policy_requires_external_asymmetric_independent_approval() -> None:
    policy = json.loads((MANIFEST_DIR / "review-policy.json").read_text(encoding="utf-8"))

    assert set(policy["required_review_types"]) == {
        "code",
        "evidence",
        "security",
        "privacy",
        "licensing",
    }
    assert policy["required_decision"] == "approved"
    assert policy["subject_binding"] == {
        "require_exact_commit_sha": True,
        "require_exact_tree_sha": True,
    }
    assert policy["authentication"]["algorithm"] == "ed25519"
    assert policy["authentication"]["allow_repository_local_trust_keys"] is False
    assert policy["authentication"]["bind_key_to_reviewer_id_and_review_types"] is True
    assert policy["independence"]["minimum_distinct_reviewer_ids"] >= 2
    assert policy["independence"]["implementation_principals_may_not_review"] is True
    assert set(policy["findings"]["forbid_open_severities"]) == {"critical", "high"}
    assert policy["templates_are_evidence"] is False


def test_review_templates_are_pending_unsigned_and_cannot_approve() -> None:
    templates = sorted((MANIFEST_DIR / "reviews").glob("*.review.template.json"))
    assert len(templates) == 5

    review_types = set()
    for path in templates:
        document = json.loads(path.read_text(encoding="utf-8"))
        review_types.add(document["review_type"])
        assert document["review_id"].startswith("TEMPLATE-")
        assert document["decision"] == "pending"
        assert document["authentication"] is None
        assert document["subject"]["commit_sha"] is None
        assert document["subject"]["tree_sha"] is None
        assert document["reviewer"]["id"] is None
        assert document["evidence_refs"] == []
        assert document["findings"] == []

    assert review_types == {"code", "evidence", "security", "privacy", "licensing"}


def test_review_and_egress_schemas_require_ed25519_signatures() -> None:
    review = json.loads(
        (SCHEMA_DIR / "independent-review-evidence.schema.json").read_text(encoding="utf-8")
    )
    review_authentication = review["properties"]["authentication"]["oneOf"][1]
    assert review_authentication["properties"]["algorithm"]["const"] == "ed25519"
    assert "signature_b64url" in review_authentication["required"]
    assert "private_key" not in json.dumps(review).casefold()

    egress = json.loads(
        (SCHEMA_DIR / "egress-sandbox-attestation.schema.json").read_text(encoding="utf-8")
    )
    egress_authentication = egress["properties"]["authentication"]
    assert egress_authentication["properties"]["algorithm"]["const"] == "ed25519"
    assert "signature_b64url" in egress_authentication["required"]
    assert "private_key" not in json.dumps(egress).casefold()


def test_external_review_verifier_accepts_complete_signed_independent_set(tmp_path) -> None:
    directory, trust, principals, commit_sha, tree_sha, now = _external_review_set(tmp_path)
    report = review_evidence.verify_independent_reviews(
        ROOT,
        directory,
        trust_bundle_json=trust,
        implementation_principals_json=principals,
        commit_sha=commit_sha,
        tree_sha=tree_sha,
        now=now,
    )

    assert report["satisfied"] is True
    assert report["subject"]["commit_sha"] == commit_sha
    assert report["subject"]["tree_sha"] == tree_sha
    assert {review["review_type"] for review in report["reviews"]} == {
        "code",
        "evidence",
        "security",
        "privacy",
        "licensing",
    }
    assert report["reviewers"] == ["reviewer:alpha", "reviewer:beta"]


def test_external_review_verifier_rejects_tampering_and_missing_type(tmp_path) -> None:
    directory, trust, principals, commit_sha, tree_sha, now = _external_review_set(tmp_path)
    security_path = directory / "security.json"
    security = json.loads(security_path.read_text(encoding="utf-8"))
    security["decision"] = "rejected"
    security_path.write_text(json.dumps(security), encoding="utf-8")
    with pytest.raises(review_evidence.ReviewEvidenceError, match="not an approvable"):
        review_evidence.verify_independent_reviews(
            ROOT,
            directory,
            trust_bundle_json=trust,
            implementation_principals_json=principals,
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            now=now,
        )

    directory, trust, principals, commit_sha, tree_sha, now = _external_review_set(
        tmp_path / "second"
    )
    (directory / "licensing.json").unlink()
    with pytest.raises(review_evidence.ReviewEvidenceError, match="required review types are missing"):
        review_evidence.verify_independent_reviews(
            ROOT,
            directory,
            trust_bundle_json=trust,
            implementation_principals_json=principals,
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            now=now,
        )


def test_external_review_verifier_rejects_self_review_and_repository_local_evidence(
    tmp_path,
) -> None:
    directory, trust, _, commit_sha, tree_sha, now = _external_review_set(tmp_path)
    principals = json.dumps(["implementation:owner", "reviewer:alpha"])
    with pytest.raises(review_evidence.ReviewEvidenceError, match="cannot approve"):
        review_evidence.verify_independent_reviews(
            ROOT,
            directory,
            trust_bundle_json=trust,
            implementation_principals_json=principals,
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            now=now,
        )

    with pytest.raises(review_evidence.ReviewEvidenceError, match="outside the repository"):
        review_evidence.verify_independent_reviews(
            ROOT,
            MANIFEST_DIR / "reviews",
            trust_bundle_json=trust,
            implementation_principals_json=json.dumps(["implementation:owner"]),
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            now=now,
        )


def test_external_review_verifier_rejects_open_blocker_and_accepted_risk(tmp_path) -> None:
    directory, trust, principals, commit_sha, tree_sha, now = _external_review_set(tmp_path)
    code_path = directory / "code.json"
    code = json.loads(code_path.read_text(encoding="utf-8"))
    code["findings"] = [
        {
            "id": "SEC-001",
            "severity": "critical",
            "status": "open",
            "title": "Critical release blocker",
            "evidence_refs": [0],
            "resolution": None,
        }
    ]
    # Re-signing proves that an authenticated reviewer still cannot approve an
    # open release blocker.
    alpha_key = Ed25519PrivateKey.generate()
    # The wrong signer is enough to fail closed, but the semantic blocker is
    # evaluated before signature verification and must be the reported cause.
    _sign_review(code, alpha_key)
    code_path.write_text(json.dumps(code), encoding="utf-8")
    with pytest.raises(review_evidence.ReviewEvidenceError, match="open release-blocking"):
        review_evidence.verify_independent_reviews(
            ROOT,
            directory,
            trust_bundle_json=trust,
            implementation_principals_json=principals,
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            now=now,
        )

    code["findings"][0]["severity"] = "low"
    code["findings"][0]["status"] = "accepted-risk"
    _sign_review(code, alpha_key)
    code_path.write_text(json.dumps(code), encoding="utf-8")
    with pytest.raises(review_evidence.ReviewEvidenceError, match="separate owner gate"):
        review_evidence.verify_independent_reviews(
            ROOT,
            directory,
            trust_bundle_json=trust,
            implementation_principals_json=principals,
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            now=now,
        )
