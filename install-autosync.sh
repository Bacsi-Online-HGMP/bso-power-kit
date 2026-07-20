#!/usr/bin/env bash
# Installs a macOS LaunchAgent that runs update.sh daily at 09:30.
# Uninstall:  launchctl unload ~/Library/LaunchAgents/com.claude-power-kit.autosync.plist \
#             && rm ~/Library/LaunchAgents/com.claude-power-kit.autosync.plist
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.claude-power-kit.autosync.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.claude-power-kit.autosync</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$HERE/update.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
  <key>StandardOutPath</key><string>/tmp/claude-power-kit-sync.log</string>
  <key>StandardErrorPath</key><string>/tmp/claude-power-kit-sync.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Installed. Runs daily 09:30. Log: /tmp/claude-power-kit-sync.log"
echo "Test now:  bash $HERE/update.sh"
