
# Authentication Anomaly Detection

**Safety:** operates on your own auth telemetry. Validate before locking accounts.

## When to use
You have authentication logs (Okta/Entra/Google SSO, VPN, Windows 4624/4625, Linux
auth) and want to surface account takeover and brute-force activity.

## Detections
- **Password spraying** — one→many: a few failed attempts across many accounts from
  one source in a short window.
- **Brute force** — many→one: high failed-auth count against a single account.
- **Impossible travel** — successful logins from geographically distant locations
  within a time too short to traverse.
- **MFA fatigue / bombing** — bursts of MFA push requests, then an approval.
- **Atypical context** — new device/ASN/country for a user vs their baseline;
  off-hours logins; first success after a run of failures (spray hit).
- **Dormant account activity** — sign-in on a long-unused account.

## Workflow
1. Normalize logs to: timestamp, user, source IP/ASN/geo, result, MFA, device.
2. Build per-user baselines (usual hours, countries, devices).
3. Run the detections above as windowed aggregations; score by deviation.
4. Correlate spray/brute hits with a subsequent success (the dangerous case).
5. Triage: confirm with the user, force re-auth/MFA reset, contain if compromised.

## Tuning
Baseline per-user, allow-list known VPN egress/CDNs, and weight a success-after-many-
failures far higher than failures alone. Feed results to SIEM correlation rules.

## Tools
SIEM (Splunk/Sentinel/Elastic) for windowed aggregation, GeoIP/ASN enrichment,
and UEBA baselining.

## Detailed reference
Windows event IDs, Graph/Okta APIs, Splunk detections, GeoIP/IsolationForest: `references/detail/auth-anomaly-queries.md`.
