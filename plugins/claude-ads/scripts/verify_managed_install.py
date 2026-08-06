#!/usr/bin/env python3
"""Verify a completed managed installer result on its native host."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _target_id() -> str:
    if sys.implementation.name != "cpython" or sys.version_info[:2] not in {(3, 11), (3, 12)}:
        raise ValueError("managed install verification requires CPython 3.11 or 3.12")
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    if system == "linux" and machine == "x86_64":
        platform_id = "linux"
    elif system == "darwin" and machine in {"x86_64", "arm64"}:
        platform_id = "macos-x86" if machine == "x86_64" else "macos-arm"
    elif system == "windows" and machine == "x86_64":
        platform_id = "windows"
    else:
        raise ValueError(f"no managed install target for {system}/{machine}")
    return f"runtime-{platform_id}-cp{sys.version_info.major}{sys.version_info.minor}"


def verify(repository: Path, skill_dir: Path) -> dict[str, object]:
    receipt_path = skill_dir / "managed-runtime-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    expected_fields = {
        "schema_version", "receipt_class", "target_id", "target", "resolver",
        "python_full_version", "pip_version", "requirements_lock_sha256",
        "dependency_inventory_sha256", "target_evidence_sha256",
        "pip_install_report_sha256", "components",
    }
    if not isinstance(receipt, dict) or set(receipt) != expected_fields:
        raise ValueError("managed runtime receipt fields mismatch")
    if receipt.get("schema_version") != "1.0.0" or receipt.get("receipt_class") != "managed-python-runtime-install":
        raise ValueError("managed runtime receipt identity mismatch")
    target_id = _target_id()
    if receipt.get("target_id") != target_id or receipt.get("resolver") != "pip / PyPI":
        raise ValueError("managed runtime receipt native target mismatch")
    components = receipt.get("components")
    if not isinstance(components, list) or len(components) != 33:
        raise ValueError("managed runtime receipt closure mismatch")
    if receipt.get("requirements_lock_sha256") != _sha256(repository / "requirements.lock"):
        raise ValueError("managed runtime receipt lock binding mismatch")
    inventory_path = repository / "control-plane/manifests/dependency-inventory.json"
    if receipt.get("dependency_inventory_sha256") != _sha256(inventory_path):
        raise ValueError("managed runtime receipt inventory binding mismatch")
    evidence_path = repository / "control-plane/dependency-evidence" / f"{target_id}.json"
    if receipt.get("target_evidence_sha256") != _sha256(evidence_path):
        raise ValueError("managed runtime receipt target evidence binding mismatch")

    python = skill_dir / ".venv" / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
    if not python.is_file():
        raise ValueError("managed runtime interpreter is missing")
    checks = (
        [str(python), "-m", "pip", "check"],
        [str(python), "-c", "import claude_ads_core; print(claude_ads_core.__version__)"],
    )
    for command in checks:
        result = subprocess.run(command, check=False, text=True, capture_output=True)
        if result.returncode:
            raise ValueError(f"managed runtime execution check failed: {result.stderr.strip()}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skill-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = verify(args.repository.resolve(), args.skill_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"managed install verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"verified managed install: {receipt['target_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
