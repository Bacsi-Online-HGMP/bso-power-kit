"""Shared URL validation utilities with SSRF protection.

Used by fetch_page.py, analyze_landing.py, capture_screenshot.py, and
generate_image.py to validate user-supplied URLs before making HTTP requests
or launching browsers, and to sanitize exception messages before surfacing
them to the user.
"""

import ipaddress
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import socket
import stat
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - attested browser calls fail closed below
    InvalidSignature = ValueError  # type: ignore[assignment,misc]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.exceptions import InvalidURL
except ImportError:  # pragma: no cover - callers surface their dependency error
    requests = None
    HTTPAdapter = object  # type: ignore[assignment,misc]

    class InvalidURL(ValueError):
        """Fallback used only when Requests is not installed."""

# Sensitive substrings to redact from any error message before logging or
# returning to the caller. Catches common credential parameter names (api_key,
# apikey, access_token, refresh_token, auth, key, token, secret, password,
# OAuth `code=`, AWS `signature=`) and bare `Bearer <token>` headers
# regardless of case.
_SENSITIVE_PATTERN = re.compile(
    r'\b(api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|auth|key|token|secret|password|code|signature)'
    r'\s*[=:]\s*[\"\']?(?:Bearer\s+)?[^\s&,;\"\']+|\bBearer\s+[^\s,;]+',
    re.IGNORECASE,
)

_TOKEN_PATTERN = re.compile(
    r"\b(?:sk[_-](?:live[_-])?|gh[pousr]_|AIza)[A-Za-z0-9._-]{8,}\b",
    re.IGNORECASE,
)

_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)

_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}


def _redact_sensitive(text: str) -> str:
    """Run the credential-redaction regex over arbitrary text."""
    text = _PRIVATE_KEY_PATTERN.sub("[REDACTED PRIVATE KEY]", text)
    text = _SENSITIVE_PATTERN.sub(
        lambda m: (
            "authorization=Bearer ***"
            if m.group(1) and m.group(1).lower() == "authorization" and "bearer" in m.group(0).lower()
            else (m.group(1).lower().replace('-', '_') + '=***')
            if m.group(1)
            else 'Bearer ***'
        ),
        text,
    )
    return _TOKEN_PATTERN.sub("***", text)


def redact_sensitive_text(value: Any) -> str:
    """Return a log-safe string with common credentials removed."""
    return _redact_sensitive(str(value))


def sanitize_error(err: Exception) -> str:
    """Strip potential API keys / tokens / passwords from an exception message.

    Use whenever an exception's str() reaches stdout, JSON output, or a user-
    facing error field. The redaction is irreversible — the goal is to make
    the message safe to log, not to preserve the original details.

    Args:
        err: The exception to format.

    Returns:
        The exception string with sensitive substrings replaced.
    """
    return redact_sensitive_text(err)


def sanitize_headers(headers: Any) -> dict[str, str]:
    """Return response/request headers with credential-bearing values removed."""
    sanitized: dict[str, str] = {}
    for name, value in dict(headers or {}).items():
        key = str(name)
        if key.lower() in _SENSITIVE_HEADERS:
            sanitized[key] = "***"
        else:
            sanitized[key] = redact_sensitive_text(value)
    return sanitized


def sanitize_url(url: str) -> str:
    """Strip credentials from a URL string before logging it to stderr or stdout.

    Covers tokens embedded in query parameters (`?access_token=...&code=...`)
    and userinfo (`https://user:password@host/`). The output is meant to be
    safe to surface in CLI output, logs, or transcripts — not round-trippable.

    Args:
        url: The URL to sanitize.

    Returns:
        URL with credential-bearing values replaced by `***`.
    """
    # Drop userinfo segment if present (https://user:pass@host -> https://host)
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        netloc = parsed.hostname or ''
        try:
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
        except ValueError:
            # The URL will be rejected by validate_url; redaction must still
            # be fail-safe and never expose userinfo while formatting errors.
            pass
        url = parsed._replace(netloc=netloc).geturl()
    # Redact sensitive query/fragment parameters and token-looking values.
    return _redact_sensitive(url)

_MAX_URL_LENGTH = 8192
_LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata", "metadata.google.internal"}

_ATTESTATION_VERIFIED = object()
_ATTESTATION_MAX_BYTES = 64 * 1024
_ATTESTATION_MAX_LIFETIME_SECONDS = 24 * 60 * 60
_ATTESTATION_CONTROL_KEYS = {
    "blocks_link_local",
    "blocks_loopback",
    "blocks_metadata",
    "blocks_private",
    "blocks_reserved",
    "covers_ipv4",
    "covers_ipv6",
    "covers_redirects",
    "covers_subresources",
    "fail_closed",
    "prevents_dns_rebinding",
    "public_only_after_dns",
}


@dataclass(frozen=True)
class EgressSandboxAttestation:
    """Verified, short-lived authority to dispatch Chromium network requests.

    Instances returned by :func:`load_egress_sandbox_attestation` are bound to
    one externally named execution environment and an authenticated document.
    Constructing this dataclass directly does not create a valid authority.
    """

    attestation_id: str
    issuer_id: str
    key_id: str
    environment_id: str
    issued_at: datetime
    expires_at: datetime
    document_sha256: str
    _verification_marker: object = field(repr=False, compare=False)

    def audit_reference(self) -> dict[str, str]:
        """Return non-secret metadata suitable for an operation receipt."""
        _require_verified_egress_attestation(self)
        return {
            "attestation_id": self.attestation_id,
            "issuer_id": self.issuer_id,
            "key_id": self.key_id,
            "environment_id": self.environment_id,
            "issued_at": _format_utc(self.issued_at),
            "expires_at": _format_utc(self.expires_at),
            "document_sha256": self.document_sha256,
        }


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"Egress attestation {field_name} must be an RFC 3339 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"Egress attestation {field_name} must be an RFC 3339 timestamp."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Egress attestation {field_name} must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _decode_b64url(value: str, field_name: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Egress attestation {field_name} must be base64url text.")
    try:
        padding = "=" * (-len(value) % 4)
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Egress attestation {field_name} is not valid base64url.") from exc
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if canonical != value.rstrip("="):
        raise ValueError(f"Egress attestation {field_name} is not canonical base64url.")
    return decoded


def _read_attestation_document(path: str | os.PathLike[str]) -> bytes:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise ValueError("Egress attestation document must not be a symlink.")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise ValueError(f"Cannot open egress attestation document: {sanitize_error(exc)}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Egress attestation document must be a regular file.")
        if metadata.st_size > _ATTESTATION_MAX_BYTES:
            raise ValueError("Egress attestation document is too large.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(_ATTESTATION_MAX_BYTES + 1)
        if len(data) > _ATTESTATION_MAX_BYTES:
            raise ValueError("Egress attestation document is too large.")
        return data
    finally:
        os.close(descriptor)


def _canonical_attestation_payload(document: dict[str, Any]) -> bytes:
    authenticated = json.loads(json.dumps(document))
    authentication = authenticated.get("authentication")
    if not isinstance(authentication, dict):
        raise ValueError("Egress attestation authentication must be an object.")
    authentication.pop("signature_b64url", None)
    return json.dumps(
        authenticated,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def load_egress_sandbox_attestation(
    path: str | os.PathLike[str],
    *,
    public_key_b64url: str | None = None,
    expected_key_id: str | None = None,
    expected_environment_id: str | None = None,
    now: datetime | None = None,
) -> EgressSandboxAttestation:
    """Load and authenticate a browser egress-sandbox attestation.

    Trust material is deliberately external to the attestation document. By
    default the Ed25519 public key, its accountable key identifier, and the
    execution environment identifier come from
    ``CLAUDE_ADS_EGRESS_ATTESTATION_PUBLIC_KEY_B64URL``,
    ``CLAUDE_ADS_EGRESS_ATTESTATION_KEY_ID``, and
    ``CLAUDE_ADS_EGRESS_ENVIRONMENT_ID``. A document cannot authorize itself by
    embedding a different key.
    """
    raw = _read_attestation_document(path)
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Egress attestation document must be valid UTF-8 JSON.") from exc
    if not isinstance(document, dict):
        raise ValueError("Egress attestation document must be a JSON object.")

    required_top_level = {
        "schema_version",
        "attestation_id",
        "audience",
        "issuer_id",
        "environment_id",
        "issued_at",
        "not_before",
        "expires_at",
        "enforcement_boundary",
        "controls",
        "evidence_refs",
        "authentication",
    }
    if set(document) != required_top_level:
        missing = sorted(required_top_level - set(document))
        unexpected = sorted(set(document) - required_top_level)
        detail = []
        if missing:
            detail.append(f"missing {', '.join(missing)}")
        if unexpected:
            detail.append(f"unexpected {', '.join(unexpected)}")
        raise ValueError("Invalid egress attestation fields: " + "; ".join(detail))
    if document["schema_version"] != "1.0.0":
        raise ValueError("Unsupported egress attestation schema version.")
    if document["audience"] != "claude-ads-browser-egress":
        raise ValueError("Egress attestation has the wrong audience.")

    for field_name in ("attestation_id", "issuer_id", "environment_id"):
        value = document[field_name]
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{2,127}", value):
            raise ValueError(f"Egress attestation {field_name} is invalid.")
    if document["enforcement_boundary"] not in {
        "container-network-policy",
        "host-firewall",
        "isolated-network-proxy",
    }:
        raise ValueError("Egress attestation enforcement_boundary is unsupported.")

    controls = document["controls"]
    if not isinstance(controls, dict) or set(controls) != _ATTESTATION_CONTROL_KEYS:
        raise ValueError("Egress attestation must declare the complete browser control set.")
    if any(value is not True for value in controls.values()):
        raise ValueError("Every egress attestation browser control must be true.")
    evidence_refs = document["evidence_refs"]
    if (
        not isinstance(evidence_refs, list)
        or not evidence_refs
        or len(evidence_refs) > 20
        or any(not isinstance(item, str) or not item.strip() or len(item) > 512 for item in evidence_refs)
    ):
        raise ValueError("Egress attestation evidence_refs must contain 1-20 references.")

    issued_at = _parse_utc(document["issued_at"], "issued_at")
    not_before = _parse_utc(document["not_before"], "not_before")
    expires_at = _parse_utc(document["expires_at"], "expires_at")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not issued_at <= not_before < expires_at:
        raise ValueError("Egress attestation validity timestamps are inconsistent.")
    if (expires_at - issued_at).total_seconds() > _ATTESTATION_MAX_LIFETIME_SECONDS:
        raise ValueError("Egress attestation validity exceeds 24 hours.")
    if current < not_before:
        raise ValueError("Egress attestation is not yet valid.")
    if current >= expires_at:
        raise ValueError("Egress attestation has expired.")

    authentication = document["authentication"]
    if not isinstance(authentication, dict) or set(authentication) != {
        "algorithm",
        "key_id",
        "signature_b64url",
    }:
        raise ValueError("Egress attestation authentication fields are invalid.")
    if authentication["algorithm"] != "ed25519":
        raise ValueError("Unsupported egress attestation authentication algorithm.")

    trusted_key_id = expected_key_id or os.environ.get("CLAUDE_ADS_EGRESS_ATTESTATION_KEY_ID")
    trusted_environment = expected_environment_id or os.environ.get(
        "CLAUDE_ADS_EGRESS_ENVIRONMENT_ID"
    )
    encoded_key = public_key_b64url or os.environ.get(
        "CLAUDE_ADS_EGRESS_ATTESTATION_PUBLIC_KEY_B64URL"
    )
    if not trusted_key_id or not trusted_environment or not encoded_key:
        raise ValueError(
            "External egress attestation trust material is incomplete; public key, key ID, "
            "and environment ID are required."
        )
    if authentication["key_id"] != trusted_key_id:
        raise ValueError("Egress attestation key ID is not trusted.")
    if document["environment_id"] != trusted_environment:
        raise ValueError("Egress attestation is bound to another environment.")

    if Ed25519PublicKey is None:
        raise ValueError(
            "The cryptography package is required to verify egress attestations."
        )
    public_key_bytes = _decode_b64url(encoded_key, "trust public key")
    if len(public_key_bytes) != 32:
        raise ValueError("Egress attestation Ed25519 public key must be 32 bytes.")
    signature = _decode_b64url(authentication["signature_b64url"], "signature_b64url")
    if len(signature) != 64:
        raise ValueError("Egress attestation Ed25519 signature must be 64 bytes.")
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
            signature,
            _canonical_attestation_payload(document),
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("Egress attestation authentication failed.") from exc

    return EgressSandboxAttestation(
        attestation_id=document["attestation_id"],
        issuer_id=document["issuer_id"],
        key_id=authentication["key_id"],
        environment_id=document["environment_id"],
        issued_at=issued_at,
        expires_at=expires_at,
        document_sha256=hashlib.sha256(raw).hexdigest(),
        _verification_marker=_ATTESTATION_VERIFIED,
    )


def _require_verified_egress_attestation(
    attestation: EgressSandboxAttestation | None,
    *,
    now: datetime | None = None,
) -> EgressSandboxAttestation:
    if (
        not isinstance(attestation, EgressSandboxAttestation)
        or attestation._verification_marker is not _ATTESTATION_VERIFIED
    ):
        raise ValueError(
            "Browser request blocked: a verified egress-sandbox attestation document is required."
        )
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= attestation.expires_at:
        raise ValueError("Browser request blocked: the egress-sandbox attestation has expired.")
    return attestation


def _validate_and_resolve_url(url: str) -> tuple[str, Any, tuple[str, ...]]:
    """Validate a URL and return every public address from one DNS snapshot.

    The returned addresses are suitable for connection pinning. Callers must
    not validate the hostname here and then resolve it again while connecting:
    doing so would recreate the DNS rebinding/TOCTOU window this helper exists
    to close.
    """
    if not isinstance(url, str):
        raise ValueError("URL must be a string.")
    url = url.strip()
    if not url or len(url) > _MAX_URL_LENGTH:
        raise ValueError("URL is empty or too long.")
    if any(ord(char) < 32 for char in url) or "\\" in url:
        raise ValueError("URL contains forbidden control characters or backslashes.")

    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials in URLs are not allowed.")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("URL has an invalid port.") from exc

    normalized_hostname = hostname.rstrip(".").lower()
    if normalized_hostname in _LOCAL_HOSTNAMES or normalized_hostname.endswith(".localhost"):
        raise ValueError("URL targets a local/internal hostname.")
    try:
        resolved = socket.getaddrinfo(
            normalized_hostname,
            None,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for {normalized_hostname}: {exc}") from exc
    if not resolved:
        raise ValueError(f"DNS resolution returned no addresses for {normalized_hostname}")

    addresses: list[str] = []
    for _, _, _, _, addr in resolved:
        ip = ipaddress.ip_address(addr[0])
        # is_global rejects loopback, private, link-local, multicast,
        # documentation, benchmark, CGNAT, unspecified, and reserved space.
        if not ip.is_global or ip.is_multicast or ip.is_reserved:
            raise ValueError(f"URL resolves to blocked non-public IP: {ip}")
        canonical = str(ip)
        if canonical not in addresses:
            addresses.append(canonical)
    return url, parsed, tuple(addresses)


def validate_url(url: str) -> str:
    """Validate URL scheme and block private/internal IPs (SSRF protection).

    Args:
        url: The URL to validate. If no scheme, https:// is prepended.

    Returns:
        The validated URL string (with scheme).

    Raises:
        ValueError: If URL has invalid scheme, no hostname, resolves to
                    a blocked IP, or DNS resolution fails.
    """
    validated, _, _ = _validate_and_resolve_url(url)
    return validated


def validate_browser_url(
    url: str,
    *,
    egress_attestation: EgressSandboxAttestation | None = None,
) -> str:
    """Validate a URL at the strongest boundary Playwright can enforce.

    Playwright route interception sees a URL before Chromium performs its own
    DNS lookup, but it cannot pin the later socket to the address Python
    validated. Browser dispatch is therefore denied by default, including for
    public IP literals. Callers may proceed only with a short-lived document
    authenticated by an externally provisioned trust key and bound to the
    current execution environment. The document attests that an independent
    OS/container boundary blocks non-public destinations after DNS resolution
    and across redirects. This module authenticates and records that claim; it
    cannot establish the external sandbox itself.
    """
    _require_verified_egress_attestation(egress_attestation)
    validated, _, _ = _validate_and_resolve_url(url)
    return validated


def _origin_prefix(parsed: Any) -> str:
    """Return the exact Requests adapter mount prefix for a parsed origin."""
    # Preserve an explicitly written default port and a trailing DNS dot. A
    # normalized prefix such as ``https://example.com/`` does not match
    # Requests' URL ``https://example.com:443/`` and would silently fall
    # through to the ordinary, unpinned HTTPS adapter.
    return f"{parsed.scheme}://{parsed.netloc.lower()}/"


class _PinnedHTTPAdapter(HTTPAdapter):
    """Requests adapter that connects to a validated IP without re-resolving.

    The request URL and HTTP Host header remain hostname-based. For HTTPS,
    ``server_hostname`` preserves SNI and ``assert_hostname`` preserves normal
    certificate hostname verification while the pool's socket target is the
    pinned numeric address.
    """

    def __init__(self, parsed: Any, addresses: tuple[str, ...]) -> None:
        if HTTPAdapter is object:  # pragma: no cover - dependency guard
            raise RuntimeError("requests is required for guarded HTTP requests")
        super().__init__()
        self._scheme = parsed.scheme
        self._hostname = parsed.hostname.rstrip(".").lower()
        self._port = parsed.port
        self._address = addresses[0]

    def _check_request_origin(self, request: Any) -> Any:
        parsed = urlparse(request.url)
        hostname = (parsed.hostname or "").rstrip(".").lower()
        if (
            parsed.scheme != self._scheme
            or hostname != self._hostname
            or parsed.port != self._port
        ):
            raise InvalidURL("Pinned adapter cannot be reused for another origin.")
        return parsed

    def get_connection_with_tls_context(
        self,
        request: Any,
        verify: Any,
        proxies: Any = None,
        cert: Any = None,
    ) -> Any:
        parsed = self._check_request_origin(request)
        if proxies:
            raise InvalidURL("Proxies are forbidden for guarded requests.")
        if parsed.scheme == "https" and verify is False:
            raise InvalidURL("TLS certificate verification cannot be disabled.")

        host_params, pool_kwargs = self.build_connection_pool_key_attributes(
            request,
            verify,
            cert,
        )
        host_params["host"] = self._address
        if parsed.scheme == "https":
            pool_kwargs["server_hostname"] = self._hostname
            pool_kwargs["assert_hostname"] = self._hostname

        # PreparedRequest does not add Host itself; urllib3 would otherwise
        # derive it from the pinned IP pool and break virtual hosting.
        default_port = 443 if parsed.scheme == "https" else 80
        bracketed = f"[{self._hostname}]" if ":" in self._hostname else self._hostname
        request.headers["Host"] = (
            bracketed
            if parsed.port in (None, default_port)
            else f"{bracketed}:{parsed.port}"
        )
        return self.poolmanager.connection_from_host(
            **host_params,
            pool_kwargs=pool_kwargs,
        )


def guarded_request(session: Any, method: str, url: str, **kwargs: Any) -> Any:
    """Validate and address-pin an outbound Requests dispatch.

    Automatic redirects are disabled because every redirect target must return
    to this boundary for a fresh validation. The adapter connects to an IP from
    the same DNS snapshot that passed policy, closing the validation/connect
    TOCTOU window without changing Host, SNI, or TLS hostname verification.
    """
    if requests is None:  # pragma: no cover - dependency guard
        raise ValueError("requests is required for guarded HTTP requests.")
    if not isinstance(url, str):
        raise ValueError("URL must be a string.")
    raw_url = url.strip()
    if any(ord(char) < 32 for char in raw_url) or "\\" in raw_url:
        raise ValueError("URL contains forbidden control characters or backslashes.")
    if not urlparse(raw_url).scheme:
        raw_url = f"https://{raw_url}"
    try:
        # Requests canonicalizes IDNs before adapter selection. Validate and
        # mount against that same form; mounting the caller's Unicode netloc
        # would let the prepared punycode URL fall through to the default
        # unpinned adapter.
        canonical_url = requests.Request(method.upper(), raw_url).prepare().url
    except (requests.exceptions.RequestException, ValueError) as exc:
        raise ValueError(f"Invalid URL: {sanitize_error(exc)}") from exc

    validated, parsed, addresses = _validate_and_resolve_url(canonical_url)
    if kwargs.get("allow_redirects") is True:
        raise ValueError("Automatic redirects are forbidden for guarded requests.")
    if parsed.scheme == "https" and kwargs.get("verify") is False:
        raise ValueError("TLS certificate verification cannot be disabled.")
    if kwargs.get("proxies"):
        raise ValueError("Proxies are forbidden for guarded requests.")
    kwargs["allow_redirects"] = False

    if not hasattr(session, "mount"):
        # Existing callers historically passed the requests module. Replace it
        # with an isolated Session rather than using the module-level pool,
        # which cannot be safely pinned.
        if requests is None or session is not requests:
            raise ValueError("guarded_request requires requests.Session.")
        session = requests.Session()
        session.trust_env = False

    adapter = _PinnedHTTPAdapter(parsed, addresses)
    session.mount(_origin_prefix(parsed), adapter)
    get_adapter = getattr(session, "get_adapter", None)
    if get_adapter is not None and get_adapter(validated) is not adapter:
        raise ValueError("Pinned adapter selection failed; request denied.")
    dispatcher = getattr(session, method.lower(), None)
    if dispatcher is None:
        raise ValueError(f"Unsupported HTTP method: {method}")
    return dispatcher(validated, **kwargs)


def install_playwright_ssrf_guard(
    context: Any,
    *,
    egress_attestation: EgressSandboxAttestation | None = None,
) -> list[dict[str, str]]:
    """Screen every Playwright request before dispatch.

    Context-level routing covers the main frame, redirects, child frames, and
    subresources. Callers must create the context with service workers blocked,
    because service-worker initiated requests can bypass Playwright routing.
    The returned list records sanitized blocked requests for user-facing errors.
    """
    blocked: list[dict[str, str]] = []

    def guard(route: Any, request: Any = None) -> None:
        outbound = request or route.request
        try:
            validate_browser_url(
                outbound.url,
                egress_attestation=egress_attestation,
            )
        except (TypeError, ValueError) as exc:
            blocked.append({"url": sanitize_url(str(outbound.url)), "error": sanitize_error(exc)})
            route.abort("blockedbyclient")
            return
        route.continue_()

    context.route("**/*", guard)
    return blocked


def create_guarded_browser_context(browser: Any, **kwargs: Any) -> tuple[Any, list[dict[str, str]]]:
    """Create a guarded Playwright context.

    ``egress_attestation`` is consumed here rather than passed to Playwright.
    Its default is intentionally absent, which makes every browser request
    fail closed at the route boundary.
    """
    egress_attestation = kwargs.pop("egress_attestation", None)
    _require_verified_egress_attestation(egress_attestation)
    kwargs.setdefault("service_workers", "block")
    kwargs.setdefault("accept_downloads", False)
    context = browser.new_context(**kwargs)
    return context, install_playwright_ssrf_guard(
        context,
        egress_attestation=egress_attestation,
    )


def output_root(root: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the only directory in which generated artifacts may be written."""
    configured = root or os.environ.get("CLAUDE_ADS_OUTPUT_ROOT") or os.getcwd()
    return Path(configured).expanduser().resolve()


def resolve_output_path(
    path: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] | None = None,
    create_parent: bool = False,
) -> Path:
    """Resolve an output path and reject traversal or symlink escapes.

    Relative paths are anchored to ``CLAUDE_ADS_OUTPUT_ROOT`` (or the current
    directory). Absolute paths are accepted only when they remain inside that
    root. Existing symlinks are resolved before the containment check.
    """
    base = output_root(root)
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Output path escapes configured root: {candidate}") from exc
    if create_parent:
        candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def artifact_locator(
    path: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] | None = None,
) -> str:
    """Return a repository/run-relative locator without disclosing a local path."""
    base = output_root(root)
    candidate = resolve_output_path(path, root=base)
    return candidate.relative_to(base).as_posix()
