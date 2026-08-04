#!/usr/bin/env python3
# Defensive use only. Enriches file HASHES via VirusTotal — it does not upload
# files. `hash-file` computes hashes locally and never transmits the file.
# Use only for IOCs you are authorized to investigate.
#
# Hardening vs. the original:
#   - API key read from env var VT_API_KEY (not a CLI arg that leaks to shell
#     history / process list).
#   - Dependency pinned in requirements.txt.
#   - Network timeouts and graceful errors retained.
"""VirusTotal v3 hash enrichment (read-only)."""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

VT_API_URL = "https://www.virustotal.com/api/v3"


def _get_api_key():
    key = os.environ.get("VT_API_KEY", "").strip()
    if not key:
        sys.exit("error: set VT_API_KEY in your environment (do not pass keys as arguments)")
    return key


class VirusTotalClient:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({"x-apikey": api_key, "Accept": "application/json"})

    def get_file_report(self, file_hash):
        resp = self.session.get(f"{VT_API_URL}/files/{file_hash}", timeout=30)
        if resp.status_code == 404:
            return {"hash": file_hash, "found": False}
        resp.raise_for_status()
        attrs = resp.json().get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})
        return {
            "hash": file_hash,
            "found": True,
            "sha256": attrs.get("sha256"),
            "md5": attrs.get("md5"),
            "sha1": attrs.get("sha1"),
            "file_type": attrs.get("type_description"),
            "size": attrs.get("size"),
            "meaningful_name": attrs.get("meaningful_name"),
            "detection_ratio": f"{stats.get('malicious', 0)}/{sum(stats.values()) or 0}",
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "undetected": stats.get("undetected", 0),
            "first_seen": attrs.get("first_submission_date"),
            "last_analysis_date": attrs.get("last_analysis_date"),
            "tags": attrs.get("tags", []),
            "popular_threat_classification": attrs.get("popular_threat_classification", {}),
        }

    def get_file_behavior(self, file_hash):
        resp = self.session.get(f"{VT_API_URL}/files/{file_hash}/behaviours", timeout=30)
        resp.raise_for_status()
        out = []
        for b in resp.json().get("data", [])[:5]:
            a = b.get("attributes", {})
            out.append({
                "sandbox": a.get("sandbox_name"),
                "processes_created": a.get("processes_created", [])[:10],
                "files_written": a.get("files_written", [])[:10],
                "registry_keys_set": a.get("registry_keys_set", [])[:10],
                "dns_lookups": a.get("dns_lookups", [])[:10],
                "http_conversations": a.get("http_conversations", [])[:10],
            })
        return {"hash": file_hash, "behaviors": out}


def enrich_bulk(client, hashes, rate_limit=4):
    results = []
    for i, h in enumerate(x.strip() for x in hashes if x.strip()):
        try:
            results.append(client.get_file_report(h))
        except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
            results.append({"hash": h, "error": str(exc)})
        if rate_limit and (i + 1) % rate_limit == 0:
            time.sleep(60)  # VT free tier: ~4 req/min
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_hashes": len(results),
        "found": sum(1 for r in results if r.get("found")),
        "malicious": sum(1 for r in results if r.get("malicious", 0) > 0),
        "results": results,
    }


def hash_file(filepath):
    algos = {"md5": hashlib.md5(), "sha1": hashlib.sha1(), "sha256": hashlib.sha256()}
    with open(filepath, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            for a in algos.values():
                a.update(chunk)
    return {name: a.hexdigest() for name, a in algos.items()}


def main():
    ap = argparse.ArgumentParser(description="VirusTotal hash enrichment (read-only)")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("lookup"); p.add_argument("--hash", required=True)
    p = sub.add_parser("bulk"); p.add_argument("--hashes", nargs="+", required=True); p.add_argument("--rate-limit", type=int, default=4)
    p = sub.add_parser("behavior"); p.add_argument("--hash", required=True)
    p = sub.add_parser("hash-file"); p.add_argument("--file", required=True)
    args = ap.parse_args()

    # hash-file is fully local and needs no API key.
    if args.command == "hash-file":
        print(json.dumps(hash_file(args.file), indent=2))
        return

    if requests is None:
        sys.exit("error: requests not installed — run: pip install -r requirements.txt")

    client = VirusTotalClient(_get_api_key())
    if args.command == "lookup":
        result = client.get_file_report(args.hash)
    elif args.command == "bulk":
        result = enrich_bulk(client, args.hashes, args.rate_limit)
    elif args.command == "behavior":
        result = client.get_file_behavior(args.hash)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
