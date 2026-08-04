# Linux Forensics — command & artifact reference

Read when you need exact paths/commands for the `linux-forensic-artifacts` playbook.
All read-only triage; prefer running against a mounted copy/image of the evidence.

## Key artifact locations
| Artifact | Path | Notes |
|---|---|---|
| Auth logs | `/var/log/auth.log` (Debian), `/var/log/secure` (RHEL) | auth, sudo, SSH |
| Login history | `/var/log/wtmp` | binary — read with `last` |
| Failed logins | `/var/log/btmp` | binary — read with `lastb` |
| Bash history | `~/.bash_history` | per user; check timestamps if `HISTTIMEFORMAT` set |
| SSH keys | `~/.ssh/authorized_keys` | persistence |
| Cron | `/etc/crontab`, `/var/spool/cron/crontabs/` | persistence |
| systemd | `/etc/systemd/system/` | service/timer persistence |
| Preload | `/etc/ld.so.preload` | library hijack |
| SUID | `find / -perm -4000 -type f 2>/dev/null` | privilege escalation |

## Login history
```bash
last  -i -f /var/log/wtmp           # successful logins, show IPs
lastb    -f /var/log/btmp           # failed logins
last -s 2026-06-01 -t 2026-06-23    # date range
```

## Rootkit scanners
```bash
chkrootkit -q -r /mnt/evidence      # quiet, scan mounted evidence
rkhunter --check --rootdir /mnt/evidence
```

## auditd
```bash
ausearch -m execve -ts recent       # recent command execution
ausearch -m USER_AUTH -ts today     # auth events
ausearch -ua 0 -ts today            # root actions
aureport --auth ; aureport --login ; aureport --file
```

## osquery (SQL over live system)
```sql
SELECT * FROM users WHERE uid = 0;
SELECT * FROM crontab;
SELECT * FROM authorized_keys;
SELECT * FROM suid_bin;
SELECT * FROM process_open_sockets;
SELECT * FROM shell_history;
```

## Super timeline (Plaso) & integrity (AIDE)
```bash
log2timeline.py /cases/timeline.plaso /mnt/evidence
psort.py -o l2tcsv /cases/timeline.plaso "date > '2026-06-01'" > timeline.csv
aide --init ; aide --check          # file-integrity baseline / compare
```
