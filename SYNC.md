# Syncing this setup across accounts, devices, and apps

This repo is both a **plugin marketplace** (`claude-power-kit`, 19 plugins) and a
**dotfiles source** (`dotfiles/claude-code/`). One repo = one source of truth.

## Second Pro account (this Mac)

```bash
# Claude Code, account 2
bash bootstrap.sh ~/.claude-pro2
CLAUDE_CONFIG_DIR=~/.claude-pro2 claude   # then /login with account 2

# Cowork, account 2 (isolated second Desktop instance)
open -n -a "Claude.app" --args --user-data-dir="$HOME/.claude-instances/pro2"
# log in, then Settings > Capabilities > add this folder as marketplace
```

## New machine

```bash
git clone <your-remote> claude-power-kit
cd claude-power-kit && bash bootstrap.sh
```

## Publishing (enables device sync)

```bash
git remote add origin git@github.com:<you>/claude-power-kit.git
git push -u origin main
```

Keep it **private** — dotfiles include your CLAUDE.md and settings.
`.gitignore` already blocks credentials/session data; never force-add those.

## Updating everywhere

1. Change plugins or dotfiles here, commit, push.
2. On each machine/account: `git pull`, then inside claude:
   `/plugin marketplace update claude-power-kit`
3. Re-run `bash bootstrap.sh [config-dir]` if dotfiles changed.

## What does NOT sync via this repo

- **claude.ai connectors + server-side memory** — per account, re-add in each
  account's settings. Memory workaround: ask account 1's Claude to write a
  "what you know about me" markdown, paste into account 2.
- **Credentials** — each account/device logs in on its own (by design).
- **Local memory stores** (agentmemory/Pensyve data) — live on each machine's
  disk; both accounts on the same machine share them automatically.

## Repo layout

```
.claude-plugin/marketplace.json   # 19 plugins, paths verified
plugins/                          # vendored plugin repos
dotfiles/claude-code/             # CLAUDE.md, settings.json, agents/, commands/
bootstrap.sh                      # one-command setup for a config dir
tools/                            # non-plugin utilities
```

Notes from setup audit (2026-07-20):
- `agentmemory` plugin source points at `plugin/` subdir (fixed)
- `worktrunk` plugin source points at `plugins/worktrunk` subdir (fixed)
- `ai-research-skills` got a generated `plugin.json` exposing all 98 skills
