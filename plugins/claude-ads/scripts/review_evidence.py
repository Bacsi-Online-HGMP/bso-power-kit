#!/usr/bin/env python3
"""Verify external, independently signed Claude Ads release-review evidence."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - verification fails closed below
    InvalidSignature = ValueError  # type: ignore[assignment,misc]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]


REPOSITORY = "https://github.com/AI-Marketing-Hub/claude-ads"
REVIEW_TYPES = {"code", "evidence", "security", "privacy", "licensing"}
SEVERITIES = {"critical", "high", "medium", "low", "informational"}
EVIDENCE_KINDS = {
    "ci-run",
    "command-output",
    "diff",
    "document",
    "issue",
    "pull-request",
    "report",
    "source-ledger",
    "test-artifact",
}
REVIEW_MAX_BYTES = 1024 * 1024
REVIEW_MAX_FILES = 100
TRUST_BUNDLE_MAX_BYTES = 256 * 1024


class ReviewEvidenceError(RuntimeError):
    """Independent review evidence failed closed."""


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ReviewEvidenceError(f"{label} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewEvidenceError(f"{label} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReviewEvidenceError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _decode_b64url(value: Any, label: str, expected_length: int) -> bytes:
    if not isinstance(value, str) or not value:
        raise ReviewEvidenceError(f"{label} must be base64url text")
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (TypeError, ValueError) as exc:
        raise ReviewEvidenceError(f"{label} is not valid base64url") from exc
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if canonical != value.rstrip("=") or len(decoded) != expected_length:
        raise ReviewEvidenceError(f"{label} is not canonical or has the wrong length")
    return decoded


def _canonical_review_payload(document: dict[str, Any]) -> bytes:
    authenticated = json.loads(json.dumps(document))
    authentication = authenticated.get("authentication")
    if not isinstance(authentication, dict):
        raise ReviewEvidenceError("review authentication must be an object")
    authentication.pop("signature_b64url", None)
    return json.dumps(
        authenticated,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _read_regular_file(path: Path, maximum_bytes: int, label: str) -> bytes:
    if path.is_symlink():
        raise ReviewEvidenceError(f"{label} must not be a symlink: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ReviewEvidenceError(f"cannot open {label}: {path.name}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ReviewEvidenceError(f"{label} must be a regular file: {path.name}")
        if metadata.st_size > maximum_bytes:
            raise ReviewEvidenceError(f"{label} is too large: {path.name}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(maximum_bytes + 1)
        if len(data) > maximum_bytes:
            raise ReviewEvidenceError(f"{label} is too large: {path.name}")
        return data
    finally:
        os.close(descriptor)


def _load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewEvidenceError(f"{label} must be valid UTF-8 JSON") from exc


def _git(root: Path, expression: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", expression],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        raise ReviewEvidenceError(f"cannot resolve release subject {expression}")
    value = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ReviewEvidenceError(f"release subject {expression} is not a full Git object ID")
    return value


def _load_policy(root: Path) -> dict[str, Any]:
    path = root / "control-plane" / "manifests" / "review-policy.json"
    document = _load_json_bytes(_read_regular_file(path, REVIEW_MAX_BYTES, "review policy"), "review policy")
    if not isinstance(document, dict):
        raise ReviewEvidenceError("review policy must be an object")
    expected = {
        "schema_version",
        "subject_repository",
        "required_review_types",
        "required_decision",
        "subject_binding",
        "authentication",
        "independence",
        "freshness",
        "findings",
        "templates_are_evidence",
    }
    if set(document) != expected:
        raise ReviewEvidenceError("review policy fields do not match the v1 contract")
    if (
        document["schema_version"] != "1.0.0"
        or document["subject_repository"] != REPOSITORY
        or set(document["required_review_types"]) != REVIEW_TYPES
        or document["required_decision"] != "approved"
        or document["templates_are_evidence"] is not False
    ):
        raise ReviewEvidenceError("review policy weakens the required release contract")
    if document["subject_binding"] != {
        "require_exact_commit_sha": True,
        "require_exact_tree_sha": True,
    }:
        raise ReviewEvidenceError("review policy must bind the exact commit and tree")
    authentication = document["authentication"]
    if authentication != {
        "algorithm": "ed25519",
        "trust_keys_environment": "CLAUDE_ADS_REVIEW_TRUST_KEYS_JSON",
        "allow_repository_local_trust_keys": False,
        "bind_key_to_reviewer_id_and_review_types": True,
    }:
        raise ReviewEvidenceError("review policy must use external reviewer-bound Ed25519 keys")
    independence = document["independence"]
    if (
        not isinstance(independence, dict)
        or independence.get("minimum_distinct_reviewer_ids", 0) < 2
        or independence.get("implementation_principal_environment")
        != "CLAUDE_ADS_IMPLEMENTATION_PRINCIPALS_JSON"
        or independence.get("implementation_principals_may_not_review") is not True
    ):
        raise ReviewEvidenceError("review policy independence requirements are too weak")
    freshness = document["freshness"]
    maximum_age_days = freshness.get("maximum_age_days") if isinstance(freshness, dict) else None
    if not isinstance(maximum_age_days, int) or not 1 <= maximum_age_days <= 30:
        raise ReviewEvidenceError("review policy freshness is invalid")
    findings = document["findings"]
    if (
        not isinstance(findings, dict)
        or set(findings.get("forbid_open_severities", [])) != {"critical", "high"}
        or findings.get("accepted_risk_requires_owner_gate") is not True
    ):
        raise ReviewEvidenceError("review policy finding requirements are too weak")
    return document


def _load_trust_bundle(raw_json: str | None) -> dict[str, dict[str, Any]]:
    if not raw_json:
        raise ReviewEvidenceError("external review trust bundle is required")
    if len(raw_json.encode("utf-8")) > TRUST_BUNDLE_MAX_BYTES:
        raise ReviewEvidenceError("external review trust bundle is too large")
    document = _load_json_bytes(raw_json.encode("utf-8"), "review trust bundle")
    if not isinstance(document, dict) or set(document) != {"schema_version", "keys"}:
        raise ReviewEvidenceError("review trust bundle fields are invalid")
    if (
        document["schema_version"] != "1.0.0"
        or not isinstance(document["keys"], list)
        or not 1 <= len(document["keys"]) <= 100
    ):
        raise ReviewEvidenceError("review trust bundle version or keys are invalid")
    keys: dict[str, dict[str, Any]] = {}
    for entry in document["keys"]:
        expected = {
            "key_id",
            "public_key_b64url",
            "reviewer_id",
            "allowed_review_types",
            "valid_from",
            "valid_until",
            "revoked",
        }
        if not isinstance(entry, dict) or set(entry) != expected:
            raise ReviewEvidenceError("review trust key fields are invalid")
        key_id = entry["key_id"]
        reviewer_id = entry["reviewer_id"]
        allowed = entry["allowed_review_types"]
        if (
            not isinstance(key_id, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", key_id)
            or not isinstance(reviewer_id, str)
            or len(reviewer_id) < 3
            or not isinstance(allowed, list)
            or not allowed
            or not set(allowed) <= REVIEW_TYPES
            or len(set(allowed)) != len(allowed)
            or not isinstance(entry["revoked"], bool)
        ):
            raise ReviewEvidenceError("review trust key identity or scope is invalid")
        if key_id in keys:
            raise ReviewEvidenceError(f"duplicate review trust key: {key_id}")
        entry = dict(entry)
        entry["public_key"] = _decode_b64url(
            entry["public_key_b64url"],
            f"review public key {key_id}",
            32,
        )
        entry["valid_from_parsed"] = _parse_utc(entry["valid_from"], f"{key_id}.valid_from")
        entry["valid_until_parsed"] = _parse_utc(entry["valid_until"], f"{key_id}.valid_until")
        if entry["valid_from_parsed"] >= entry["valid_until_parsed"]:
            raise ReviewEvidenceError(f"review trust key validity is inconsistent: {key_id}")
        keys[key_id] = entry
    if not keys:
        raise ReviewEvidenceError("review trust bundle has no keys")
    return keys


def _load_implementation_principals(raw_json: str | None) -> set[str]:
    if not raw_json:
        raise ReviewEvidenceError("external implementation-principal list is required")
    document = _load_json_bytes(raw_json.encode("utf-8"), "implementation-principal list")
    if (
        not isinstance(document, list)
        or not document
        or len(document) > 1000
        or any(not isinstance(value, str) or len(value) < 3 for value in document)
        or len(set(document)) != len(document)
    ):
        raise ReviewEvidenceError("implementation-principal list must be a unique non-empty array")
    return set(document)


def _validate_review_document(
    document: Any,
    *,
    filename: str,
    commit_sha: str,
    tree_sha: str,
    trust_keys: dict[str, dict[str, Any]],
    implementation_principals: set[str],
    policy: dict[str, Any],
    now: datetime,
) -> dict[str, str]:
    expected = {
        "schema_version",
        "review_id",
        "review_type",
        "subject",
        "reviewer",
        "reviewed_at",
        "decision",
        "evidence_refs",
        "findings",
        "authentication",
    }
    if not isinstance(document, dict) or set(document) != expected:
        raise ReviewEvidenceError(f"review fields are invalid: {filename}")
    review_id = document["review_id"]
    review_type = document["review_type"]
    if (
        document["schema_version"] != "1.0.0"
        or not isinstance(review_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{2,127}", review_id)
        or review_id.startswith("TEMPLATE-")
        or review_type not in REVIEW_TYPES
        or document["decision"] != "approved"
    ):
        raise ReviewEvidenceError(f"review is not an approvable v1 document: {filename}")
    if document["subject"] != {
        "repository": REPOSITORY,
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
    }:
        raise ReviewEvidenceError(f"review does not bind the exact release subject: {filename}")

    reviewer = document["reviewer"]
    if not isinstance(reviewer, dict) or set(reviewer) != {
        "id",
        "independence_basis",
        "conflict_disclosure",
    }:
        raise ReviewEvidenceError(f"reviewer fields are invalid: {filename}")
    reviewer_id = reviewer["id"]
    if (
        not isinstance(reviewer_id, str)
        or len(reviewer_id) < 3
        or not isinstance(reviewer["independence_basis"], str)
        or len(reviewer["independence_basis"]) < 20
        or not isinstance(reviewer["conflict_disclosure"], str)
        or len(reviewer["conflict_disclosure"]) < 4
    ):
        raise ReviewEvidenceError(f"reviewer identity or independence is incomplete: {filename}")
    if reviewer_id in implementation_principals:
        raise ReviewEvidenceError(f"implementation principal cannot approve review: {reviewer_id}")

    reviewed_at = _parse_utc(document["reviewed_at"], f"{filename}.reviewed_at")
    maximum_age = timedelta(days=policy["freshness"]["maximum_age_days"])
    if reviewed_at > now + timedelta(minutes=5):
        raise ReviewEvidenceError(f"review timestamp is in the future: {filename}")
    if now - reviewed_at > maximum_age:
        raise ReviewEvidenceError(f"review evidence is stale: {filename}")

    evidence_refs = document["evidence_refs"]
    if (
        not isinstance(evidence_refs, list)
        or not evidence_refs
        or len(evidence_refs) > 100
    ):
        raise ReviewEvidenceError(f"review evidence references are incomplete: {filename}")
    for reference in evidence_refs:
        if not isinstance(reference, dict) or set(reference) != {"kind", "locator", "sha256"}:
            raise ReviewEvidenceError(f"review evidence reference fields are invalid: {filename}")
        if (
            reference["kind"] not in EVIDENCE_KINDS
            or not isinstance(reference["locator"], str)
            or not reference["locator"].strip()
            or (
                reference["sha256"] is not None
                and not (
                    isinstance(reference["sha256"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])
                )
            )
        ):
            raise ReviewEvidenceError(f"review evidence reference is invalid: {filename}")

    findings = document["findings"]
    if not isinstance(findings, list) or len(findings) > 500:
        raise ReviewEvidenceError(f"review findings are invalid: {filename}")
    finding_ids: set[str] = set()
    for finding in findings:
        required = {"id", "severity", "status", "title", "evidence_refs", "resolution"}
        if not isinstance(finding, dict) or set(finding) != required:
            raise ReviewEvidenceError(f"review finding fields are invalid: {filename}")
        finding_id = finding["id"]
        if (
            not isinstance(finding_id, str)
            or not re.fullmatch(r"[A-Z][A-Z0-9-]{2,63}", finding_id)
            or finding_id in finding_ids
            or finding["severity"] not in SEVERITIES
            or finding["status"] not in {"open", "resolved", "accepted-risk"}
            or not isinstance(finding["title"], str)
            or not 3 <= len(finding["title"]) <= 500
            or not isinstance(finding["evidence_refs"], list)
            or not finding["evidence_refs"]
            or any(
                not isinstance(index, int) or not 0 <= index < len(evidence_refs)
                for index in finding["evidence_refs"]
            )
        ):
            raise ReviewEvidenceError(f"review finding is invalid: {filename}")
        finding_ids.add(finding_id)
        if finding["status"] == "accepted-risk":
            raise ReviewEvidenceError(
                f"accepted-risk finding requires a separate owner gate: {finding_id}"
            )
        if finding["status"] == "open" and finding["severity"] in {"critical", "high"}:
            raise ReviewEvidenceError(f"open release-blocking finding: {finding_id}")
        if finding["status"] == "resolved" and (
            not isinstance(finding["resolution"], str) or not finding["resolution"].strip()
        ):
            raise ReviewEvidenceError(f"resolved finding lacks resolution: {finding_id}")
        if finding["resolution"] is not None and (
            not isinstance(finding["resolution"], str) or len(finding["resolution"]) > 2000
        ):
            raise ReviewEvidenceError(f"review finding resolution is invalid: {finding_id}")

    authentication = document["authentication"]
    if not isinstance(authentication, dict) or set(authentication) != {
        "algorithm",
        "key_id",
        "signature_b64url",
    }:
        raise ReviewEvidenceError(f"review authentication fields are invalid: {filename}")
    if authentication["algorithm"] != "ed25519":
        raise ReviewEvidenceError(f"review authentication algorithm is unsupported: {filename}")
    key_id = authentication["key_id"]
    key = trust_keys.get(key_id)
    if not key or key["revoked"]:
        raise ReviewEvidenceError(f"review key is absent or revoked: {key_id}")
    if key["reviewer_id"] != reviewer_id or review_type not in key["allowed_review_types"]:
        raise ReviewEvidenceError(f"review key is not authorized for reviewer and type: {key_id}")
    if not key["valid_from_parsed"] <= reviewed_at < key["valid_until_parsed"]:
        raise ReviewEvidenceError(f"review key was not valid at review time: {key_id}")
    if Ed25519PublicKey is None:
        raise ReviewEvidenceError("cryptography is required for Ed25519 review verification")
    signature = _decode_b64url(
        authentication["signature_b64url"],
        f"review signature {review_id}",
        64,
    )
    try:
        Ed25519PublicKey.from_public_bytes(key["public_key"]).verify(
            signature,
            _canonical_review_payload(document),
        )
    except (InvalidSignature, ValueError) as exc:
        raise ReviewEvidenceError(f"review signature verification failed: {review_id}") from exc
    return {
        "review_id": review_id,
        "review_type": review_type,
        "reviewer_id": reviewer_id,
        "key_id": key_id,
        "reviewed_at": _format_utc(reviewed_at),
    }


def verify_independent_reviews(
    root: str | os.PathLike[str],
    evidence_dir: str | os.PathLike[str],
    *,
    trust_bundle_json: str | None = None,
    implementation_principals_json: str | None = None,
    commit_sha: str | None = None,
    tree_sha: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify the complete external independent-review set for one Git tree."""
    repository_root = Path(root).resolve()
    raw_evidence_dir = Path(evidence_dir).expanduser()
    if raw_evidence_dir.is_symlink():
        raise ReviewEvidenceError("review evidence directory must not be a symlink")
    directory = raw_evidence_dir.resolve()
    try:
        directory.relative_to(repository_root)
    except ValueError:
        pass
    else:
        raise ReviewEvidenceError("review evidence must be outside the repository checkout")
    if not directory.is_dir():
        raise ReviewEvidenceError("external review evidence directory does not exist")

    policy = _load_policy(repository_root)
    trust_keys = _load_trust_bundle(
        trust_bundle_json or os.environ.get(policy["authentication"]["trust_keys_environment"])
    )
    implementation_principals = _load_implementation_principals(
        implementation_principals_json
        or os.environ.get(policy["independence"]["implementation_principal_environment"])
    )
    subject_commit = commit_sha or _git(repository_root, "HEAD")
    subject_tree = tree_sha or _git(repository_root, "HEAD^{tree}")
    if not re.fullmatch(r"[0-9a-f]{40}", subject_commit) or not re.fullmatch(
        r"[0-9a-f]{40}", subject_tree
    ):
        raise ReviewEvidenceError("release subject requires full lowercase Git object IDs")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    entries = sorted(directory.iterdir())
    if any(path.suffix != ".json" or not path.is_file() for path in entries):
        raise ReviewEvidenceError("external review evidence directory contains unexpected entries")
    files = entries
    if not files or len(files) > REVIEW_MAX_FILES:
        raise ReviewEvidenceError("external review evidence must contain 1-100 JSON files")
    verified: list[dict[str, str]] = []
    document_digests: list[dict[str, str]] = []
    seen_types: set[str] = set()
    seen_ids: set[str] = set()
    for path in files:
        raw = _read_regular_file(path, REVIEW_MAX_BYTES, "review evidence")
        document = _load_json_bytes(raw, f"review evidence {path.name}")
        item = _validate_review_document(
            document,
            filename=path.name,
            commit_sha=subject_commit,
            tree_sha=subject_tree,
            trust_keys=trust_keys,
            implementation_principals=implementation_principals,
            policy=policy,
            now=current,
        )
        if item["review_type"] in seen_types:
            raise ReviewEvidenceError(f"duplicate review type: {item['review_type']}")
        if item["review_id"] in seen_ids:
            raise ReviewEvidenceError(f"duplicate review ID: {item['review_id']}")
        seen_types.add(item["review_type"])
        seen_ids.add(item["review_id"])
        verified.append(item)
        document_digests.append(
            {"review_id": item["review_id"], "sha256": hashlib.sha256(raw).hexdigest()}
        )

    if seen_types != REVIEW_TYPES:
        missing = ", ".join(sorted(REVIEW_TYPES - seen_types))
        raise ReviewEvidenceError(f"required review types are missing: {missing}")
    reviewers = {item["reviewer_id"] for item in verified}
    if len(reviewers) < policy["independence"]["minimum_distinct_reviewer_ids"]:
        raise ReviewEvidenceError("independent review requires at least two distinct reviewers")

    return {
        "schema_version": "1.0.0",
        "satisfied": True,
        "evaluated_at": _format_utc(current),
        "subject": {
            "repository": REPOSITORY,
            "commit_sha": subject_commit,
            "tree_sha": subject_tree,
        },
        "reviewers": sorted(reviewers),
        "reviews": sorted(verified, key=lambda item: item["review_type"]),
        "evidence_documents": sorted(document_digests, key=lambda item: item["review_id"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--evidence-dir",
        default=os.environ.get("CLAUDE_ADS_REVIEW_EVIDENCE_DIR"),
        help="external directory containing signed review JSON documents",
    )
    parser.add_argument("--commit-sha")
    parser.add_argument("--tree-sha")
    args = parser.parse_args(argv)
    if not args.evidence_dir:
        print("review evidence error: external evidence directory is required", file=sys.stderr)
        return 1
    try:
        report = verify_independent_reviews(
            args.root,
            args.evidence_dir,
            commit_sha=args.commit_sha,
            tree_sha=args.tree_sha,
        )
    except (OSError, TypeError, ValueError, ReviewEvidenceError) as exc:
        print(f"review evidence error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
