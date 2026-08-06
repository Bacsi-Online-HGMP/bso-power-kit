"""SSRF regression tests for ``scripts/url_utils.py``.

Locks in the v1.5.1 hardening: any URL whose hostname resolves to a private,
loopback, link-local, CGNAT, or otherwise-internal address must be rejected,
and DNS failures must fail closed (raise ValueError, not pass through).

These tests do not require network access — IP-literal hostnames bypass DNS
resolution. The dns-failure case uses a hostname that definitely won't resolve.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


# Make scripts/ importable without requiring an installed package
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from url_utils import (  # noqa: E402
    EgressSandboxAttestation,
    guarded_request,
    install_playwright_ssrf_guard,
    load_egress_sandbox_attestation,
    resolve_output_path,
    sanitize_error,
    sanitize_headers,
    sanitize_url,
    validate_browser_url,
    validate_url,
)


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _attestation_document(now: datetime) -> dict:
    return {
        "schema_version": "1.0.0",
        "attestation_id": "attestation:test-001",
        "audience": "claude-ads-browser-egress",
        "issuer_id": "security-reviewer:test",
        "environment_id": "test-environment",
        "issued_at": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "not_before": (now - timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "enforcement_boundary": "container-network-policy",
        "controls": {
            "blocks_link_local": True,
            "blocks_loopback": True,
            "blocks_metadata": True,
            "blocks_private": True,
            "blocks_reserved": True,
            "covers_ipv4": True,
            "covers_ipv6": True,
            "covers_redirects": True,
            "covers_subresources": True,
            "fail_closed": True,
            "prevents_dns_rebinding": True,
            "public_only_after_dns": True,
        },
        "evidence_refs": ["test-artifact:egress-policy-001"],
        "authentication": {
            "algorithm": "ed25519",
            "key_id": "test-ed25519-key",
            "signature_b64url": "",
        },
    }


def _write_signed_attestation(
    tmp_path: Path,
    *,
    now: datetime | None = None,
    mutate_before_sign=None,
) -> tuple[Path, str, datetime]:
    current = now or datetime.now(timezone.utc)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    document = _attestation_document(current)
    if mutate_before_sign:
        mutate_before_sign(document)
    unsigned = json.loads(json.dumps(document))
    unsigned["authentication"].pop("signature_b64url")
    payload = json.dumps(
        unsigned,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    document["authentication"]["signature_b64url"] = _b64url(private_key.sign(payload))
    path = tmp_path / "egress-attestation.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path, _b64url(public_key), current


def _load_test_attestation(tmp_path: Path) -> EgressSandboxAttestation:
    path, public_key, current = _write_signed_attestation(tmp_path)
    return load_egress_sandbox_attestation(
        path,
        public_key_b64url=public_key,
        expected_key_id="test-ed25519-key",
        expected_environment_id="test-environment",
        now=current,
    )


# ─── SSRF blocklist ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/admin",
    "http://2130706433/admin",       # integer-encoded 127.0.0.1
    "http://0x7f000001/admin",       # hexadecimal 127.0.0.1
    "http://127.1/admin",            # shortened loopback notation
    "http://localhost/secret",         # resolves to 127.0.0.1
    "http://0.0.0.0:8080",
    "http://10.0.0.1",
    "http://172.16.0.5",
    "http://172.31.255.254",
    "http://192.168.1.1",
    "http://169.254.169.254/latest/meta-data/",  # AWS metadata endpoint
    "http://100.64.0.1",                          # CGNAT range
    "http://224.0.0.1",                           # multicast
    "http://198.18.0.1",                          # benchmark network
    "https://[::1]/admin",
    "https://[fc00::1]",                          # ULA
    "https://[fe80::1%25eth0]",                   # link-local (note %% for URL)
    "https://[::ffff:127.0.0.1]",                 # IPv4-mapped IPv6 loopback
    "https://[::]/",                              # IPv6 unspecified (v1.6.0 fix)
    "https://[64:ff9b::a9fe:a9fe]/",              # NAT64 prefix → IPv4 169.254.169.254 (v1.7.1 fix)
    "https://[2002:7f00:0001::]/",                # 6to4 prefix wrapping 127.0.0.1 (v1.7.1 fix)
    "https://[2001:db8::1]/",                     # IPv6 documentation range (v1.7.1 fix)
])
def test_blocks_private_and_internal_addresses(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.parametrize("url", [
    "ftp://example.com",
    "file:///etc/passwd",
    "gopher://example.com",
    "data:text/html,<script>alert(1)</script>",
    "javascript:alert(1)",
])
def test_blocks_non_http_schemes(url):
    with pytest.raises(ValueError):
        validate_url(url)


@pytest.mark.parametrize("url", [
    "https://user:password@example.com/path",
    "https://example.com\\@127.0.0.1/",
    "https://example.com:invalid/path",
    "https://example.com/\nHost: 127.0.0.1",
])
def test_blocks_parser_differentials_and_url_credentials(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_dns_resolution_failure_fails_closed():
    """A hostname that cannot be resolved should raise, not be allowed
    through to the requests/playwright layer."""
    with pytest.raises(ValueError):
        validate_url("http://nonexistent-hostname-for-claude-ads-tests.invalid")


@pytest.mark.parametrize("url,expected_contains", [
    ("example.com", "https://example.com"),    # bare hostname gets https:// prepended
    ("https://example.com/foo?bar=baz", "https://example.com/foo"),
])
def test_valid_public_urls_pass(url, expected_contains):
    """Public hostnames that resolve to non-blocked IPs must pass through.
    This requires network access (DNS for example.com) so we keep it minimal."""
    pytest.importorskip("socket")
    try:
        result = validate_url(url)
    except ValueError as e:
        if "DNS" in str(e) or "resolve" in str(e).lower():
            pytest.skip("No network access for DNS resolution")
        raise
    assert expected_contains in result


# ─── sanitize_error ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw,sanitized_marker", [
    ("Failed with key=sk-1234567890abcdef", "key=***"),
    ("Got 401 with token=ghp_AAA111BBB222CCC", "token=***"),
    ("Error: secret=topsecret123 in payload", "secret=***"),
    ("Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig is invalid", "Bearer ***"),
    ("Authorization: Bearer ghp_AAA111BBB222CCC failed", "Bearer ***"),
    ("auth=Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig", "auth=***"),  # auth= captures full Bearer token
    ("password = hunter2 was rejected", "password=***"),  # note: regex normalizes
    # New patterns added in v1.7.1 hardening:
    ("api_key=sk_live_abc123xyz failed", "api_key=***"),
    ("Got apikey=sk_live_abc123xyz", "apikey=***"),
    ("access_token=ya29.AHESpeudo refresh failed", "access_token=***"),
    ("refresh-token: 1//05somelong_value_here was rotated", "refresh_token=***"),
    ("OAuth callback ?code=4/0AY0e-g7abc&state=xyz", "code=***"),
    ("AWS Signature=AKIAxx/20260518/... invalid", "signature=***"),
])
def test_sanitize_error_strips_credentials(raw, sanitized_marker):
    msg = sanitize_error(Exception(raw))
    assert sanitized_marker in msg
    # And the original secret value must NOT survive (token bodies)
    for forbidden in (
        "sk-1234567890abcdef", "ghp_AAA111BBB222CCC", "topsecret123",
        "eyJhbGciOiJIUzI1NiJ9", "hunter2",
        "sk_live_abc123xyz", "ya29.AHESpeudo", "1//05somelong_value_here",
        "4/0AY0e-g7abc", "AKIAxx/20260518/...",
    ):
        assert forbidden not in msg


def test_sanitize_error_preserves_benign_message():
    """Messages without secrets should pass through unchanged."""
    msg = sanitize_error(Exception("File not found: /tmp/foo.json"))
    assert "File not found" in msg
    assert "/tmp/foo.json" in msg


# ─── sanitize_url ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw,forbidden_substrings,required_substrings", [
    # OAuth flow callback URLs
    ("https://example.com/cb?code=4/0AY0e-g7abc&state=xyz",
     ["4/0AY0e-g7abc"], ["code=***"]),
    # Access tokens in query string
    ("https://api.example.com/data?access_token=ya29.AHESpeudo",
     ["ya29.AHESpeudo"], ["access_token=***"]),
    # Userinfo (basic auth) in URL — should be stripped entirely
    ("https://user:supersecretpass@example.com/path",
     ["user", "supersecretpass"], ["https://example.com/path"]),
    # Mixed: userinfo + query token
    ("https://admin:hunter2@api.example.com/x?api_key=sk_live_xyz",
     ["admin", "hunter2", "sk_live_xyz"], ["api_key=***"]),
])
def test_sanitize_url_strips_credentials(raw, forbidden_substrings, required_substrings):
    cleaned = sanitize_url(raw)
    for forbidden in forbidden_substrings:
        assert forbidden not in cleaned, f"Expected {forbidden!r} stripped from {cleaned!r}"
    for required in required_substrings:
        assert required in cleaned, f"Expected {required!r} present in {cleaned!r}"


def test_sanitize_url_preserves_benign_url():
    """Plain URLs without credentials should pass through unchanged."""
    url = "https://example.com/landing?utm_source=meta&utm_campaign=brand"
    assert sanitize_url(url) == url


def test_sanitize_headers_removes_cookie_and_embedded_token():
    cleaned = sanitize_headers({
        "Set-Cookie": "session=top-secret",
        "Location": "https://example.com/cb?access_token=ya29.AHESpeudo",
        "Content-Type": "text/html",
    })
    assert cleaned["Set-Cookie"] == "***"
    assert "ya29.AHESpeudo" not in cleaned["Location"]
    assert cleaned["Content-Type"] == "text/html"


def test_sanitize_error_removes_private_key_block():
    private_key = "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----"
    assert "abc123" not in sanitize_error(RuntimeError(private_key))


# ─── Pre-request and output guards ─────────────────────────────────────────


def test_guarded_request_refuses_automatic_redirects(monkeypatch):
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )

    class Session:
        def get(self, *args, **kwargs):  # pragma: no cover - must not dispatch
            raise AssertionError("network dispatch should not happen")

    with pytest.raises(ValueError, match="Automatic redirects"):
        guarded_request(Session(), "GET", "https://example.com", allow_redirects=True)


def test_guarded_request_pins_dns_snapshot_and_preserves_tls_identity(monkeypatch):
    """A later DNS rebind cannot change the socket target after validation."""
    dns_calls = []

    def rebinding_resolver(host, *args, **kwargs):
        dns_calls.append(host)
        if len(dns_calls) == 1:
            return [(2, 1, 6, "", ("93.184.216.34", 0))]
        # A vulnerable implementation that resolves again at connect time
        # would receive the metadata address on its second hostname lookup.
        return [(2, 1, 6, "", ("169.254.169.254", 0))]

    monkeypatch.setattr("url_utils.socket.getaddrinfo", rebinding_resolver)

    class PoolManager:
        def connection_from_host(self, **kwargs):
            self.kwargs = kwargs
            return object()

    class Session:
        def mount(self, prefix, adapter):
            self.prefix = prefix
            self.adapter = adapter

        def get(self, url, **kwargs):
            prepared = requests.Request("GET", url).prepare()
            self.adapter.poolmanager = PoolManager()
            self.adapter.get_connection_with_tls_context(
                prepared,
                verify=True,
                proxies=None,
                cert=None,
            )
            self.prepared = prepared
            return SimpleNamespace(status_code=200)

    session = Session()
    response = guarded_request(session, "GET", "https://example.com/path")

    assert response.status_code == 200
    assert dns_calls == ["example.com"]
    assert session.prefix == "https://example.com/"
    assert session.adapter.poolmanager.kwargs["host"] == "93.184.216.34"
    pool_kwargs = session.adapter.poolmanager.kwargs["pool_kwargs"]
    assert pool_kwargs["server_hostname"] == "example.com"
    assert pool_kwargs["assert_hostname"] == "example.com"
    assert session.prepared.headers["Host"] == "example.com"


def test_guarded_request_mount_prefix_preserves_explicit_default_port(monkeypatch):
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )

    class Session:
        def mount(self, prefix, adapter):
            self.prefix = prefix

        def get(self, url, **kwargs):
            return SimpleNamespace(status_code=200)

    session = Session()
    guarded_request(session, "GET", "https://example.com:443/path")
    assert session.prefix == "https://example.com:443/"


def test_guarded_request_mounts_requests_canonical_idn_origin(monkeypatch):
    resolved_hosts = []

    def resolver(host, *args, **kwargs):
        resolved_hosts.append(host)
        return [(2, 1, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("url_utils.socket.getaddrinfo", resolver)

    class Session:
        def mount(self, prefix, adapter):
            self.prefix = prefix

        def get(self, url, **kwargs):
            self.url = url
            return SimpleNamespace(status_code=200)

    session = Session()
    guarded_request(session, "GET", "https://b\N{LATIN SMALL LETTER U WITH DIAERESIS}cher.de/path")

    assert session.prefix == "https://xn--bcher-kva.de/"
    assert session.url == "https://xn--bcher-kva.de/path"
    assert resolved_hosts == ["xn--bcher-kva.de"]


def test_guarded_request_rejects_private_dns_snapshot_before_dispatch(monkeypatch):
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("169.254.169.254", 0))],
    )

    class Session:
        def mount(self, *args, **kwargs):  # pragma: no cover - must not mount
            raise AssertionError("adapter must not be mounted")

        def get(self, *args, **kwargs):  # pragma: no cover - must not dispatch
            raise AssertionError("network dispatch must not happen")

    with pytest.raises(ValueError, match="blocked non-public IP"):
        guarded_request(Session(), "GET", "https://rebind.example/")


def test_guarded_request_cannot_disable_tls_or_use_proxy(monkeypatch):
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )

    class Session:
        def mount(self, *args, **kwargs):
            raise AssertionError("unsafe request must not mount")

    with pytest.raises(ValueError, match="TLS certificate verification"):
        guarded_request(Session(), "GET", "https://example.com", verify=False)
    with pytest.raises(ValueError, match="Proxies are forbidden"):
        guarded_request(
            Session(),
            "GET",
            "https://example.com",
            proxies={"https": "http://proxy.example"},
        )


def test_output_path_is_contained_and_blocks_symlink_escape(tmp_path):
    root = tmp_path / "outputs"
    root.mkdir()
    assert resolve_output_path("reports/a.pdf", root=root) == root / "reports" / "a.pdf"
    with pytest.raises(ValueError, match="escapes configured root"):
        resolve_output_path("../outside.txt", root=root)

    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes configured root"):
        resolve_output_path("linked/leak.txt", root=root)


def test_playwright_guard_blocks_private_requests_before_dispatch(monkeypatch, tmp_path):
    handlers = []

    class Context:
        def route(self, pattern, handler):
            assert pattern == "**/*"
            handlers.append(handler)

    blocked = install_playwright_ssrf_guard(
        Context(),
        egress_attestation=_load_test_attestation(tmp_path),
    )

    class Request:
        url = "http://169.254.169.254/latest/meta-data/"

    class Route:
        def __init__(self):
            self.aborted = False
            self.continued = False

        def abort(self, reason):
            assert reason == "blockedbyclient"
            self.aborted = True

        def continue_(self):
            self.continued = True

    route = Route()
    handlers[0](route, Request())
    assert route.aborted is True
    assert route.continued is False
    assert blocked and "non-public IP" in blocked[0]["error"]


def test_playwright_guard_fails_closed_without_egress_attestation(monkeypatch):
    """Route validation cannot pin Chromium DNS, so default dispatch aborts."""
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    handlers = []

    class Context:
        def route(self, pattern, handler):
            handlers.append(handler)

    class Route:
        def __init__(self):
            self.aborted = False
            self.continued = False

        def abort(self, reason):
            self.aborted = reason == "blockedbyclient"

        def continue_(self):
            self.continued = True

    blocked = install_playwright_ssrf_guard(Context())
    route = Route()
    handlers[0](route, SimpleNamespace(url="https://example.com/landing"))

    assert route.aborted is True
    assert route.continued is False
    assert "verified egress-sandbox attestation document is required" in blocked[0]["error"]


def test_playwright_guard_allows_public_url_only_with_verified_egress_attestation(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    handlers = []

    class Context:
        def route(self, pattern, handler):
            handlers.append(handler)

    class Route:
        aborted = False
        continued = False

        def abort(self, reason):
            self.aborted = True

        def continue_(self):
            self.continued = True

    attestation = _load_test_attestation(tmp_path)
    blocked = install_playwright_ssrf_guard(Context(), egress_attestation=attestation)
    route = Route()
    handlers[0](route, SimpleNamespace(url="https://example.com/landing"))

    assert route.continued is True
    assert route.aborted is False
    assert blocked == []


def test_boolean_cannot_self_assert_browser_egress(monkeypatch):
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    with pytest.raises(ValueError, match="verified egress-sandbox attestation"):
        validate_browser_url("https://example.com", egress_attestation=True)


def test_load_egress_attestation_verifies_ed25519_and_audit_reference(tmp_path):
    path, public_key, current = _write_signed_attestation(tmp_path)
    attestation = load_egress_sandbox_attestation(
        path,
        public_key_b64url=public_key,
        expected_key_id="test-ed25519-key",
        expected_environment_id="test-environment",
        now=current,
    )

    reference = attestation.audit_reference()
    assert reference["attestation_id"] == "attestation:test-001"
    assert reference["issuer_id"] == "security-reviewer:test"
    assert reference["environment_id"] == "test-environment"
    assert len(reference["document_sha256"]) == 64


def test_load_egress_attestation_rejects_tampering_wrong_environment_and_expiry(tmp_path):
    path, public_key, current = _write_signed_attestation(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["controls"]["blocks_metadata"] = False
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="browser control must be true"):
        load_egress_sandbox_attestation(
            path,
            public_key_b64url=public_key,
            expected_key_id="test-ed25519-key",
            expected_environment_id="test-environment",
            now=current,
        )

    path, public_key, current = _write_signed_attestation(tmp_path)
    with pytest.raises(ValueError, match="another environment"):
        load_egress_sandbox_attestation(
            path,
            public_key_b64url=public_key,
            expected_key_id="test-ed25519-key",
            expected_environment_id="production-runner",
            now=current,
        )
    with pytest.raises(ValueError, match="expired"):
        load_egress_sandbox_attestation(
            path,
            public_key_b64url=public_key,
            expected_key_id="test-ed25519-key",
            expected_environment_id="test-environment",
            now=current + timedelta(hours=2),
        )


def test_load_egress_attestation_rejects_signature_tampering_and_symlink(tmp_path):
    path, public_key, current = _write_signed_attestation(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["evidence_refs"] = ["test-artifact:substituted"]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="authentication failed"):
        load_egress_sandbox_attestation(
            path,
            public_key_b64url=public_key,
            expected_key_id="test-ed25519-key",
            expected_environment_id="test-environment",
            now=current,
        )

    link = tmp_path / "attestation-link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="must not be a symlink"):
        load_egress_sandbox_attestation(
            link,
            public_key_b64url=public_key,
            expected_key_id="test-ed25519-key",
            expected_environment_id="test-environment",
            now=current,
        )


def test_analyze_landing_rejects_hostname_before_browser_launch(monkeypatch):
    pytest.importorskip("playwright.sync_api")
    monkeypatch.setattr(
        "url_utils.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    import analyze_landing as analyze_landing_module

    result = analyze_landing_module.analyze_landing("https://example.com/landing")

    assert "verified egress-sandbox attestation document is required" in result["error"]


def test_guarded_browser_context_disables_service_workers_and_downloads(tmp_path):
    from url_utils import create_guarded_browser_context

    class Context:
        def route(self, pattern, handler):
            self.pattern = pattern

    class Browser:
        def new_context(self, **kwargs):
            self.kwargs = kwargs
            return Context()

    browser = Browser()
    create_guarded_browser_context(
        browser,
        viewport={"width": 100, "height": 100},
        egress_attestation=_load_test_attestation(tmp_path),
    )
    assert browser.kwargs["service_workers"] == "block"
    assert browser.kwargs["accept_downloads"] is False


def test_screenshot_receipt_binds_artifact_and_attestation_without_url_path(
    tmp_path,
    monkeypatch,
):
    pytest.importorskip("playwright.sync_api")
    from capture_screenshot import _write_capture_receipt

    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(tmp_path))
    screenshot = tmp_path / "landing.png"
    screenshot.write_bytes(b"sanitized-png-fixture")
    attestation = _load_test_attestation(tmp_path)
    lifecycle = {
        "schema_version": "1.0.0",
        "lifecycle_id": "capture-test",
        "classification": "confidential",
        "retention": {"minimum_seconds": 0, "mode": "operator-defined", "delete_after": "2026-07-12T16:00:00Z", "purpose": "Verify sanitized capture receipt", "exception_reason": None},
        "encryption": {"at_rest": "verified", "in_transit": "verified", "evidence_refs": ["operator-attestation:test-encryption"]},
        "access": {"owner": "test-owner", "authorized_roles": ["test-runner"], "access_log_locator": None},
        "deletion": {"status": "scheduled", "method": "Test cleanup", "verification_required": True, "verification_artifact_locator": None},
        "incident": {"owner": "test-owner", "reporting_channel": "Private test channel", "status": "not-triggered", "record_locator": None},
    }
    receipt_path = _write_capture_receipt(
        screenshot,
        "https://example.com/private/customer-42?utm_campaign=secret",
        attestation,
        lifecycle,
    )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["operation"] == "browser-screenshot-capture"
    assert receipt["privacy_class"] == "confidential"
    assert receipt["target"]["origin"] == "https://example.com"
    assert "customer-42" not in receipt_path.read_text(encoding="utf-8")
    assert receipt["artifact"]["locator"] == "landing.png"
    assert receipt["artifact"]["sha256"] == hashlib.sha256(screenshot.read_bytes()).hexdigest()
    assert receipt["egress_attestation"]["attestation_id"] == "attestation:test-001"
    assert receipt["data_lifecycle"]["lifecycle_id"] == "capture-test"
    assert str(tmp_path) not in receipt_path.read_text(encoding="utf-8")


# ─── Redirect SSRF revalidation (v1.7.1 hardening) ──────────────────────────


def test_fetch_page_blocks_redirect_to_private_ip(monkeypatch):
    """fetch_page() must re-validate every redirect hop, not just the initial URL.

    Pre-v1.7.1, requests' built-in follow-redirects path silently fetched
    `Location: http://169.254.169.254/` and similar. After the fix, fetch_page
    refuses to follow a redirect into the SSRF blocklist.
    """
    from unittest.mock import MagicMock
    import importlib
    fetch_page_module = importlib.import_module("fetch_page")

    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}
    redirect_response.url = "https://example.com/"

    class FakeSession:
        def mount(self, prefix, adapter):
            self.adapter = adapter

        def get(self, *args, **kwargs):
            return redirect_response

    monkeypatch.setattr(fetch_page_module.requests, "Session", FakeSession)

    # Initial URL must pass validation (example.com resolves to a public IP).
    try:
        validate_url("https://example.com/")
    except ValueError as exc:
        if "DNS" in str(exc) or "resolve" in str(exc).lower():
            pytest.skip("No network access for DNS resolution of example.com")
        raise

    result = fetch_page_module.fetch_page("https://example.com/", timeout=5)
    assert result["error"] is not None, "expected blocked-redirect error"
    assert "Blocked redirect" in result["error"]
    # The destination IP must not leak in raw form (sanitize_error redacts)
    # but the operator should at least know it was blocked.
    assert result["status_code"] is None
    assert result["content"] is None


def test_fetch_page_allows_redirect_to_public_ip(monkeypatch):
    """A redirect chain that stays on public addresses should succeed."""
    from unittest.mock import MagicMock
    import importlib
    fetch_page_module = importlib.import_module("fetch_page")

    final_response = MagicMock()
    final_response.status_code = 200
    final_response.headers = {}
    final_response.text = "<html>ok</html>"
    final_response.url = "https://example.com/final"

    class FakeSession:
        def __init__(self):
            self.calls = 0

        def mount(self, prefix, adapter):
            self.adapter = adapter

        def get(self, *args, **kwargs):
            return final_response

    monkeypatch.setattr(fetch_page_module.requests, "Session", FakeSession)

    try:
        validate_url("https://example.com/")
    except ValueError as exc:
        if "DNS" in str(exc) or "resolve" in str(exc).lower():
            pytest.skip("No network access for DNS resolution of example.com")
        raise

    result = fetch_page_module.fetch_page("https://example.com/", timeout=5)
    assert result["error"] is None
    assert result["status_code"] == 200
    assert result["content"] == "<html>ok</html>"
