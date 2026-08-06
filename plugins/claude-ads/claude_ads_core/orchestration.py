"""Immutable file-backed orchestration packets and artifact-only gates."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .workflow_contracts import WorkflowContractError, validate_workflow_contract


class OrchestrationError(ValueError):
    """Raised when packet persistence or artifact-only evaluation fails."""


PACKET_CONTRACTS = {
    "run": "orchestration-run",
    "task": "orchestration-task",
    "result": "orchestration-result",
    "gate": "orchestration-gate",
}


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the sole hash/signature representation for a packet."""
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def artifact_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _packet_id(kind: str, payload: Mapping[str, Any]) -> str:
    field = {"run": "run_id", "task": "task_id", "result": "result_id", "gate": "gate_id"}[kind]
    return str(payload[field])


class OrchestrationStore:
    """Persist append-only orchestration evidence beneath one contained root."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _directory(self, kind: str) -> Path:
        if kind not in PACKET_CONTRACTS:
            raise OrchestrationError(f"unknown packet kind {kind!r}")
        return self.root / {"run": "runs", "task": "tasks", "result": "results", "gate": "gates"}[kind]

    @staticmethod
    def _reject_symlink_components(path: Path) -> None:
        absolute = path.absolute()
        current = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            current /= part
            if current.is_symlink():
                raise OrchestrationError(f"orchestration path contains a symlink: {current}")

    def path_for(self, kind: str, packet_id: str) -> Path:
        if not packet_id or not all(character.isalnum() or character in "._-" for character in packet_id):
            raise OrchestrationError("packet ID is not path-safe")
        return self._directory(kind) / f"{packet_id}.json"

    def write(self, kind: str, payload: Mapping[str, Any]) -> Path:
        """Validate and create a packet exactly once with mode 0600."""
        contract = PACKET_CONTRACTS.get(kind)
        if contract is None:
            raise OrchestrationError(f"unknown packet kind {kind!r}")
        try:
            validate_workflow_contract(contract, payload)
        except WorkflowContractError as exc:
            raise OrchestrationError(str(exc)) from exc
        directory = self._directory(kind)
        self._reject_symlink_components(self.root)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._reject_symlink_components(directory)
        path = self.path_for(kind, _packet_id(kind, payload))
        if path.exists() or path.is_symlink():
            raise OrchestrationError(f"immutable packet already exists: {path.name}")
        if kind == "result":
            self._verify_supersedes(payload)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError as exc:
            raise OrchestrationError(f"immutable packet already exists: {path.name}") from exc
        try:
            data = canonical_json_bytes(payload)
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return path

    def read(self, kind: str, packet_id: str) -> dict[str, Any]:
        path = self.path_for(kind, packet_id)
        self._reject_symlink_components(path.parent)
        if path.is_symlink() or not path.is_file():
            raise OrchestrationError(f"packet is missing or unsafe: {path.name}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_workflow_contract(PACKET_CONTRACTS[kind], payload)
        except (OSError, json.JSONDecodeError, WorkflowContractError) as exc:
            raise OrchestrationError(f"invalid packet {path.name}: {exc}") from exc
        return payload

    def list(self, kind: str) -> list[dict[str, Any]]:
        directory = self._directory(kind)
        if not directory.exists():
            return []
        self._reject_symlink_components(directory)
        return [self.read(kind, path.stem) for path in sorted(directory.glob("*.json"))]

    def _verify_supersedes(self, payload: Mapping[str, Any]) -> None:
        prior_id = payload.get("supersedes")
        existing = self.list("result")
        if prior_id is None:
            if any(item["task_id"] == payload["task_id"] for item in existing):
                raise OrchestrationError("a repeated task result must supersede the prior result")
            return
        prior = next((item for item in existing if item["result_id"] == prior_id), None)
        if prior is None:
            raise OrchestrationError("supersedes references a missing result")
        if prior["run_id"] != payload["run_id"] or prior["task_id"] != payload["task_id"]:
            raise OrchestrationError("supersedes must remain within the same run and task")
        if any(item.get("supersedes") == prior_id for item in existing):
            raise OrchestrationError("a result may be superseded only once")
        def instant(value: str) -> datetime:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

        if instant(str(payload["created_at"])) <= instant(str(prior["created_at"])):
            raise OrchestrationError("a superseding result must have a later created_at")


def _latest_results(results: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    items = list(results)
    by_id = {str(item["result_id"]): item for item in items}
    superseded = {str(item["supersedes"]) for item in items if item.get("supersedes") is not None}
    latest: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if str(item["result_id"]) in superseded:
            continue
        task_id = str(item["task_id"])
        if task_id in latest:
            raise OrchestrationError(f"task {task_id!r} has multiple unsuperseded results")
        latest[task_id] = item
        prior_id = item.get("supersedes")
        if prior_id is not None and str(prior_id) not in by_id:
            raise OrchestrationError(f"result {item['result_id']!r} supersedes missing evidence")
    return latest


def evaluate_artifact_gate(
    run: Mapping[str, Any],
    tasks: Iterable[Mapping[str, Any]],
    results: Iterable[Mapping[str, Any]],
    *,
    gate_id: str,
    stage: str,
    required_task_ids: Iterable[str],
    evaluated_at: str,
) -> dict[str, Any]:
    """Build a deterministic gate solely from validated packet artifacts."""
    try:
        validate_workflow_contract("orchestration-run", run)
        task_list = list(tasks)
        result_list = list(results)
        for task in task_list:
            validate_workflow_contract("orchestration-task", task)
        for result in result_list:
            validate_workflow_contract("orchestration-result", result)
    except WorkflowContractError as exc:
        raise OrchestrationError(str(exc)) from exc
    run_id = str(run["run_id"])
    task_by_id: dict[str, Mapping[str, Any]] = {}
    for task in task_list:
        if task["run_id"] != run_id:
            raise OrchestrationError("task subject does not match the run")
        if task["task_id"] in task_by_id:
            raise OrchestrationError(f"duplicate task ID {task['task_id']!r}")
        task_by_id[str(task["task_id"])] = task
    for result in result_list:
        if result["run_id"] != run_id:
            raise OrchestrationError("result subject does not match the run")
        task = task_by_id.get(str(result["task_id"]))
        if task is None or task["role"] != result["role"]:
            raise OrchestrationError("result does not match a declared task and role")
    latest = _latest_results(result_list)
    required = list(dict.fromkeys(required_task_ids))
    if not required:
        raise OrchestrationError("a gate requires at least one task")
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    evaluated_result_ids: list[str] = []
    for task_id in required:
        task = task_by_id.get(task_id)
        result = latest.get(task_id)
        passed = task is not None and result is not None and result["status"] == "ok"
        evidence_refs: list[str] = []
        if result is not None:
            evaluated_result_ids.append(str(result["result_id"]))
            evidence_refs = [f"result:{result['result_id']}", *result["evidence_refs"]]
        if task is None:
            message = "required task packet is missing"
        elif result is None:
            message = "required result packet is missing"
        elif result["status"] != "ok":
            message = f"latest result status is {result['status']}"
        else:
            message = "latest immutable result is ok"
        checks.append({"id": f"task-{task_id}", "passed": passed, "evidence_refs": evidence_refs, "message": message})
        if not passed:
            blockers.append(f"{task_id}: {message}")
    gate = {
        "schema_version": "1.0.0",
        "artifact_type": "orchestration-gate",
        "gate_id": gate_id,
        "run_id": run_id,
        "stage": stage,
        "evaluated_at": evaluated_at,
        "evaluator": "artifact-only-v1",
        "required_task_ids": required,
        "evaluated_result_ids": sorted(evaluated_result_ids),
        "checks": checks,
        "decision": "pass" if not blockers else "fail",
        "blockers": blockers,
    }
    try:
        validate_workflow_contract("orchestration-gate", gate)
    except WorkflowContractError as exc:
        raise OrchestrationError(str(exc)) from exc
    return gate
