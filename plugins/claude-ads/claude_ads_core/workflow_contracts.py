"""Strict dependency-free validators for workflow and orchestration artifacts.

These validators intentionally check structural truth only.  They do not infer
platform eligibility, authorize a mutation, or turn a plan into evidence.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit


SCHEMA_VERSION = "1.0.0"
PLATFORMS = {
    "google", "meta", "youtube", "linkedin", "tiktok", "microsoft",
    "apple", "amazon", "reddit", "pinterest", "snapchat", "x",
}
PRIVACY_CLASSES = {"public", "internal", "confidential", "restricted"}
ARTIFACT_STATUSES = {"draft", "complete", "partial", "failed"}
WORKFLOW_CONTRACT_NAMES = (
    "data-lifecycle",
    "setup-profile",
    "brand-profile",
    "media-plan",
    "creative-brief",
    "generation-manifest",
    "monitoring-bundle",
    "experiment-artifact",
    "mutation-plan",
    "orchestration-run",
    "orchestration-task",
    "orchestration-result",
    "orchestration-gate",
)


class WorkflowContractError(ValueError):
    """Raised when a workflow artifact is structurally invalid."""


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WorkflowContractError(f"{path} must be an object")
    return value


def _exact(
    value: Any,
    path: str,
    required: Sequence[str],
    optional: Sequence[str] = (),
) -> Mapping[str, Any]:
    obj = _object(value, path)
    missing = [key for key in required if key not in obj]
    if missing:
        raise WorkflowContractError(f"{path} missing required field(s): {', '.join(missing)}")
    unknown = sorted(set(obj) - set(required) - set(optional))
    if unknown:
        raise WorkflowContractError(f"{path} has unknown field(s): {', '.join(unknown)}")
    return obj


def _string(value: Any, path: str, *, pattern: str | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowContractError(f"{path} must be a non-empty string")
    if pattern and not re.fullmatch(pattern, value):
        raise WorkflowContractError(f"{path} has an invalid format")
    return value


def _nullable_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _enum(value: Any, path: str, choices: set[str]) -> str:
    if value not in choices:
        raise WorkflowContractError(f"{path} must be one of: {', '.join(sorted(choices))}")
    return str(value)


def _bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise WorkflowContractError(f"{path} must be a boolean")
    return value


def _number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkflowContractError(f"{path} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise WorkflowContractError(f"{path} must be finite")
    if minimum is not None and result < minimum:
        raise WorkflowContractError(f"{path} must be >= {minimum}")
    return result


def _integer(value: Any, path: str, *, minimum: int | None = None) -> int:
    """Validate a schema ``integer`` without Python's bool/int coercion.

    JSON contract inputs must carry an actual integer token. Floats, including
    integral-looking values such as ``100.0``, are rejected deliberately so the
    dependency-free validator cannot silently widen the public contract.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        raise WorkflowContractError(f"{path} must be an integer")
    if minimum is not None and value < minimum:
        raise WorkflowContractError(f"{path} must be >= {minimum}")
    return value


def _list(value: Any, path: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list):
        raise WorkflowContractError(f"{path} must be an array")
    if len(value) < minimum:
        raise WorkflowContractError(f"{path} must contain at least {minimum} item(s)")
    return value


def _strings(value: Any, path: str, *, minimum: int = 0, unique: bool = True) -> list[str]:
    items = _list(value, path, minimum=minimum)
    result = [_string(item, f"{path}[{index}]") for index, item in enumerate(items)]
    if unique and len(result) != len(set(result)):
        raise WorkflowContractError(f"{path} must contain unique values")
    return result


def _datetime(value: Any, path: str) -> str:
    text = _string(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkflowContractError(f"{path} must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise WorkflowContractError(f"{path} must include a UTC offset")
    return text


def _date(value: Any, path: str) -> str:
    text = _string(value, path)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise WorkflowContractError(f"{path} must be an ISO 8601 date") from exc
    return text


def _sha256(value: Any, path: str) -> str:
    return _string(value, path, pattern=r"[0-9a-f]{64}")


def _id(value: Any, path: str) -> str:
    return _string(value, path, pattern=r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _base(payload: Mapping[str, Any], artifact_type: str) -> None:
    if payload["schema_version"] != SCHEMA_VERSION:
        raise WorkflowContractError(f"$.schema_version must equal {SCHEMA_VERSION!r}")
    if payload["artifact_type"] != artifact_type:
        raise WorkflowContractError(f"$.artifact_type must equal {artifact_type!r}")
    _id(payload["run_id"], "$.run_id")
    _datetime(payload["created_at"], "$.created_at")


def _platforms(value: Any, path: str, *, minimum: int = 1) -> list[str]:
    values = _strings(value, path, minimum=minimum)
    for index, platform in enumerate(values):
        _enum(platform, f"{path}[{index}]", PLATFORMS)
    return values


def _validate_data_lifecycle_at(value: Any, path: str) -> Mapping[str, Any]:
    required = (
        "schema_version", "lifecycle_id", "classification", "retention",
        "encryption", "access", "deletion", "incident",
    )
    doc = _exact(value, path, required)
    if doc["schema_version"] != SCHEMA_VERSION:
        raise WorkflowContractError(f"{path}.schema_version must equal {SCHEMA_VERSION!r}")
    _id(doc["lifecycle_id"], f"{path}.lifecycle_id")
    classification = _enum(doc["classification"], f"{path}.classification", PRIVACY_CLASSES)

    retention = _exact(
        doc["retention"], f"{path}.retention",
        ("minimum_seconds", "mode", "delete_after", "purpose", "exception_reason"),
    )
    _integer(retention["minimum_seconds"], f"{path}.retention.minimum_seconds", minimum=0)
    mode = _enum(retention["mode"], f"{path}.retention.mode", {"ephemeral", "operator-defined", "policy-defined", "exception"})
    delete_after = retention["delete_after"]
    if delete_after is not None:
        _datetime(delete_after, f"{path}.retention.delete_after")
    _string(retention["purpose"], f"{path}.retention.purpose")
    exception_reason = _nullable_string(retention["exception_reason"], f"{path}.retention.exception_reason")
    if classification != "public" and mode != "exception" and delete_after is None:
        raise WorkflowContractError(f"{path}.retention.delete_after is required for non-public data")
    if mode == "exception" and not exception_reason:
        raise WorkflowContractError(f"{path}.retention.exception_reason is required for an exception")

    encryption = _exact(doc["encryption"], f"{path}.encryption", ("at_rest", "in_transit", "evidence_refs"))
    at_rest = _enum(encryption["at_rest"], f"{path}.encryption.at_rest", {"verified", "not-applicable"})
    in_transit = _enum(encryption["in_transit"], f"{path}.encryption.in_transit", {"verified", "not-applicable"})
    encryption_evidence = _strings(encryption["evidence_refs"], f"{path}.encryption.evidence_refs")
    if classification != "public" and (at_rest != "verified" or in_transit != "verified" or not encryption_evidence):
        raise WorkflowContractError(f"{path}.encryption requires verified at-rest and in-transit controls with evidence for non-public data")

    access = _exact(doc["access"], f"{path}.access", ("owner", "authorized_roles", "access_log_locator"))
    _string(access["owner"], f"{path}.access.owner")
    _strings(access["authorized_roles"], f"{path}.access.authorized_roles", minimum=1)
    if access["access_log_locator"] is not None:
        _relative_path(access["access_log_locator"], f"{path}.access.access_log_locator")

    deletion = _exact(
        doc["deletion"], f"{path}.deletion",
        ("status", "method", "verification_required", "verification_artifact_locator"),
    )
    deletion_status = _enum(deletion["status"], f"{path}.deletion.status", {"scheduled", "verified", "exception"})
    _string(deletion["method"], f"{path}.deletion.method")
    if not _bool(deletion["verification_required"], f"{path}.deletion.verification_required"):
        raise WorkflowContractError(f"{path}.deletion.verification_required must be true")
    locator = deletion["verification_artifact_locator"]
    if locator is not None:
        _relative_path(locator, f"{path}.deletion.verification_artifact_locator")
    if deletion_status == "verified" and locator is None:
        raise WorkflowContractError(f"{path}.deletion.verified status requires a verification artifact")

    incident = _exact(doc["incident"], f"{path}.incident", ("owner", "reporting_channel", "status", "record_locator"))
    _string(incident["owner"], f"{path}.incident.owner")
    _string(incident["reporting_channel"], f"{path}.incident.reporting_channel")
    incident_status = _enum(incident["status"], f"{path}.incident.status", {"not-triggered", "open", "contained", "resolved"})
    if incident["record_locator"] is not None:
        _relative_path(incident["record_locator"], f"{path}.incident.record_locator")
    if incident_status != "not-triggered" and incident["record_locator"] is None:
        raise WorkflowContractError(f"{path}.incident.record_locator is required after an incident is triggered")
    return doc


def _validate_data_lifecycle(payload: Mapping[str, Any]) -> None:
    _validate_data_lifecycle_at(payload, "$")


def _validate_setup(payload: Mapping[str, Any]) -> None:
    required = (
        "schema_version", "artifact_type", "run_id", "created_at", "business",
        "objective", "platforms", "account_refs", "data_sources", "privacy_class",
        "mutation_authority", "approver_ids", "assumptions", "data_lifecycle",
    )
    doc = _exact(payload, "$", required)
    _base(doc, "setup-profile")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    business = _exact(doc["business"], "$.business", ("name", "business_model", "geographies", "regulated_categories"))
    _string(business["name"], "$.business.name")
    _string(business["business_model"], "$.business.business_model")
    _strings(business["geographies"], "$.business.geographies", minimum=1)
    _strings(business["regulated_categories"], "$.business.regulated_categories")
    objective = _exact(doc["objective"], "$.objective", ("primary", "conversion_definition", "success_metrics"))
    _string(objective["primary"], "$.objective.primary")
    _string(objective["conversion_definition"], "$.objective.conversion_definition")
    _strings(objective["success_metrics"], "$.objective.success_metrics", minimum=1)
    _platforms(doc["platforms"], "$.platforms")
    for index, item in enumerate(_list(doc["account_refs"], "$.account_refs")):
        ref = _exact(item, f"$.account_refs[{index}]", ("platform", "account_id"))
        _enum(ref["platform"], f"$.account_refs[{index}].platform", PLATFORMS)
        _string(ref["account_id"], f"$.account_refs[{index}].account_id")
    source_ids: set[str] = set()
    for index, item in enumerate(_list(doc["data_sources"], "$.data_sources", minimum=1)):
        source = _exact(item, f"$.data_sources[{index}]", ("id", "kind", "platform", "status"))
        source_id = _id(source["id"], f"$.data_sources[{index}].id")
        if source_id in source_ids:
            raise WorkflowContractError("$.data_sources IDs must be unique")
        source_ids.add(source_id)
        _enum(source["kind"], f"$.data_sources[{index}].kind", {"export", "api", "screenshot", "manual"})
        if source["platform"] != "cross-platform":
            _enum(source["platform"], f"$.data_sources[{index}].platform", PLATFORMS)
        _enum(source["status"], f"$.data_sources[{index}].status", {"available", "missing", "unverified"})
    _enum(doc["privacy_class"], "$.privacy_class", PRIVACY_CLASSES)
    if doc["privacy_class"] != doc["data_lifecycle"]["classification"]:
        raise WorkflowContractError("$.privacy_class must match $.data_lifecycle.classification")
    authority = _enum(doc["mutation_authority"], "$.mutation_authority", {"none", "draft-only", "approved-plan-required"})
    approvers = _strings(doc["approver_ids"], "$.approver_ids")
    if authority == "approved-plan-required" and not approvers:
        raise WorkflowContractError("$.approver_ids is required for approved-plan-required authority")
    _strings(doc["assumptions"], "$.assumptions")


def _validate_brand(payload: Mapping[str, Any]) -> None:
    required = (
        "schema_version", "artifact_type", "run_id", "created_at", "brand_name",
        "website_url", "observations", "inferences", "source_ids",
        "source_assets_authorized", "missing_fields", "status",
        "data_lifecycle",
    )
    doc = _exact(payload, "$", required)
    _base(doc, "brand-profile")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    _string(doc["brand_name"], "$.brand_name")
    url = _nullable_string(doc["website_url"], "$.website_url")
    if url:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise WorkflowContractError("$.website_url must be a public-style HTTPS URL without userinfo")
    for field, inferred in (("observations", False), ("inferences", True)):
        for index, item in enumerate(_list(doc[field], f"$.{field}")):
            keys = ("field", "value", "evidence_refs", "confidence") + (("approval_status",) if inferred else ())
            record = _exact(item, f"$.{field}[{index}]", keys)
            _string(record["field"], f"$.{field}[{index}].field")
            if not isinstance(record["value"], (str, int, float, bool, list, dict)) and record["value"] is not None:
                raise WorkflowContractError(f"$.{field}[{index}].value must be JSON-compatible")
            evidence = _strings(record["evidence_refs"], f"$.{field}[{index}].evidence_refs")
            _enum(record["confidence"], f"$.{field}[{index}].confidence", {"high", "medium", "low", "none"})
            if not inferred and not evidence:
                raise WorkflowContractError(f"$.{field}[{index}].evidence_refs must not be empty")
            if inferred:
                _enum(record["approval_status"], f"$.{field}[{index}].approval_status", {"pending", "approved", "rejected"})
    _strings(doc["source_ids"], "$.source_ids")
    _bool(doc["source_assets_authorized"], "$.source_assets_authorized")
    _strings(doc["missing_fields"], "$.missing_fields")
    _enum(doc["status"], "$.status", ARTIFACT_STATUSES)


def _validate_media_plan(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "run_id", "created_at", "objective", "currency", "channels", "actions", "assumptions", "exclusions", "status", "data_lifecycle")
    doc = _exact(payload, "$", required)
    _base(doc, "media-plan")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    _string(doc["objective"], "$.objective")
    _string(doc["currency"], "$.currency", pattern=r"[A-Z]{3}")
    for index, item in enumerate(_list(doc["channels"], "$.channels", minimum=1)):
        channel = _exact(item, f"$.channels[{index}]", ("platform", "role", "rationale", "budget_amount", "prerequisites", "exclusions"))
        _enum(channel["platform"], f"$.channels[{index}].platform", PLATFORMS)
        _string(channel["role"], f"$.channels[{index}].role")
        _string(channel["rationale"], f"$.channels[{index}].rationale")
        if channel["budget_amount"] is not None:
            _number(channel["budget_amount"], f"$.channels[{index}].budget_amount", minimum=0)
        _strings(channel["prerequisites"], f"$.channels[{index}].prerequisites")
        _strings(channel["exclusions"], f"$.channels[{index}].exclusions")
    action_ids: set[str] = set()
    for index, item in enumerate(_list(doc["actions"], "$.actions", minimum=1)):
        action = _exact(item, f"$.actions[{index}]", ("id", "description", "owner", "timing", "dependencies", "evidence_refs", "success_measure", "rollback_or_exit"))
        action_id = _id(action["id"], f"$.actions[{index}].id")
        if action_id in action_ids:
            raise WorkflowContractError("$.actions IDs must be unique")
        action_ids.add(action_id)
        for field in ("description", "owner", "timing", "success_measure", "rollback_or_exit"):
            _string(action[field], f"$.actions[{index}].{field}")
        _strings(action["dependencies"], f"$.actions[{index}].dependencies")
        _strings(action["evidence_refs"], f"$.actions[{index}].evidence_refs")
    _strings(doc["assumptions"], "$.assumptions")
    _strings(doc["exclusions"], "$.exclusions")
    _enum(doc["status"], "$.status", ARTIFACT_STATUSES)


def _validate_creative(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "run_id", "created_at", "objective", "audience", "offer", "approved_claims", "hypotheses", "copy_deck", "specification_source_ids", "human_review", "status", "data_lifecycle")
    doc = _exact(payload, "$", required)
    _base(doc, "creative-brief")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    for field in ("objective", "audience", "offer"):
        _string(doc[field], f"$.{field}")
    for index, item in enumerate(_list(doc["approved_claims"], "$.approved_claims")):
        claim = _exact(item, f"$.approved_claims[{index}]", ("claim", "evidence_refs"))
        _string(claim["claim"], f"$.approved_claims[{index}].claim")
        _strings(claim["evidence_refs"], f"$.approved_claims[{index}].evidence_refs", minimum=1)
    hypothesis_ids: set[str] = set()
    for index, item in enumerate(_list(doc["hypotheses"], "$.hypotheses", minimum=1)):
        hypothesis = _exact(item, f"$.hypotheses[{index}]", ("id", "insight", "promise", "hook", "cta", "platforms", "experiment_hypothesis"))
        hypothesis_id = _id(hypothesis["id"], f"$.hypotheses[{index}].id")
        if hypothesis_id in hypothesis_ids:
            raise WorkflowContractError("$.hypotheses IDs must be unique")
        hypothesis_ids.add(hypothesis_id)
        for field in ("insight", "promise", "hook", "cta", "experiment_hypothesis"):
            _string(hypothesis[field], f"$.hypotheses[{index}].{field}")
        _platforms(hypothesis["platforms"], f"$.hypotheses[{index}].platforms")
    for index, item in enumerate(_list(doc["copy_deck"], "$.copy_deck")):
        copy = _exact(item, f"$.copy_deck[{index}]", ("hypothesis_id", "platform", "placement", "fields"))
        if copy["hypothesis_id"] not in hypothesis_ids:
            raise WorkflowContractError(f"$.copy_deck[{index}].hypothesis_id is unknown")
        _enum(copy["platform"], f"$.copy_deck[{index}].platform", PLATFORMS)
        _string(copy["placement"], f"$.copy_deck[{index}].placement")
        names: set[str] = set()
        for field_index, item_field in enumerate(_list(copy["fields"], f"$.copy_deck[{index}].fields", minimum=1)):
            field = _exact(item_field, f"$.copy_deck[{index}].fields[{field_index}]", ("name", "value"))
            name = _string(field["name"], f"$.copy_deck[{index}].fields[{field_index}].name")
            if name in names:
                raise WorkflowContractError(f"$.copy_deck[{index}].fields names must be unique")
            names.add(name)
            _string(field["value"], f"$.copy_deck[{index}].fields[{field_index}].value")
    sources = _strings(doc["specification_source_ids"], "$.specification_source_ids")
    if doc["copy_deck"] and not sources:
        raise WorkflowContractError("$.specification_source_ids is required when copy_deck is present")
    _enum(doc["human_review"], "$.human_review", {"pending", "approved", "rejected"})
    _enum(doc["status"], "$.status", ARTIFACT_STATUSES)


def _validate_generation(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "run_id", "created_at", "provider", "inputs", "outputs", "failures", "human_review", "status", "data_lifecycle")
    doc = _exact(payload, "$", required)
    _base(doc, "generation-manifest")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    provider = _exact(doc["provider"], "$.provider", ("id", "model", "capability_evidence"))
    _string(provider["id"], "$.provider.id")
    _string(provider["model"], "$.provider.model")
    _strings(provider["capability_evidence"], "$.provider.capability_evidence", minimum=1)
    inputs = _exact(doc["inputs"], "$.inputs", ("creative_brief_sha256", "brand_profile_sha256", "source_assets"))
    _sha256(inputs["creative_brief_sha256"], "$.inputs.creative_brief_sha256")
    _sha256(inputs["brand_profile_sha256"], "$.inputs.brand_profile_sha256")
    for index, item in enumerate(_list(inputs["source_assets"], "$.inputs.source_assets")):
        asset = _exact(item, f"$.inputs.source_assets[{index}]", ("path", "sha256", "rights_confirmed"))
        _relative_path(asset["path"], f"$.inputs.source_assets[{index}].path")
        _sha256(asset["sha256"], f"$.inputs.source_assets[{index}].sha256")
        _bool(asset["rights_confirmed"], f"$.inputs.source_assets[{index}].rights_confirmed")
    for index, item in enumerate(_list(doc["outputs"], "$.outputs")):
        output = _exact(item, f"$.outputs[{index}]", ("asset_id", "path", "sha256", "media_type", "width", "height", "prompt_version", "prompt_sha256", "prompt_summary", "status", "cost"))
        _id(output["asset_id"], f"$.outputs[{index}].asset_id")
        _relative_path(output["path"], f"$.outputs[{index}].path")
        _sha256(output["sha256"], f"$.outputs[{index}].sha256")
        _string(output["media_type"], f"$.outputs[{index}].media_type")
        _integer(output["width"], f"$.outputs[{index}].width", minimum=1)
        _integer(output["height"], f"$.outputs[{index}].height", minimum=1)
        _string(output["prompt_version"], f"$.outputs[{index}].prompt_version")
        _sha256(output["prompt_sha256"], f"$.outputs[{index}].prompt_sha256")
        if output["prompt_summary"] != "[redacted: raw prompt is ephemeral and is not persisted]":
            raise WorkflowContractError(f"$.outputs[{index}].prompt_summary must use the canonical redaction marker")
        _enum(output["status"], f"$.outputs[{index}].status", {"generated", "validated", "rejected"})
        if output["cost"] is not None:
            cost = _exact(output["cost"], f"$.outputs[{index}].cost", ("currency", "amount"))
            _string(cost["currency"], f"$.outputs[{index}].cost.currency", pattern=r"[A-Z]{3}")
            _number(cost["amount"], f"$.outputs[{index}].cost.amount", minimum=0)
    for index, item in enumerate(_list(doc["failures"], "$.failures")):
        failure = _exact(item, f"$.failures[{index}]", ("input_id", "reason", "recovery_hint"))
        for field in failure:
            _string(failure[field], f"$.failures[{index}].{field}")
    _enum(doc["human_review"], "$.human_review", {"pending", "approved", "rejected"})
    _enum(doc["status"], "$.status", ARTIFACT_STATUSES)


def _relative_path(value: Any, path: str) -> str:
    text = _string(value, path)
    if text.startswith(("/", "\\")) or "\\" in text or any(part in {"", ".", ".."} for part in text.split("/")):
        raise WorkflowContractError(f"{path} must be a contained POSIX relative path")
    return text


def _validate_monitoring(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "run_id", "created_at", "window", "checkpoints", "missing_inputs", "contradictions", "completeness", "data_lifecycle")
    doc = _exact(payload, "$", required)
    _base(doc, "monitoring-bundle")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    window = _exact(doc["window"], "$.window", ("start", "end", "timezone"))
    start = _date(window["start"], "$.window.start")
    end = _date(window["end"], "$.window.end")
    if end < start:
        raise WorkflowContractError("$.window.end must not precede start")
    _string(window["timezone"], "$.window.timezone")
    for index, item in enumerate(_list(doc["checkpoints"], "$.checkpoints")):
        checkpoint = _exact(item, f"$.checkpoints[{index}]", ("checkpoint_id", "platform", "observed_at", "control_id", "status", "evidence_refs", "observation", "recovery_hint"))
        _id(checkpoint["checkpoint_id"], f"$.checkpoints[{index}].checkpoint_id")
        _enum(checkpoint["platform"], f"$.checkpoints[{index}].platform", PLATFORMS | {"cross-platform"})
        _datetime(checkpoint["observed_at"], f"$.checkpoints[{index}].observed_at")
        _string(checkpoint["control_id"], f"$.checkpoints[{index}].control_id")
        status = _enum(checkpoint["status"], f"$.checkpoints[{index}].status", {"normal", "warning", "critical", "unknown"})
        refs = _strings(checkpoint["evidence_refs"], f"$.checkpoints[{index}].evidence_refs")
        if status != "unknown" and not refs:
            raise WorkflowContractError(f"$.checkpoints[{index}].evidence_refs must not be empty")
        _string(checkpoint["observation"], f"$.checkpoints[{index}].observation")
        _string(checkpoint["recovery_hint"], f"$.checkpoints[{index}].recovery_hint")
    _strings(doc["missing_inputs"], "$.missing_inputs")
    _strings(doc["contradictions"], "$.contradictions")
    completeness = _enum(doc["completeness"], "$.completeness", {"complete", "partial", "failed"})
    if doc["missing_inputs"] and completeness == "complete":
        raise WorkflowContractError("$.completeness cannot be complete with missing inputs")


def _validate_experiment(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "run_id", "created_at", "experiment_id", "stage", "design", "result", "decision", "status", "data_lifecycle")
    doc = _exact(payload, "$", required)
    _base(doc, "experiment-artifact")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    _id(doc["experiment_id"], "$.experiment_id")
    stage = _enum(doc["stage"], "$.stage", {"setup", "readout"})
    design = _exact(doc["design"], "$.design", ("decision", "hypothesis", "treatment", "control", "randomization_unit", "population", "primary_metric", "guardrails", "minimum_effect", "stopping_rule", "exclusions"))
    for field in ("decision", "hypothesis", "treatment", "control", "randomization_unit", "population", "primary_metric", "minimum_effect", "stopping_rule"):
        _string(design[field], f"$.design.{field}")
    _strings(design["guardrails"], "$.design.guardrails", minimum=1)
    _strings(design["exclusions"], "$.design.exclusions")
    if stage == "setup":
        if doc["result"] is not None or doc["decision"] is not None:
            raise WorkflowContractError("setup artifacts must not contain result or decision")
    else:
        result = _exact(doc["result"], "$.result", ("assignment_integrity", "data_complete", "effect_estimate", "uncertainty", "evidence_refs"))
        _bool(result["assignment_integrity"], "$.result.assignment_integrity")
        _bool(result["data_complete"], "$.result.data_complete")
        _string(result["effect_estimate"], "$.result.effect_estimate")
        _string(result["uncertainty"], "$.result.uncertainty")
        _strings(result["evidence_refs"], "$.result.evidence_refs", minimum=1)
        _string(doc["decision"], "$.decision")
    _enum(doc["status"], "$.status", ARTIFACT_STATUSES)


def _validate_mutation(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "run_id", "created_at", "plan_id", "platform", "account_id", "object_id", "operation", "before", "after", "reason", "blast_radius", "ceilings", "approval", "idempotency_key", "audit_destination", "verification_steps", "rollback", "remote_precondition_sha256", "status", "data_lifecycle")
    doc = _exact(payload, "$", required)
    _base(doc, "mutation-plan")
    _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    _id(doc["plan_id"], "$.plan_id")
    _enum(doc["platform"], "$.platform", PLATFORMS)
    _string(doc["account_id"], "$.account_id")
    _string(doc["object_id"], "$.object_id")
    operation = _string(doc["operation"], "$.operation").casefold().replace("-", "_")
    if "delete" in operation:
        raise WorkflowContractError("$.operation permanent deletion is outside the contract")
    before = _object(doc["before"], "$.before")
    after = _object(doc["after"], "$.after")
    if before == after:
        raise WorkflowContractError("$.before and $.after must differ")
    for field in ("reason", "blast_radius", "idempotency_key"):
        _string(doc[field], f"$.{field}")
    for index, item in enumerate(_list(doc["ceilings"], "$.ceilings", minimum=1)):
        ceiling = _exact(item, f"$.ceilings[{index}]", ("name", "value", "unit"))
        _string(ceiling["name"], f"$.ceilings[{index}].name")
        if not isinstance(ceiling["value"], (str, int, float)) or isinstance(ceiling["value"], bool):
            raise WorkflowContractError(f"$.ceilings[{index}].value must be a string or number")
        _string(ceiling["unit"], f"$.ceilings[{index}].unit")
    status = _enum(doc["status"], "$.status", {"draft", "approved", "applied", "verified", "rolled-back"})
    if doc["approval"] is not None:
        approval = _exact(doc["approval"], "$.approval", ("status", "approver_id", "approved_plan_sha256", "approved_at"))
        _enum(approval["status"], "$.approval.status", {"approved"})
        _string(approval["approver_id"], "$.approval.approver_id")
        _sha256(approval["approved_plan_sha256"], "$.approval.approved_plan_sha256")
        _datetime(approval["approved_at"], "$.approval.approved_at")
    if status != "draft" and doc["approval"] is None:
        raise WorkflowContractError("$.approval is required after draft status")
    _relative_path(doc["audit_destination"], "$.audit_destination")
    _strings(doc["verification_steps"], "$.verification_steps", minimum=1)
    rollback = _exact(doc["rollback"], "$.rollback", ("operation", "expected_state", "verification"))
    _string(rollback["operation"], "$.rollback.operation")
    _object(rollback["expected_state"], "$.rollback.expected_state")
    _strings(rollback["verification"], "$.rollback.verification", minimum=1)
    _sha256(doc["remote_precondition_sha256"], "$.remote_precondition_sha256")


def _validate_orchestration_run(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "run_id", "created_at", "objective", "scopes", "phases", "privacy_class", "mutation_authority", "status", "data_lifecycle")
    doc = _exact(payload, "$", required)
    _base(doc, "orchestration-run")
    lifecycle = _validate_data_lifecycle_at(doc["data_lifecycle"], "$.data_lifecycle")
    _string(doc["objective"], "$.objective")
    _strings(doc["scopes"], "$.scopes", minimum=1)
    _strings(doc["phases"], "$.phases", minimum=1)
    _enum(doc["privacy_class"], "$.privacy_class", PRIVACY_CLASSES)
    if doc["privacy_class"] != lifecycle["classification"]:
        raise WorkflowContractError("$.privacy_class must match $.data_lifecycle.classification")
    _enum(doc["mutation_authority"], "$.mutation_authority", {"none", "repository-only", "draft-external", "approved-external"})
    _enum(doc["status"], "$.status", {"open"})


def _validate_orchestration_task(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "task_id", "run_id", "role", "objective", "scope", "exclusions", "evidence_policy", "privacy_class", "mutation_authority", "inputs", "output_contract", "verification", "recovery", "depends_on", "created_at", "status")
    doc = _exact(payload, "$", required)
    _base(doc, "orchestration-task")
    _id(doc["task_id"], "$.task_id")
    _string(doc["role"], "$.role")
    _string(doc["objective"], "$.objective")
    _strings(doc["scope"], "$.scope", minimum=1)
    _strings(doc["exclusions"], "$.exclusions")
    _strings(doc["evidence_policy"], "$.evidence_policy", minimum=1)
    _enum(doc["privacy_class"], "$.privacy_class", PRIVACY_CLASSES)
    _enum(doc["mutation_authority"], "$.mutation_authority", {"none", "repository-only", "draft-external", "approved-external"})
    for index, item in enumerate(_list(doc["inputs"], "$.inputs")):
        artifact = _exact(item, f"$.inputs[{index}]", ("artifact_id", "sha256"))
        _string(artifact["artifact_id"], f"$.inputs[{index}].artifact_id")
        _sha256(artifact["sha256"], f"$.inputs[{index}].sha256")
    output = _exact(doc["output_contract"], "$.output_contract", ("contract", "destination", "single_writer"))
    _enum(output["contract"], "$.output_contract.contract", set(WORKFLOW_CONTRACT_NAMES))
    _relative_path(output["destination"], "$.output_contract.destination")
    if not _bool(output["single_writer"], "$.output_contract.single_writer"):
        raise WorkflowContractError("$.output_contract.single_writer must be true")
    _strings(doc["verification"], "$.verification", minimum=1)
    _strings(doc["recovery"], "$.recovery", minimum=1)
    dependencies = _strings(doc["depends_on"], "$.depends_on")
    if doc["task_id"] in dependencies:
        raise WorkflowContractError("$.depends_on cannot include the task itself")
    _enum(doc["status"], "$.status", {"queued"})


def _validate_orchestration_result(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "result_id", "task_id", "run_id", "role", "created_at", "status", "output_artifacts", "evidence_refs", "summary", "blockers", "recovery_hints", "supersedes")
    doc = _exact(payload, "$", required)
    _base(doc, "orchestration-result")
    _id(doc["result_id"], "$.result_id")
    _id(doc["task_id"], "$.task_id")
    _string(doc["role"], "$.role")
    status = _enum(doc["status"], "$.status", {"ok", "needs_input", "blocked", "failed"})
    for index, item in enumerate(_list(doc["output_artifacts"], "$.output_artifacts")):
        artifact = _exact(item, f"$.output_artifacts[{index}]", ("path", "contract", "sha256"))
        _relative_path(artifact["path"], f"$.output_artifacts[{index}].path")
        _enum(artifact["contract"], f"$.output_artifacts[{index}].contract", set(WORKFLOW_CONTRACT_NAMES))
        _sha256(artifact["sha256"], f"$.output_artifacts[{index}].sha256")
    _strings(doc["evidence_refs"], "$.evidence_refs")
    _string(doc["summary"], "$.summary")
    blockers = _strings(doc["blockers"], "$.blockers")
    recovery = _strings(doc["recovery_hints"], "$.recovery_hints")
    if status == "ok" and blockers:
        raise WorkflowContractError("$.blockers must be empty for an ok result")
    if status != "ok" and (not blockers or not recovery):
        raise WorkflowContractError("non-ok results require blockers and recovery_hints")
    if doc["supersedes"] is not None:
        _id(doc["supersedes"], "$.supersedes")
        if doc["supersedes"] == doc["result_id"]:
            raise WorkflowContractError("$.supersedes cannot reference the result itself")


def _validate_orchestration_gate(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "artifact_type", "gate_id", "run_id", "stage", "evaluated_at", "evaluator", "required_task_ids", "evaluated_result_ids", "checks", "decision", "blockers")
    doc = _exact(payload, "$", required)
    if doc["schema_version"] != SCHEMA_VERSION or doc["artifact_type"] != "orchestration-gate":
        raise WorkflowContractError("gate version or artifact_type is invalid")
    _id(doc["run_id"], "$.run_id")
    _id(doc["gate_id"], "$.gate_id")
    _string(doc["stage"], "$.stage")
    _datetime(doc["evaluated_at"], "$.evaluated_at")
    _enum(doc["evaluator"], "$.evaluator", {"artifact-only-v1"})
    required_ids = _strings(doc["required_task_ids"], "$.required_task_ids", minimum=1)
    _strings(doc["evaluated_result_ids"], "$.evaluated_result_ids")
    checks = _list(doc["checks"], "$.checks", minimum=len(required_ids))
    for index, item in enumerate(checks):
        check = _exact(item, f"$.checks[{index}]", ("id", "passed", "evidence_refs", "message"))
        _id(check["id"], f"$.checks[{index}].id")
        _bool(check["passed"], f"$.checks[{index}].passed")
        _strings(check["evidence_refs"], f"$.checks[{index}].evidence_refs")
        _string(check["message"], f"$.checks[{index}].message")
    decision = _enum(doc["decision"], "$.decision", {"pass", "fail"})
    blockers = _strings(doc["blockers"], "$.blockers")
    all_passed = all(check["passed"] for check in checks)
    if (decision == "pass") != all_passed:
        raise WorkflowContractError("$.decision must equal the aggregate check verdict")
    if decision == "pass" and blockers:
        raise WorkflowContractError("$.blockers must be empty for a passing gate")
    if decision == "fail" and not blockers:
        raise WorkflowContractError("a failing gate requires blockers")


WORKFLOW_VALIDATORS: dict[str, Callable[[Mapping[str, Any]], None]] = {
    "data-lifecycle": _validate_data_lifecycle,
    "setup-profile": _validate_setup,
    "brand-profile": _validate_brand,
    "media-plan": _validate_media_plan,
    "creative-brief": _validate_creative,
    "generation-manifest": _validate_generation,
    "monitoring-bundle": _validate_monitoring,
    "experiment-artifact": _validate_experiment,
    "mutation-plan": _validate_mutation,
    "orchestration-run": _validate_orchestration_run,
    "orchestration-task": _validate_orchestration_task,
    "orchestration-result": _validate_orchestration_result,
    "orchestration-gate": _validate_orchestration_gate,
}


def validate_workflow_contract(name: str, payload: Any) -> None:
    """Validate one workflow artifact without external dependencies."""
    validator = WORKFLOW_VALIDATORS.get(name)
    if validator is None:
        raise WorkflowContractError(f"unknown workflow contract {name!r}")
    validator(_object(payload, "$"))
