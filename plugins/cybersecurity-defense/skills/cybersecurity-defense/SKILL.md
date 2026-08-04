---
name: cybersecurity-defense
description: Defensive cybersecurity playbooks for blue-team and security-operations
  work — cloud incident response (AWS/Azure/GCP), Linux host forensics, DNS-tunneling
  threat hunting with Zeek, authentication-anomaly detection, ISO 27001 ISMS setup,
  and VirusTotal malware-hash enrichment. Use this skill whenever the user is
  investigating a possible breach or compromise, responding to a security incident,
  hunting for malicious activity in logs, triaging a host, enriching IOCs or file
  hashes, detecting suspicious logins, or preparing for ISO 27001 / security
  compliance — even when they don't name a specific technique. Defensive use only.
license: Apache-2.0
metadata:
  provenance: Compacted and hardened from the community Anthropic-Cybersecurity-Skills repo (not an Anthropic project).
---

# Cybersecurity Defense

A set of six defensive playbooks. Each lives in `references/` so you only load the
one the task needs — read the relevant file in full before acting on it, since each
carries its own workflow, commands, and safety notes.

**Scope:** defensive only (detection, response, forensics, hardening, compliance).
There is deliberately no offensive/exploitation tooling here. Always operate on
systems and data you own or are explicitly authorized to handle, and treat the
guidance as a starting point to verify, not gospel — it's community-derived.

## Pick the right playbook

| If the user is… | Read |
|---|---|
| Responding to a breach in AWS / Azure / GCP — suspicious API calls, compromised keys, public buckets, crypto-mining | `references/cloud-incident-response.md` |
| Triaging a possibly-compromised Linux host — processes, persistence, logs, timeline | `references/linux-forensic-artifacts.md` |
| Hunting covert DNS channels / exfiltration in Zeek `dns.log` | `references/dns-tunneling-hunt.md` |
| Investigating suspicious logins — password spraying, brute force, impossible travel, MFA fatigue | `references/auth-anomaly-detection.md` |
| Standing up or certifying an ISO/IEC 27001 ISMS (scope, risk, SoA, Annex A) | `references/iso-27001-isms.md` |
| Enriching file hashes / IOCs with VirusTotal detection + sandbox behavior | `references/malware-hash-enrichment.md` |

If a task spans several areas (e.g. a cloud breach involving suspicious logins and
malware), read each relevant playbook and combine them — containment first, then
investigation, then eradication and hardening.

Four playbooks have a deeper reference under `references/detail/` (exact commands,
event IDs, detection queries, thresholds, the full ISO Annex A control list) plus a
blank ISO audit checklist in `assets/`. Each playbook points to its detail file —
load it only when the task needs that level of specificity, to keep context lean.

## Bundled script

`scripts/vt_enrich.py` performs read-only VirusTotal hash enrichment (it never
uploads files). It reads the API key from the `VT_API_KEY` environment variable —
never pass keys as command-line arguments, which leak into shell history and the
process list. Install its one pinned dependency first:

```bash
pip install -r scripts/requirements.txt
export VT_API_KEY="..."
python scripts/vt_enrich.py lookup --hash <sha256>
```

The `malware-hash-enrichment` playbook explains how to interpret the output.
