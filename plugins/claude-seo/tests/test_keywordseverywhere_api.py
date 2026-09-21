"""Keywords Everywhere (Open PageRank) API client regressions.

Covers the fallback backlinks source added for #262: a successful lookup,
an authentication error, a rate-limit response, and the 100-domain batch
cap. The success/error/rate-limit bodies below are recorded shapes from
the Open PageRank API docs (https://www.domcop.com/openpagerank/documentation),
which Keywords Everywhere's endpoint is a drop-in continuation of.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

pytest.importorskip("requests")
import keywordseverywhere_api  # noqa: E402
from url_safety import URLSafetyError  # noqa: E402

# Recorded success response for a single-domain rank lookup.
RECORDED_SUCCESS_RESPONSE = {
    "status_code": 200,
    "last_updated": "26th August 2026",
    "response": [
        {
            "status_code": 200,
            "error": "",
            "page_rank_decimal": 4.68,
            "domain": "example.com",
            "rank": "4",
            "page_rank_integer": 5,
        }
    ],
}

# Recorded auth-error body: Open PageRank returns this shape for a missing
# or invalid API-OPR header.
RECORDED_AUTH_ERROR_RESPONSE = {
    "status_code": 401,
    "message": "Invalid API Key or Domain limit reached",
}

# Recorded rate-limit body.
RECORDED_RATE_LIMIT_RESPONSE = {
    "status_code": 429,
    "message": "Rate limit exceeded",
}


class FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self) -> dict:
        return self._body


def test_get_rank_success_parses_recorded_response() -> None:
    fake = FakeResponse(200, RECORDED_SUCCESS_RESPONSE)
    with patch.object(keywordseverywhere_api, "safe_requests_get", return_value=fake) as mock_get:
        result = keywordseverywhere_api.get_rank(["example.com"], "opr_live_testkey")

    assert result["status"] == "success"
    assert result["error"] is None
    assert result["data"]["domains"] == [
        {
            "domain": "example.com",
            "page_rank_decimal": 4.68,
            "page_rank_integer": 5,
            "rank": "4",
        }
    ]
    assert result["metadata"]["source"] == "keywordseverywhere"
    # The API key must travel in the API-OPR header, never as a query param.
    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["API-OPR"] == "opr_live_testkey"


def test_get_rank_auth_error_maps_to_error_status() -> None:
    fake = FakeResponse(401, RECORDED_AUTH_ERROR_RESPONSE)
    with patch.object(keywordseverywhere_api, "safe_requests_get", return_value=fake):
        result = keywordseverywhere_api.get_rank(["example.com"], "bad-key")

    assert result["status"] == "error"
    assert result["data"] is None
    assert "Invalid Keywords Everywhere API key" in result["error"]


def test_get_rank_rate_limit_maps_to_rate_limited_status() -> None:
    fake = FakeResponse(429, RECORDED_RATE_LIMIT_RESPONSE)
    with patch.object(keywordseverywhere_api, "safe_requests_get", return_value=fake):
        result = keywordseverywhere_api.get_rank(["example.com"], "opr_live_testkey")

    assert result["status"] == "rate_limited"
    assert result["data"] is None
    assert result["metadata"]["rate_limited"] is True


def test_get_rank_ssrf_block_surfaces_as_error_not_a_crash() -> None:
    with patch.object(
        keywordseverywhere_api, "safe_requests_get", side_effect=URLSafetyError("blocked host")
    ):
        result = keywordseverywhere_api.get_rank(["example.com"], "opr_live_testkey")

    assert result["status"] == "error"
    assert "blocked by SSRF protection" in result["error"]


def test_main_rejects_batches_over_100_domains_without_a_network_call(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    domains = [f"d{i}.example.com" for i in range(101)]
    monkeypatch.setattr(sys, "argv", ["keywordseverywhere_api.py", "rank", *domains, "--json"])
    with patch.object(keywordseverywhere_api, "safe_requests_get") as mock_get:
        with pytest.raises(SystemExit) as exc_info:
            keywordseverywhere_api.main()

    assert exc_info.value.code == 1
    mock_get.assert_not_called()
    err = capsys.readouterr().err
    assert "101" in err
    assert "max 100" in err


def test_upstream_error_body_never_echoes_the_key(monkeypatch):
    """A 500 whose body repeats the key must not leak it into the result."""
    import keywordseverywhere_api as ke

    class _Resp:
        status_code = 500
        text = "upstream error: API-OPR opr_live_SECRET123 rejected"

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(ke, "safe_requests_get", lambda *a, **k: _Resp())
    result = ke.get_rank(["example.com"], api_key="opr_live_SECRET123")
    assert "opr_live_SECRET123" not in str(result)
    assert "<redacted>" in str(result.get("error", ""))
