# Authentication Anomaly — log sources & queries

Read when you need event IDs, API endpoints, or detection queries for the
`auth-anomaly-detection` playbook. Store tokens/keys in env vars or a secrets
manager — never inline them in saved queries.

## Windows security event IDs
| ID | Meaning |
|---|---|
| 4624 | Successful logon |
| 4625 | Failed logon |
| 4648 | Logon with explicit credentials |
| 4672 | Special privileges assigned (admin) |
| 4768 / 4769 | Kerberos TGT / service-ticket request |
| 4771 | Kerberos pre-auth failed |
| 4776 | NTLM credential validation |

## Cloud identity log APIs
```bash
# Azure AD / Entra sign-ins (Microsoft Graph) — bearer token from env
GET https://graph.microsoft.com/v1.0/auditLogs/signIns?$filter=createdDateTime ge 2026-06-01
GET https://graph.microsoft.com/v1.0/identityProtection/riskyUsers

# Okta system log — token from env ($OKTA_TOKEN), not inline
curl "https://your-org.okta.com/api/v1/logs?filter=outcome.result+eq+%22FAILURE%22&since=2026-06-01" \
  -H "Authorization: SSWS $OKTA_TOKEN"
```

## Splunk SPL detections
```spl
# brute force: many failures against one account
index=auth result=failure | bin _time span=10m
| stats count by user src_ip _time | where count>=10

# password spray: one source, many accounts
index=auth result=failure | bin _time span=30m
| stats dc(user) as targets count by src_ip _time | where targets>=10

# impossible travel (geo speed)
index=auth result=success | iplocation src_ip | sort user _time
| streamstats last(lat) as plat last(lon) as plon last(_time) as ptime by user
| eval dist=6371*2*asin(sqrt(pow(sin((lat-plat)*pi()/360),2)+cos(plat*pi()/180)*cos(lat*pi()/180)*pow(sin((lon-plon)*pi()/360),2)))
| eval speed=dist/((_time-ptime)/3600) | where speed>900 AND dist>100
```

## Enrichment & modeling
```python
import geoip2.database                       # GeoIP/ASN context
reader = geoip2.database.Reader('/opt/geoip/GeoLite2-City.mmdb')

from sklearn.ensemble import IsolationForest  # unsupervised anomaly scoring
model = IsolationForest(n_estimators=200, contamination=0.01, random_state=42).fit(X)
# predict: -1 = anomaly, 1 = normal; score_samples: lower = more anomalous
```
Weight a **success following a run of failures** far higher than failures alone —
that's the spray/brute-force that actually landed.
