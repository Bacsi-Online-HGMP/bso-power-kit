
# Linux Forensic Artifacts

**Safety:** read-only triage. Collect to an external/forensic location; avoid writing
to the subject filesystem. Run only on hosts you are authorized to investigate.

## When to use
A Linux host shows signs of compromise (alerts, odd network traffic, unexpected
processes), or you need to confirm/deny intrusion and capture evidence.

## Workflow
1. **Volatile first** — running processes (`ps -ef`, `/proc`), open network sockets
   (`ss -tunap`), loaded modules (`lsmod`), logged-in users (`w`, `last`), and
   process→binary mapping (deleted-but-running binaries via `/proc/*/exe`).
2. **Persistence** — cron (`/etc/cron*`, user crontabs), systemd units & timers,
   `~/.bashrc`/`profile.d`, `rc.local`, SSH `authorized_keys`, LD_PRELOAD,
   kernel modules, and new/SUID binaries.
3. **Logs** — `/var/log/auth.log`/`secure` (auth, sudo, SSH), `journalctl`,
   `wtmp`/`btmp`/`lastlog`, shell history, package-manager logs. Watch for gaps
   (log wiping) and timestamps that don't match.
4. **Filesystem timeline** — build a MAC-time timeline (e.g. `find -newer`,
   Sleuth Kit `fls`/`mactime`) around the suspected window; look in `/tmp`,
   `/dev/shm`, hidden dirs, and recently modified system binaries.
5. **Correlate & conclude** — tie artifacts to a narrative (initial access →
   execution → persistence → C2/exfil); record IOCs and affected accounts.

## Tools
Sleuth Kit (`fls`, `mactime`), `auditd`, `chkrootkit`/`rkhunter`, `osquery`,
`grep`/`jq` for log parsing, and a write-blocked image or copy for preservation.

## Detailed reference
Exact paths, scanners, auditd/osquery/Plaso commands: `references/detail/linux-forensics-commands.md`.
