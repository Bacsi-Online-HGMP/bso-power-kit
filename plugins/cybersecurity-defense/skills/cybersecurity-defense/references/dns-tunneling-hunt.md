
# DNS Tunneling Hunt (Zeek)

**Safety:** analysis of your own network telemetry. No active probing.

## When to use
You have Zeek `dns.log` and want to find covert channels: tunneling tools (iodine,
dnscat2, DNSExfiltrator) or malware using DNS for C2/exfiltration.

## Signals to hunt
- **Volume per domain** — one second-level domain receiving an outsized share of
  queries from a host.
- **Label entropy/length** — long subdomains with high-entropy/base32/hex labels
  (encoded payload), unusually long total query names.
- **Record types** — disproportionate `TXT`, `NULL`, `CNAME`, or `A`-with-encoded-labels.
- **Beaconing** — regular interval queries to the same domain (low jitter).
- **Answer ratio** — many `NXDOMAIN` or repetitive answers; tunneling generates odd
  response patterns.

## Workflow
1. Aggregate `dns.log` by `query` second-level domain and by source host.
2. Rank domains by query count, distinct-subdomain count, and mean label length.
3. Flag domains exceeding a baseline (e.g. >100 unique subdomains/hour from one host,
   mean label length > 30, or >50% TXT/NULL).
4. Pivot suspicious domains to `conn.log` for volume/duration and to threat intel.
5. Confirm: inspect decoded labels, identify the tool, scope affected hosts, contain.

## Example (zeek-cut / awk)
```bash
zeek-cut id.orig_h query qtype_name < dns.log \
 | awk '{n=split($2,a,"."); dom=a[n-1]"."a[n]; cnt[dom]++; len[dom]+=length($2)}
        END{for(d in cnt) printf "%-30s q=%-6d avglen=%.0f\n", d, cnt[d], len[d]/cnt[d]}' \
 | sort -k2 -t= -rn | head
```

## Tools
Zeek, `zeek-cut`, RITA (beacon analysis), entropy scoring; tune thresholds to your
network baseline to cut false positives (CDNs, telemetry domains).

## Detailed reference
Thresholds, Zeek fields, entropy math, SPL queries, RITA, MITRE map: `references/detail/dns-tunneling-detail.md`.
