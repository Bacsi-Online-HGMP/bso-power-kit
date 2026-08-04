# DNS Tunneling — detection detail

Read when you need thresholds, Zeek fields, entropy math, or SPL queries for the
`dns-tunneling-hunt` playbook. Tune thresholds to your baseline to cut false positives.

## Scoring thresholds
| Indicator | Threshold | Rationale |
|---|---|---|
| Query length | > 50 chars | normal queries ~20–30 |
| Subdomain label length | > 30 chars | max label is 63; tunnels run near-max |
| Subdomain Shannon entropy | > 3.5 bits/char | base32/64 encoding is high-entropy |
| Unique subdomains/domain | > 100/hour | legit domains have few |
| Query volume to one domain | > 100/hour | sustained volume = tunnel |
| TXT query ratio | > 50% to a domain | TXT carries more data |
| NULL queries | any volume | rarely legitimate |

## Zeek dns.log fields
`ts`(0) · `id.orig_h`(2, source) · `id.resp_h`(4, resolver) · `query`(9) ·
`qtype_name`(13) · `answers`(21) · `rcode_name` (watch NXDOMAIN patterns).

## Shannon entropy
| Data | Entropy | 
|---|---|
| Normal hostnames | 2.0–3.0 |
| Hex / base32 | 3.5–4.0 |
| base64 | 4.0–5.0 |
```python
import math
from collections import Counter
def shannon_entropy(s):
    if not s: return 0.0
    n = len(s)
    return -sum((c/n)*math.log2(c/n) for c in Counter(s).values())
# flag subdomains with entropy > 3.5
```

## Splunk SPL (if logs are in a SIEM)
```spl
# long queries by base domain
index=zeek sourcetype=bro_dns | eval qlen=len(query)
| where qlen>50 | rex field=query "\.(?<dom>[^.]+\.[^.]+)$"
| stats count avg(qlen) as avg_len dc(query) as uniq by id.orig_h dom
| where count>50 | sort -avg_len

# unusual record types
index=zeek sourcetype=bro_dns | where qtype_name IN ("TXT","NULL","CNAME","MX","KEY")
| rex field=query "\.(?<dom>[^.]+\.[^.]+)$"
| stats count dc(query) as uniq by id.orig_h dom qtype_name | where count>50
```

## RITA (automated beacon/tunnel analysis)
```bash
rita import /opt/zeek/logs/current dns_hunt
rita show-dns-tunneling dns_hunt
rita show-exploded-dns dns_hunt | sort -k2 -nr | head -20
```

## Tooling fingerprints (for reference)
iodine (NULL/TXT/CNAME/A) · dnscat2 (TXT/CNAME/MX) · dns2tcp (TXT/KEY) ·
DNSExfiltrator (TXT/A) · Cobalt Strike DNS (A/TXT) · Heyoka (all).

## MITRE ATT&CK
T1071.004 (DNS C2) · T1048.003 (exfil over non-C2 protocol) · T1572 (protocol
tunneling) · T1568.002 (DGA) · T1132.001 (standard encoding).
