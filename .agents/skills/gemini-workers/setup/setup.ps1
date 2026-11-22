# Rebuilds the gemini-workers setup on this Windows machine. Safe to re-run: each step
# skips what is already in place, and every settings file it changes is backed up first.
#   powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\gemini-workers\setup\setup.ps1"
param(
    [string]$Version = "v0.1.1",
    [string]$InstallDir = "C:\Tools\antigravity-mcp"
)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot

function Write-Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }

Write-Step "Prerequisites"
if (-not (Get-Command agy -ErrorAction SilentlyContinue)) { throw "agy not found. Install it: irm https://antigravity.google/cli/install.ps1 | iex, then run agy once to sign in." }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git not found." }
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { throw "claude CLI not found." }
$python = (py -0p) | ForEach-Object {
    if ($_ -match '-V:(\d+)\.(\d+)\S*\s+\*?\s*(\S.+)$' -and ([int]$Matches[1] -gt 3 -or [int]$Matches[2] -ge 11)) {
        [pscustomobject]@{ Minor = [int]$Matches[2]; Path = $Matches[3].Trim() }
    }
} | Sort-Object Minor -Descending | Select-Object -First 1 -ExpandProperty Path
if (-not $python) { throw "Python 3.11+ not found (py -0p). Install it from python.org." }
Write-Host "agy $(agy --version), python $python"

Write-Step "antigravity-mcp $Version in $InstallDir"
if (Test-Path "$InstallDir\server.py") {
    Write-Host "already installed: $(& $python "$InstallDir\server.py" --version)"
} else {
    New-Item -ItemType Directory -Force (Split-Path $InstallDir) | Out-Null
    git -c advice.detachedHead=false clone --depth 1 --branch $Version https://github.com/houyhlouis/antigravity-mcp.git $InstallDir
}

Write-Step "agy permission rules (all commands allowed, dangerous ones hard-denied)"
$homeRule = "/Users/$env:USERNAME"
& $python "$here\merge.py" agy "$env:USERPROFILE\.gemini\antigravity-cli\settings.json" "$here\agy-permissions.json" $homeRule

Write-Step "Server config (approval_relay) with owner-only permissions"
$cfgDir = "$env:APPDATA\AntigravityMCP"
$cfg = "$cfgDir\config.toml"
New-Item -ItemType Directory -Force $cfgDir | Out-Null
$wanted = [IO.File]::ReadAllText("$here\antigravity-mcp.config.toml")
$changed = -not (Test-Path $cfg) -or ([IO.File]::ReadAllText($cfg) -ne $wanted)
if ($changed) { [IO.File]::WriteAllText($cfg, $wanted, (New-Object Text.UTF8Encoding $false)) }
$me = [Security.Principal.WindowsIdentity]::GetCurrent().Name
foreach ($p in @($cfgDir, $cfg)) {
    $inherit = if ($p -eq $cfgDir) { "(OI)(CI)" } else { "" }
    icacls $p /inheritance:r /grant:r "${me}:$inherit(F)" "*S-1-5-18:$inherit(F)" "*S-1-5-32-544:$inherit(F)" | Out-Null
}
# Restarting the broker closes live worker sessions, so only do it when the config changed.
if ($changed) { Write-Host "config changed: restarting broker"; & $python "$InstallDir\server.py" stop | Out-Null }
$doctor = & $python "$InstallDir\server.py" doctor
$doctor | Select-String 'signed_in|acp_available|findings|^ok ='

Write-Step "Register MCP server in Claude Code (user scope)"
claude mcp get antigravity *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "already registered"
} else {
    claude mcp add --transport stdio --scope user antigravity -- $python "$InstallDir\server.py" serve
}

Write-Step "Claude Code allow rule"
& $python "$here\merge.py" allow "$env:USERPROFILE\.claude\settings.json" "mcp__antigravity"

Write-Host "`nDone. Open a new Claude Code session to load the antigravity tools." -ForegroundColor Green
