
# Cloud Incident Response

**Safety:** run containment commands only in accounts you are authorized to operate.

## When to use
CSPM/GuardDuty/Defender alerts, suspicious CloudTrail / Azure Activity / GCP Audit
events, suspected key or service-principal compromise, or unauthorized resources.
Not for purely on-prem incidents.

## Prerequisites
Centralized cloud audit logging (all regions), pre-provisioned read-only forensic
IAM roles, an isolated forensic account/subscription/project, flow logs enabled.

## Workflow
1. **Confirm** — review audit logs for tell-tale events: console login from new geo,
   `CreateAccessKey`, public-bucket policy changes, `DeleteTrail`/`StopLogging`,
   role/permission grants, VM/instance creation in odd regions, MFA disabled.
2. **Contain (identity-first)** —
   - AWS: set access key `Inactive`; attach `AWSDenyAll`; deny-by-token-issue-time on roles; move EC2 to an isolate SG.
   - Azure: disable user; `Revoke-AzureADUserAllRefreshToken`; remove role assignments; NSG deny-all on the VM.
   - GCP: disable/rotate service-account keys; remove broad IAM bindings; isolate instance.
3. **Preserve evidence** — export audit logs to the forensic account/bucket; snapshot
   disks/volumes; capture flow logs and IAM/credential reports before resources rotate.
4. **Investigate patterns** — credential→privesc→resource abuse, public storage→exfil,
   SSRF→IMDS token theft→lateral movement, CI/CD compromise, cross-account pivots.
5. **Eradicate & recover** — rotate all compromised secrets; remove attacker IAM
   entities/resources; restore policies; re-enable disabled controls.
6. **Harden** — enforce MFA, SCP/Azure Policy guardrails against log disablement,
   least-privilege from access-analyzer data, IMDSv2, budget alerts for crypto-mining.

## Tools
CloudTrail / Azure Activity & Sign-in Logs / GCP Audit Logs; Prowler, ScoutSuite,
Steampipe, Cartography for posture and attack-path review; Cado for cloud forensics.
