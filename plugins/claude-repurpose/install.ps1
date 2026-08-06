# Claude Repurpose Installer (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\repurpose"
$AgentDir = Join-Path $env:USERPROFILE ".claude\agents"
$RepoUrl = "https://github.com/AgriciDaniel/claude-repurpose"
$RepoTag = if ($env:CLAUDE_REPURPOSE_TAG) { $env:CLAUDE_REPURPOSE_TAG } else { "v1.0.0" }

Write-Host "=================================="
Write-Host "  Claude Repurpose - Installer"
Write-Host "  Content Repurposing Engine"
Write-Host "=================================="
Write-Host ""

# Check prerequisites
try { python --version | Out-Null } catch { Write-Error "Python 3 is required but not installed."; exit 1 }
try { git --version | Out-Null } catch { Write-Error "Git is required but not installed."; exit 1 }

$PythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$PythonOk = python -c "import sys; print(1 if sys.version_info >= (3, 10) else 0)"
if ($PythonOk -eq "0") { Write-Error "Python 3.10+ required but $PythonVersion found."; exit 1 }
Write-Host "  Python $PythonVersion detected"

# Check optional tools
try { yt-dlp --version | Out-Null; Write-Host "  yt-dlp detected" } catch { Write-Host "  yt-dlp not found (optional: pip install yt-dlp)" }

# Create directories
New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null

# Clone to temp
$TempDir = Join-Path $env:TEMP "claude-repurpose-install"
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }

Write-Host "  Downloading Claude Repurpose ($RepoTag)..."
git clone --depth 1 --branch $RepoTag $RepoUrl $TempDir 2>$null

if (-not (Test-Path (Join-Path $TempDir "skills"))) {
    Write-Error "Clone failed. Check your network and try again."
    exit 1
}

# Copy skills
Write-Host "  Installing skill files..."
Get-ChildItem -Path (Join-Path $TempDir "skills") -Directory | ForEach-Object {
    $Target = Join-Path $env:USERPROFILE ".claude\skills\$($_.Name)"
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    Copy-Item -Recurse -Force "$($_.FullName)\*" $Target
}

# Copy agents
Write-Host "  Installing subagents..."
Copy-Item -Force (Join-Path $TempDir "agents\*.md") $AgentDir -ErrorAction SilentlyContinue

# Copy scripts
$ScriptsTarget = Join-Path $SkillDir "scripts"
New-Item -ItemType Directory -Force -Path $ScriptsTarget | Out-Null
Copy-Item -Recurse -Force (Join-Path $TempDir "scripts\*") $ScriptsTarget

# Copy hooks
$HooksTarget = Join-Path $SkillDir "hooks"
New-Item -ItemType Directory -Force -Path $HooksTarget | Out-Null
Copy-Item -Recurse -Force (Join-Path $TempDir "hooks\*") $HooksTarget -ErrorAction SilentlyContinue

# Copy requirements
Copy-Item -Force (Join-Path $TempDir "requirements.txt") $SkillDir -ErrorAction SilentlyContinue

# Install Python dependencies
Write-Host "  Installing Python dependencies..."
$VenvDir = Join-Path $SkillDir ".venv"
try {
    python -m venv $VenvDir
    & (Join-Path $VenvDir "Scripts\pip.exe") install --quiet -r (Join-Path $TempDir "requirements.txt")
    Write-Host "    Installed in venv at $VenvDir"
} catch {
    pip install --quiet --user -r (Join-Path $TempDir "requirements.txt") 2>$null
    Write-Host "    Installed with --user fallback"
}

# Cleanup
Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "  Claude Repurpose installed successfully!"
Write-Host ""
Write-Host "  Usage:"
Write-Host "    1. Start Claude Code:  claude"
Write-Host "    2. Run commands:       /repurpose https://example.com/blog/post"
Write-Host ""
