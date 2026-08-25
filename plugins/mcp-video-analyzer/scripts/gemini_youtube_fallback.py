#!/usr/bin/env python3
"""Gemini native-YouTube fallback for the `video` skill (DOWNSTREAM ADDITION).

Not part of upstream mcp-video-analyzer. It exists because the MCP server / CLI
reach YouTube through yt-dlp: when yt-dlp is blocked (region lock, login wall,
age gate, throttling) or a long video has no captions and no Whisper backend,
they return an empty transcript. Gemini can ingest a public YouTube URL
*natively* — no download — so it covers exactly those gaps.

It is a last-resort lane, invoked by SKILL.md only after the normal tools come
back with no transcript for a YouTube URL. Gemini watches the video and returns
its own reading (a transcript, or an answer) — this is text from Gemini, not
frames the calling agent can re-inspect.

Usage:
    GEMINI_API_KEY=... python3 gemini_youtube_fallback.py <youtube-url>
    GEMINI_API_KEY=... python3 gemini_youtube_fallback.py <youtube-url> --ask "what happens at the end?"
    python3 gemini_youtube_fallback.py --selftest        # offline logic check, no key/network

Key resolution (first hit wins), so the secret stays out of Git and out of a
globally-exported shell var:
    1. GEMINI_API_KEY in the environment
    2. GEMINI_API_KEY=... in ~/.config/video-analyzer/.env  (chmod 600)
Get a key at https://aistudio.google.com/apikey.

On the free tier, RPM/RPD limits are per model, so several video analyses in a
row exhaust one model fast. The request cascades across a chain of DISTINCT
video-capable models (best -> lite); a per-model 429 (quota) or 5xx (congestion)
falls straight to the next model, multiplying effective throughput.

Env:
    GEMINI_API_KEY   the key (or put it in the .env above)
    GEMINI_MODEL     optional; the cascade's PRIMARY model (default
                     "gemini-flash-latest"). The built-in fallbacks follow it.
    GEMINI_MODELS    optional; comma-separated list that REPLACES the whole
                     cascade, in order (e.g. "gemini-3.5-flash,gemini-2.5-flash").

Stdlib only — no pip install. Exits non-zero (with a reason on stderr) on any
failure so the caller can tell "Gemini could not help" from a real transcript.
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

# Primary is the floating "latest" alias so it auto-tracks Google's newest Flash
# (currently gemini-3.7-flash) without a code edit.
DEFAULT_MODEL = "gemini-flash-latest"

# CASCADE of DISTINCT video-capable models, best -> lite. Free-tier RPM/RPD limits
# are PER MODEL, so cascading across separate models multiplies effective
# throughput: a single video analysis over 8 clips would blow one model's RPD,
# but each model here carries its own quota bucket. On a per-model 429 (quota) or
# 5xx (congestion) we fall straight to the next. Every entry was verified to
# ACCEPT VIDEO INPUT (gemini-2.5-flash-lite is excluded — it 404s on fileData).
# This list is deliberately version-pinned (the whole point is distinct buckets);
# refresh it when Google adds/removes Flash models, or override per-run with the
# GEMINI_MODELS env var (comma-separated) — no code edit needed.
FALLBACK_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
)


def resolve_models() -> list[str]:
    """The ordered, de-duplicated model cascade to try in turn.

    GEMINI_MODELS (comma-separated) overrides the whole cascade. Otherwise the
    cascade is GEMINI_MODEL-or-DEFAULT_MODEL as primary, then FALLBACK_MODELS.
    A model pinned as primary is not tried twice.
    """
    override = os.environ.get("GEMINI_MODELS", "").strip()
    if override:
        raw = [m.strip() for m in override.split(",")]
    else:
        primary = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        raw = [primary, *FALLBACK_MODELS]
    chain: list[str] = []
    for m in raw:
        if m and m not in chain:
            chain.append(m)
    return chain
API_HOST = "https://generativelanguage.googleapis.com"
TIMEOUT_SECONDS = 300
# Transient / quota statuses: 429 = rate or daily quota exhausted (RPM/RPD),
# 5xx = server congestion. Both mean "try another model", and are worth ONE
# backoff pass at the end (RPM windows reset, congestion eases). 404/400 mean the
# model rejects the request outright — skip permanently, never retry.
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
RETRY_BACKOFF_SECONDS = 8
CONFIG_ENV = os.path.expanduser("~/.config/video-analyzer/.env")


def read_dotenv_key(name: str, path: str = CONFIG_ENV) -> str | None:
    """Return KEY=value for `name` from a dotenv file, or None if absent/unreadable.

    Deliberately tiny: `KEY=value` lines, `#` comments, optional surrounding
    quotes. Not a full dotenv parser — this file holds one or two API keys.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == name:
                    return value.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def resolve_api_key() -> str:
    """Environment first, then the ~/.config dotenv. Empty string if neither."""
    return os.environ.get("GEMINI_API_KEY", "").strip() or read_dotenv_key("GEMINI_API_KEY") or ""


def ssl_context() -> ssl.SSLContext:
    """A verifying TLS context, using certifi's CA bundle when it is importable.

    The python.org macOS build ships no CA store (get_default_verify_paths() is
    empty), so a bare default context fails every HTTPS call with
    CERTIFICATE_VERIFY_FAILED. certifi carries the bundle and is present in that
    build's site-packages; fall back to the system default elsewhere. Never
    disables verification.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()

# Public single-video YouTube pages only, mirroring the repo's own url-detector.
# Playlists/channels are rejected — Gemini ingests one video, not a list.
_YOUTUBE_RE = re.compile(
    r"^https?://(?:(?:www\.|m\.)?youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/)[\w-]+"
    r"|youtu\.be/[\w-]+)",
    re.IGNORECASE,
)

TRANSCRIPT_PROMPT = (
    "Watch this video and produce a timestamped transcript of the speech. "
    "Output one line per spoken segment in the exact format `M:SS\ttext` "
    "(use H:MM:SS past one hour), timestamps measured from the start. "
    "Output only the transcript lines: no preamble, no commentary, no markdown."
)


def is_youtube_url(url: str) -> bool:
    """True only for a public single-video YouTube URL Gemini can ingest."""
    return bool(_YOUTUBE_RE.match(url.strip()))


def build_request(url: str, question: str | None, model: str, api_key: str):
    """Build the (endpoint_url, headers, body_bytes) for a generateContent call.

    The API key travels in the x-goog-api-key header, never in the URL, so it
    stays out of logs and proxies.
    """
    prompt = (
        f"{question.strip()}\n\nAnswer using both the audio and what is visible "
        "on screen. Cite timestamps as M:SS."
        if question
        else TRANSCRIPT_PROMPT
    )
    body = {
        "contents": [
            {
                "parts": [
                    {"fileData": {"fileUri": url}},
                    {"text": prompt},
                ]
            }
        ]
    }
    endpoint = f"{API_HOST}/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    return endpoint, headers, json.dumps(body).encode("utf-8")


def parse_response(payload: dict) -> str:
    """Pull the text out of a generateContent response, or raise with the reason.

    Handles the two ways Gemini declines: a top-level promptFeedback.blockReason
    (input rejected) and a candidate finishReason other than STOP with no text
    (output truncated/blocked). Both must surface, not read as an empty result.
    """
    feedback = payload.get("promptFeedback") or {}
    if feedback.get("blockReason"):
        raise RuntimeError(f"Gemini blocked the request: {feedback['blockReason']}")

    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        reason = candidates[0].get("finishReason", "unknown")
        raise RuntimeError(f"Gemini returned no text (finishReason={reason}).")
    return text


def attempt_model(url, question, model, api_key, ctx):
    """One request against one model. Returns (text, code, detail).

    On success text is the answer and code is 200. On failure text is None and
    (code, detail) explain it: an HTTP status (429/5xx = retryable, 404/400 =
    dead), 0 for a network error, or -1 when the model replied but blocked or
    returned no text (content issue — another model may still answer).
    """
    endpoint, headers, data = build_request(url, question, model, api_key)
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS, context=ctx) as resp:
            return parse_response(json.loads(resp.read().decode("utf-8"))), 200, ""
    except urllib.error.HTTPError as e:
        return None, e.code, e.read().decode("utf-8", "replace")[:150]
    except urllib.error.URLError as e:
        return None, 0, f"network: {e.reason}"
    except RuntimeError as e:  # parse_response: blocked / no text for this model
        return None, -1, str(e)


def run(url: str, question: str | None) -> str:
    api_key = resolve_api_key()
    if not api_key:
        raise SystemExit(
            "No Gemini API key. Export GEMINI_API_KEY, or put GEMINI_API_KEY=... in "
            f"{CONFIG_ENV} (chmod 600). Get one at https://aistudio.google.com/apikey."
        )
    if not is_youtube_url(url):
        raise SystemExit(
            f"Not a public single-video YouTube URL: {url}\n"
            "Gemini native ingestion only covers YouTube; use the normal tools for other sources."
        )

    ctx = ssl_context()
    models = resolve_models()
    retryable: list[str] = []  # models that hit quota/congestion — worth one more pass
    last = ""

    def note(model: str, primary: bool) -> None:
        if model != models[0] or not primary:
            sys.stderr.write(f"answered by fallback model: {model}\n")

    # Pass 1 — one shot per model, spreading across distinct free-tier quota
    # buckets. Fall straight through on 429 (quota) / 5xx (congestion); a hard
    # 404/400 means the model can't serve this request, so drop it for good.
    for model in models:
        text, code, detail = attempt_model(url, question, model, api_key, ctx)
        if text is not None:
            note(model, True)
            return text
        last = f"{model}: {code} {detail}"
        sys.stderr.write(f"{model} -> {code}, next\n")
        if code in RETRY_STATUS or code == 0:  # quota / congestion / network
            retryable.append(model)

    # Pass 2 — a single backoff pass over the quota/congestion failures only.
    # RPM windows reset and 503s ease within seconds; a persistent RPD 429 will
    # just fail again, which is the correct outcome (quota really is spent).
    if retryable:
        sys.stderr.write(f"all {len(models)} models busy; backing off {RETRY_BACKOFF_SECONDS}s\n")
        time.sleep(RETRY_BACKOFF_SECONDS)
        for model in retryable:
            text, code, detail = attempt_model(url, question, model, api_key, ctx)
            if text is not None:
                sys.stderr.write(f"answered by fallback model: {model} (2nd pass)\n")
                return text
            last = f"{model}: {code} {detail}"

    raise SystemExit(f"Gemini API failed across {len(models)} models (last: {last}).")


def _selftest() -> None:
    """Offline check of the non-trivial logic: URL gate, request shape, parsing."""
    assert is_youtube_url("https://youtu.be/abc123")
    assert is_youtube_url("https://www.youtube.com/watch?v=abc-DEF_9")
    assert is_youtube_url("https://youtube.com/shorts/xyz")
    assert not is_youtube_url("https://vimeo.com/12345")
    assert not is_youtube_url("https://www.youtube.com/playlist?list=PL1")

    endpoint, headers, data = build_request(
        "https://youtu.be/abc", None, DEFAULT_MODEL, "SECRET"
    )
    assert f"{DEFAULT_MODEL}:generateContent" in endpoint
    assert "abc" not in endpoint and "SECRET" not in endpoint  # url/key never in the URL
    assert headers["x-goog-api-key"] == "SECRET"
    body = json.loads(data)
    parts = body["contents"][0]["parts"]
    assert parts[0]["fileData"]["fileUri"] == "https://youtu.be/abc"
    assert "transcript" in parts[1]["text"].lower()  # default = transcript mode
    ask_body = json.loads(build_request("https://youtu.be/abc", "why?", "m", "k")[2])
    assert "why?" in ask_body["contents"][0]["parts"][1]["text"]  # --ask threads through

    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, ".env")
        with open(p, "w", encoding="utf-8") as f:
            f.write('# comment\nGEMINI_API_KEY = "abc123"\nGEMINI_MODEL=x\n')
        assert read_dotenv_key("GEMINI_API_KEY", p) == "abc123"  # trims spaces + quotes
        assert read_dotenv_key("MISSING", p) is None
        assert read_dotenv_key("GEMINI_API_KEY", os.path.join(d, "nope")) is None  # no file

    ctx = ssl_context()  # verifying context; certifi bundle when importable
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED

    chain = resolve_models()
    assert chain[0] == DEFAULT_MODEL  # floating-latest leads
    assert len(chain) == len(set(chain)) >= 5  # deduped, and a real cascade of buckets
    os.environ["GEMINI_MODEL"] = FALLBACK_MODELS[0]
    try:
        pinned = resolve_models()
        assert pinned[0] == FALLBACK_MODELS[0] and pinned.count(FALLBACK_MODELS[0]) == 1
    finally:
        del os.environ["GEMINI_MODEL"]
    os.environ["GEMINI_MODELS"] = "m-a, m-b ,m-a,m-c"  # whole-cascade override, trims + dedups
    try:
        assert resolve_models() == ["m-a", "m-b", "m-c"]
    finally:
        del os.environ["GEMINI_MODELS"]

    ok = {"candidates": [{"content": {"parts": [{"text": "0:00\thello"}]}}]}
    assert parse_response(ok) == "0:00\thello"

    for bad in (
        {"promptFeedback": {"blockReason": "SAFETY"}},
        {"candidates": []},
        {"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]},
    ):
        try:
            parse_response(bad)
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"expected parse_response to raise on {bad}")

    print("selftest ok")


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        _selftest()
        return 0
    args = [a for a in argv[1:] if a]
    question = None
    if "--ask" in args:
        i = args.index("--ask")
        question = args[i + 1] if i + 1 < len(args) else None
        del args[i : i + 2]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    print(run(args[0], question))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
