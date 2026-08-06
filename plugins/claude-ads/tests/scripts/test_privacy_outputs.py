"""Regression tests for prompt and local-path minimization in shipped JSON."""

from __future__ import annotations

import hashlib
import base64
import json
import os
import subprocess
import struct
import sys
import zlib
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_image  # noqa: E402


_VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def _probe_png(ihdr: bytes, idat: bytes, middle: bytes = b"") -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + middle
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def test_private_permission_implementation_uses_structural_handle_acl_checks():
    source = (SCRIPTS_DIR / "generate_image.py").read_text(encoding="utf-8")
    assert "SetSecurityInfo" in source
    assert "GetSecurityInfo" in source
    assert "GetAclInformation" in source
    assert "GetAce" in source
    assert "ace_flags == 0" in source
    assert "CreateFileW" in source
    assert "SECURITY_ATTRIBUTES" in source
    assert "ReOpenFile" in source
    assert "GetFileInformationByHandleEx" in source
    assert "_windows_open_path_guard" in source
    assert "_windows_delete_by_anchor" in source
    assert "0x80020000" in source
    assert "0x00000001,  # FILE_SHARE_READ only" in source
    assert "SetNamedSecurityInfo" not in source
    assert 'sddl = f"O:{current_sid}D:P' in source
    assert "icacls" not in source.lower()
    assert "whoami" not in source.lower()


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL semantics require NTFS")
def test_windows_private_writer_applies_verified_owner_only_dacl(tmp_path):
    output = tmp_path / "private.bin"
    generate_image._write_private(output, b"private")
    assert output.read_bytes() == b"private"
    script = r"""
$sections = [System.Security.AccessControl.AccessControlSections]::Access -bor [System.Security.AccessControl.AccessControlSections]::Owner
$security = [System.IO.File]::GetAccessControl($env:CLAUDE_ADS_PRIVATE_FILE, $sections)
$current = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$owner = $security.GetOwner([System.Security.Principal.SecurityIdentifier])
$rules = @($security.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]))
if (-not $security.AreAccessRulesProtected) { throw 'DACL inheritance is not protected' }
if (-not $owner.Equals($current)) { throw 'owner is not the current token user' }
if ($rules.Count -ne 1) { throw "expected one ACE, found $($rules.Count)" }
$rule = $rules[0]
if ($rule.IsInherited) { throw 'ACE is inherited' }
if ($rule.InheritanceFlags -ne [System.Security.AccessControl.InheritanceFlags]::None) { throw 'ACE has inheritance flags' }
if ($rule.PropagationFlags -ne [System.Security.AccessControl.PropagationFlags]::None) { throw 'ACE has propagation flags' }
if (-not $rule.IdentityReference.Equals($current)) { throw 'ACE trustee mismatch' }
if ($rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) { throw 'ACE is not allow' }
if ($rule.FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl) { throw 'ACE is not exact full control' }
"""
    verified = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        env={**os.environ, "CLAUDE_ADS_PRIVATE_FILE": str(output)},
        check=False,
        capture_output=True,
        text=True,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics require NTFS")
def test_windows_path_guard_allows_read_and_denies_write(tmp_path):
    descriptor, path, anchor = generate_image._windows_create_private_temp(
        tmp_path, ".guard-", ".bin", temporary=False
    )
    guard = None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(b"private")
        guard = generate_image._windows_open_path_guard(path, anchor)
        assert path.read_bytes() == b"private"
        with pytest.raises(OSError):
            with path.open("wb"):
                pass
    finally:
        generate_image._close_windows_handle(guard)
        generate_image._windows_delete_by_anchor(anchor)
        generate_image._close_windows_handle(anchor)
    assert not path.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows file identity requires NTFS/ReFS")
def test_windows_guard_rejects_pre_acquisition_path_swap_and_deletes_exact_anchor(tmp_path):
    descriptor, path, anchor = generate_image._windows_create_private_temp(
        tmp_path, ".swap-", ".bin", temporary=False
    )
    moved = tmp_path / "moved-private.bin"
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(b"private")
        path.rename(moved)
        path.write_bytes(b"replacement")
        with pytest.raises(PermissionError, match="no longer identifies"):
            generate_image._windows_open_path_guard(path, anchor)
    finally:
        generate_image._windows_delete_by_anchor(anchor)
        generate_image._close_windows_handle(anchor)
    assert not moved.exists()
    assert path.read_bytes() == b"replacement"


def _lifecycle() -> dict:
    return {
        "schema_version": "1.0.0",
        "lifecycle_id": "private-generation-test",
        "classification": "internal",
        "retention": {"minimum_seconds": 0, "mode": "operator-defined", "delete_after": "2026-07-12T16:00:00Z", "purpose": "Verify sanitized generation output", "exception_reason": None},
        "encryption": {"at_rest": "verified", "in_transit": "verified", "evidence_refs": ["operator-attestation:test-encryption"]},
        "access": {"owner": "test-owner", "authorized_roles": ["test-runner"], "access_log_locator": None},
        "deletion": {"status": "scheduled", "method": "Test cleanup", "verification_required": True, "verification_artifact_locator": None},
        "incident": {"owner": "test-owner", "reporting_channel": "Private test channel", "status": "not-triggered", "record_locator": None},
    }


def test_batch_json_contains_hashes_and_relative_locators_only(tmp_path, monkeypatch, capsys):
    raw_prompt = "private customer launch prompt with unreleased offer"
    batch = tmp_path / "jobs.json"
    batch.write_text(json.dumps([{"prompt": raw_prompt, "output": "creative.png"}]), encoding="utf-8")
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setattr(generate_image, "generate_image", lambda *args, **kwargs: (b"private-image", 100, 100))

    generate_image.run_batch(
        str(batch), "artifacts", "gemini", "test-model", "ephemeral-test-key", True, _lifecycle()
    )

    payload = json.loads(capsys.readouterr().out)
    shipped = json.dumps(payload)
    assert raw_prompt not in shipped
    assert str(tmp_path) not in shipped
    assert payload[0]["prompt_sha256"] == hashlib.sha256(raw_prompt.encode()).hexdigest()
    assert payload[0]["prompt_summary"] == generate_image._PROMPT_SUMMARY
    assert payload[0]["file_locator"] == "artifacts/creative.png"
    assert payload[0]["model"] == "test-model"
    assert "prompt" not in payload[0]
    assert "file" not in payload[0]
    assert generate_image._path_has_private_permissions(
        tmp_path / "artifacts/creative.png"
    )


def test_batch_reference_requires_explicit_bounded_input_root(
    tmp_path, monkeypatch, capsys
):
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    outside = tmp_path / "private-client-reference.png"
    outside.write_bytes(b"private-client-reference-bytes")
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": str(outside)}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.delenv("CLAUDE_ADS_INPUT_ROOT", raising=False)
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )

    with pytest.raises(ValueError, match="require --input-root"):
        generate_image.run_batch(
            str(batch),
            "artifacts",
            "gemini",
            "test-model",
            "ephemeral-test-key",
            True,
            _lifecycle(),
        )

    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "reference",
    ["../private.png", "/tmp/private.png", "C:\\private.png", "nested\\private.png"],
)
def test_batch_reference_rejects_nonportable_or_escaping_paths(
    reference, tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": reference}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )

    generate_image.run_batch(
        str(batch),
        "artifacts",
        "gemini",
        "test-model",
        "ephemeral-test-key",
        True,
        _lifecycle(),
        str(input_root),
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["generation_success"] is False


def test_batch_reference_rejects_windows_drive_relative_path(
    tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "C:private.png").write_bytes(_VALID_PNG)
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "C:private.png"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )

    generate_image.run_batch(
        str(batch),
        "artifacts",
        "gemini",
        "test-model",
        "ephemeral-test-key",
        True,
        _lifecycle(),
        str(input_root),
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["generation_success"] is False


def test_batch_reference_uses_private_snapshot_and_removes_it(
    tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    references = input_root / "brand"
    references.mkdir(parents=True)
    output_root.mkdir()
    source = references / "reference.png"
    source_bytes = _VALID_PNG
    source.write_bytes(source_bytes)
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "brand/reference.png"}]),
        encoding="utf-8",
    )
    observed = {}

    def fake_generate(prompt, ratio, provider, model, api_key, reference_path):
        snapshot = Path(reference_path)
        observed["path"] = snapshot
        observed["bytes"] = snapshot.read_bytes()
        observed["mode"] = snapshot.stat().st_mode & 0o777
        observed["private_permissions"] = generate_image._path_has_private_permissions(
            snapshot
        )
        return b"generated-image", 1, 1

    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(generate_image, "generate_image", fake_generate)
    generate_image.run_batch(
        str(batch),
        "artifacts",
        "gemini",
        "test-model",
        "ephemeral-test-key",
        True,
        _lifecycle(),
        str(input_root),
    )

    payload = json.loads(capsys.readouterr().out)
    assert observed["path"] != source
    assert observed["bytes"] == source_bytes
    assert observed["private_permissions"] is True
    if os.name != "nt":
        assert observed["mode"] == 0o600
    assert not observed["path"].exists()
    assert payload[0]["reference_image_sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert payload[0]["generation_success"] is True


def test_batch_reference_rejects_non_image_bytes_with_image_suffix(
    tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "secret.png").write_bytes(b"not-an-image: confidential text")
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "secret.png"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )

    generate_image.run_batch(
        str(batch),
        "artifacts",
        "gemini",
        "test-model",
        "ephemeral-test-key",
        True,
        _lifecycle(),
        str(input_root),
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["generation_success"] is False


@pytest.mark.parametrize(
    "payload",
    [
        _probe_png(
            struct.pack(">IIBBBBB", 1, 1, 3, 6, 0, 0, 0),
            zlib.compress(b"\x00\x00"),
        ),
        _probe_png(
            struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0),
            b"",
        ),
        _probe_png(
            struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0),
            zlib.compress(b"private text"),
        ),
        _probe_png(
            struct.pack(">IIBBBBB", 1, 1, 1, 3, 0, 0, 0),
            zlib.compress(b"\x00\x00"),
            _png_chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff\x80\x80\x80"),
        ),
        _probe_png(
            struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0),
            zlib.compress(b"\x00\x00\x00\x00\x00"),
            _png_chunk(b"1bad", b"private"),
        ),
    ],
)
def test_batch_reference_rejects_crc_correct_malformed_png(
    payload, tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "forged.png").write_bytes(payload)
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "forged.png"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )
    generate_image.run_batch(
        str(batch), "artifacts", "gemini", "test-model", "key", True,
        _lifecycle(), str(input_root)
    )
    assert json.loads(capsys.readouterr().out)[0]["generation_success"] is False


@pytest.mark.parametrize(
    "reference",
    [
        " CON.png", "CON.png", "COM¹.png", "LPT².png", "foo:bar.png",
        "wild*.png", "traildot.png.", "control\x1f.png",
    ],
)
def test_batch_reference_rejects_nonportable_names(
    reference, tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": reference}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )
    generate_image.run_batch(
        str(batch), "artifacts", "gemini", "test-model", "key", True,
        _lifecycle(), str(input_root)
    )
    assert json.loads(capsys.readouterr().out)[0]["generation_success"] is False


def test_batch_reference_rejects_oversized_file(tmp_path, monkeypatch, capsys):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "large.png").write_bytes(_VALID_PNG)
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "large.png"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(generate_image, "MAX_REFERENCE_IMAGE_BYTES", 8)
    monkeypatch.setattr(
        generate_image, "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur")
    )
    generate_image.run_batch(
        str(batch), "artifacts", "gemini", "test-model", "key", True,
        _lifecycle(), str(input_root)
    )
    assert json.loads(capsys.readouterr().out)[0]["generation_success"] is False


def test_batch_reference_rejects_non_regular_path(tmp_path, monkeypatch, capsys):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "directory.png").mkdir()
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "directory.png"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image, "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur")
    )
    generate_image.run_batch(
        str(batch), "artifacts", "gemini", "test-model", "key", True,
        _lifecycle(), str(input_root)
    )
    assert json.loads(capsys.readouterr().out)[0]["generation_success"] is False


def test_batch_reference_uses_environment_input_root(
    tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    (input_root / "brand.png").write_bytes(_VALID_PNG)
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "brand.png"}]),
        encoding="utf-8",
    )
    observed = {}

    def fake_generate(*args):
        observed["bytes"] = Path(args[-1]).read_bytes()
        return b"generated", 1, 1

    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setenv("CLAUDE_ADS_INPUT_ROOT", str(input_root))
    monkeypatch.setattr(generate_image, "generate_image", fake_generate)
    generate_image.run_batch(
        str(batch), "artifacts", "gemini", "test-model", "key", True,
        _lifecycle()
    )
    assert observed["bytes"] == _VALID_PNG
    assert json.loads(capsys.readouterr().out)[0]["generation_success"] is True


def test_direct_cli_reference_requires_root_before_provider_dispatch(
    tmp_path, monkeypatch, capsys
):
    lifecycle = tmp_path / "lifecycle.json"
    lifecycle.write_text(json.dumps(_lifecycle()), encoding="utf-8")
    monkeypatch.delenv("CLAUDE_ADS_INPUT_ROOT", raising=False)
    monkeypatch.setattr(generate_image, "_get_api_key", lambda provider: "key")
    monkeypatch.setattr(
        generate_image, "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur")
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_image.py", "test", "--provider", "gemini", "--model", "model",
            "--reference-image", "brand.png", "--data-lifecycle", str(lifecycle),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        generate_image.main()
    assert exc.value.code == 1
    assert "requires --input-root" in capsys.readouterr().err


def test_batch_reference_rejects_symlink_before_provider_dispatch(
    tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    output_root = tmp_path / "outputs"
    input_root.mkdir()
    output_root.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"private")
    (input_root / "linked.png").symlink_to(outside)
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": "linked.png"}]),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )

    generate_image.run_batch(
        str(batch),
        "artifacts",
        "gemini",
        "test-model",
        "ephemeral-test-key",
        True,
        _lifecycle(),
        str(input_root),
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["generation_success"] is False


def test_batch_reference_parent_swap_cannot_escape_after_validation(
    tmp_path, monkeypatch, capsys
):
    input_root = tmp_path / "approved-inputs"
    approved_parent = input_root / "brand"
    parked_parent = input_root / "brand-validated"
    outside_parent = tmp_path / "outside"
    output_root = tmp_path / "outputs"
    approved_parent.mkdir(parents=True)
    outside_parent.mkdir()
    output_root.mkdir()
    relative = "brand/reference.png"
    (approved_parent / "reference.png").write_bytes(
        b"\x89PNG\r\n\x1a\napproved"
    )
    outside_bytes = b"\x89PNG\r\n\x1a\noutside-private"
    (outside_parent / "reference.png").write_bytes(outside_bytes)
    batch = tmp_path / "jobs.json"
    batch.write_text(
        json.dumps([{"prompt": "test", "reference_image": relative}]),
        encoding="utf-8",
    )
    original_resolve = generate_image._resolve_reference_source

    def resolve_then_swap(reference, root):
        result = original_resolve(reference, root)
        approved_parent.rename(parked_parent)
        approved_parent.symlink_to(outside_parent, target_is_directory=True)
        return result

    monkeypatch.setattr(generate_image, "_resolve_reference_source", resolve_then_swap)
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )

    generate_image.run_batch(
        str(batch),
        "artifacts",
        "gemini",
        "test-model",
        "ephemeral-test-key",
        True,
        _lifecycle(),
        str(input_root),
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["generation_success"] is False
    assert payload[0]["reference_image_sha256"] is None


def test_failed_capture_result_does_not_echo_raw_url_or_local_path(tmp_path, monkeypatch):
    pytest.importorskip("playwright.sync_api")
    import capture_screenshot

    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(tmp_path))
    raw_url = "https://example.com/private/customer-42?token=top-secret"
    private_path = "/private/customer/workstation/capture.png"
    lifecycle = _lifecycle()
    lifecycle["classification"] = "confidential"

    result = capture_screenshot.capture_screenshot(
        raw_url,
        private_path,
        data_lifecycle=lifecycle,
        egress_attestation=None,
    )

    shipped = json.dumps(result)
    assert raw_url not in shipped
    assert "customer-42" not in shipped
    assert private_path not in shipped
    assert result["success"] is False
