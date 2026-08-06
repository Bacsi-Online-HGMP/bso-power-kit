"""External Ed25519 authentication for canonical model-evaluation evidence."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

TRUST_ENV = "CLAUDE_ADS_MODEL_EVAL_TRUST_BUNDLE_JSON"
PRINCIPALS_ENV = "CLAUDE_ADS_MODEL_EVAL_IMPLEMENTATION_PRINCIPALS_JSON"
MAX_AGE_DAYS = 14
ALLOWED_CLOCK_SKEW = timedelta(minutes=5)


class ModelEvidenceAuthError(ValueError):
    """Raised when external model-evidence authentication is invalid."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    import hashlib

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _timestamp(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ModelEvidenceAuthError(f"{path} must be an ISO 8601 date-time")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ModelEvidenceAuthError(f"{path} must be an ISO 8601 date-time") from exc
    if result.tzinfo is None:
        raise ModelEvidenceAuthError(f"{path} must include an offset")
    return result.astimezone(timezone.utc)


def _b64url(value: Any, path: str, length: int) -> bytes:
    if not isinstance(value, str) or not value or "=" in value:
        raise ModelEvidenceAuthError(f"{path} must be unpadded base64url")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise ModelEvidenceAuthError(f"{path} is invalid base64url") from exc
    if len(decoded) != length:
        raise ModelEvidenceAuthError(f"{path} must decode to {length} bytes")
    return decoded


def _load_json_object(raw: str | None, env_name: str) -> Mapping[str, Any]:
    value = raw if raw is not None else os.environ.get(env_name)
    if not value:
        raise ModelEvidenceAuthError(f"external trust input {env_name} is required")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ModelEvidenceAuthError(f"{env_name} must be JSON") from exc
    if not isinstance(payload, Mapping):
        raise ModelEvidenceAuthError(f"{env_name} must be a JSON object")
    return payload


def _load_principals(raw: str | None) -> set[str]:
    value = raw if raw is not None else os.environ.get(PRINCIPALS_ENV)
    if not value:
        raise ModelEvidenceAuthError(f"external principal input {PRINCIPALS_ENV} is required")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ModelEvidenceAuthError(f"{PRINCIPALS_ENV} must be JSON") from exc
    if not isinstance(payload, list) or not payload:
        raise ModelEvidenceAuthError(f"{PRINCIPALS_ENV} must be a non-empty JSON array")
    if any(not isinstance(item, str) or not item for item in payload) or len(payload) != len(set(payload)):
        raise ModelEvidenceAuthError(f"{PRINCIPALS_ENV} must contain unique non-empty IDs")
    return set(payload)


def load_external_trust(
    *,
    trust_bundle_json: str | None = None,
    implementation_principals_json: str | None = None,
    now: datetime | None = None,
) -> tuple[dict[tuple[str, str], dict[str, Any]], set[str], datetime, str]:
    bundle = _load_json_object(trust_bundle_json, TRUST_ENV)
    if set(bundle) != {"schema_version", "evidence_class", "provenance", "issued_at", "keys"}:
        raise ModelEvidenceAuthError("model-eval trust bundle fields are invalid")
    if (
        bundle.get("schema_version") != "1.0.0"
        or bundle.get("evidence_class") != "external_model_eval_trust_bundle"
        or bundle.get("provenance") != "external-release-operator"
    ):
        raise ModelEvidenceAuthError("model-eval trust bundle header is invalid")
    issued_at = _timestamp(bundle.get("issued_at"), "trust_bundle.issued_at")
    keys = bundle.get("keys")
    if not isinstance(keys, list) or len(keys) < 2:
        raise ModelEvidenceAuthError("model-eval trust bundle requires at least two keys")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if issued_at > current + ALLOWED_CLOCK_SKEW:
        raise ModelEvidenceAuthError("model-eval trust bundle is future-dated")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw in enumerate(keys):
        if not isinstance(raw, Mapping) or set(raw) != {
            "signer_id",
            "key_id",
            "public_key_b64url",
            "role",
            "evidence_roles",
            "valid_from",
            "valid_until",
        }:
            raise ModelEvidenceAuthError(f"trust_bundle.keys[{index}] fields are invalid")
        signer_id = raw.get("signer_id")
        key_id = raw.get("key_id")
        role = raw.get("role")
        if not isinstance(signer_id, str) or not signer_id or not isinstance(key_id, str) or not key_id:
            raise ModelEvidenceAuthError(f"trust_bundle.keys[{index}] IDs are invalid")
        if role not in {"runner", "evaluator"}:
            raise ModelEvidenceAuthError(f"trust_bundle.keys[{index}].role is invalid")
        evidence_roles = raw.get("evidence_roles")
        if not isinstance(evidence_roles, list) or not evidence_roles or set(evidence_roles) - {"candidate", "retained-v1"}:
            raise ModelEvidenceAuthError(f"trust_bundle.keys[{index}].evidence_roles is invalid")
        valid_from = _timestamp(raw.get("valid_from"), f"trust_bundle.keys[{index}].valid_from")
        valid_until = _timestamp(raw.get("valid_until"), f"trust_bundle.keys[{index}].valid_until")
        if valid_until <= valid_from:
            raise ModelEvidenceAuthError(f"trust_bundle.keys[{index}] validity is reversed")
        public_key = _b64url(raw.get("public_key_b64url"), f"trust_bundle.keys[{index}].public_key_b64url", 32)
        key = (signer_id, key_id)
        if key in result:
            raise ModelEvidenceAuthError(f"duplicate trusted signer/key: {signer_id}/{key_id}")
        result[key] = {
            **dict(raw),
            "public_key": public_key,
            "valid_from_dt": valid_from,
            "valid_until_dt": valid_until,
        }
    principals = _load_principals(implementation_principals_json)
    return result, principals, current, sha256_json(bundle)


def verify_envelope(
    envelope: Any,
    *,
    expected_role: str,
    evidence_role: str,
    trusted_keys: Mapping[tuple[str, str], Mapping[str, Any]],
    implementation_principals: set[str],
    now: datetime,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping) or set(envelope) != {
        "signer_id",
        "key_id",
        "role",
        "signed_at",
        "binding",
        "signature_b64url",
    }:
        raise ModelEvidenceAuthError(f"{expected_role} authentication fields are invalid")
    signer_id = envelope.get("signer_id")
    key_id = envelope.get("key_id")
    if not isinstance(signer_id, str) or not signer_id or not isinstance(key_id, str) or not key_id:
        raise ModelEvidenceAuthError(f"{expected_role} signer IDs are invalid")
    if signer_id in implementation_principals:
        raise ModelEvidenceAuthError(f"{expected_role} signer is an implementation principal")
    if envelope.get("role") != expected_role:
        raise ModelEvidenceAuthError(f"{expected_role} signature role is mis-scoped")
    trusted = trusted_keys.get((signer_id, key_id))
    if trusted is None:
        raise ModelEvidenceAuthError(f"{expected_role} key is not externally trusted")
    if trusted["role"] != expected_role or evidence_role not in trusted["evidence_roles"]:
        raise ModelEvidenceAuthError(f"{expected_role} key scope does not permit {evidence_role}")
    signed_at = _timestamp(envelope.get("signed_at"), f"{expected_role}.signed_at")
    if not trusted["valid_from_dt"] <= signed_at <= trusted["valid_until_dt"]:
        raise ModelEvidenceAuthError(f"{expected_role} signature falls outside key validity")
    if signed_at > now + ALLOWED_CLOCK_SKEW or now - signed_at > timedelta(days=MAX_AGE_DAYS):
        raise ModelEvidenceAuthError(f"{expected_role} signature is stale or future-dated")
    signature = _b64url(envelope.get("signature_b64url"), f"{expected_role}.signature_b64url", 64)
    unsigned = {key: value for key, value in envelope.items() if key != "signature_b64url"}
    try:
        Ed25519PublicKey.from_public_bytes(trusted["public_key"]).verify(signature, canonical_bytes(unsigned))
    except InvalidSignature as exc:
        raise ModelEvidenceAuthError(f"{expected_role} signature verification failed") from exc
    return dict(envelope)
