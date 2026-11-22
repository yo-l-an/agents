# Links every skill in this repo's .agents\skills into Claude Code's skills folder, so edits
# here are live everywhere. Safe to re-run: links already in place are kept.
#   powershell -ExecutionPolicy Bypass -File <repo>\bin\install-skills.ps1 [-Force] [-Target <folder>]
# Links are directory junctions: they need no admin rights and no Developer Mode.
# Without -Force, a skill folder or link that already exists under another source is reported and left alone.
# With -Force, it is moved to <Target>\.trash (a folder) or replaced (a link), then linked here.
param(
    [string]$Target = "$env:USERPROFILE\.claude\skills",
    [switch]$Force
)
$ErrorActionPreference = "Stop"
$source = Join-Path (Split-Path $PSScriptRoot) ".agents\skills"
New-Item -ItemType Directory -Force $Target | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$counts = @{ linked = 0; kept = 0; skipped = 0 }

foreach ($skill in Get-ChildItem -Directory $source) {
    if (-not (Test-Path (Join-Path $skill.FullName "SKILL.md"))) { continue }
    $link = Join-Path $Target $skill.Name
    $item = Get-Item -Force $link -ErrorAction SilentlyContinue
    if ($item) {
        $isLink = [bool]$item.LinkType
        if ($isLink -and (@($item.Target)[0] -eq $skill.FullName)) { $counts.kept++; continue }
        $what = if ($isLink) { "a link to $(@($item.Target)[0])" } else { "a folder" }
        if (-not $Force) {
            Write-Warning "$($skill.Name): $link is $what. Re-run with -Force to replace it."
            $counts.skipped++; continue
        }
        if ($isLink) {
            $item.Delete()  # removes the junction only, never what it points to
        } else {
            $trash = Join-Path $Target ".trash"
            New-Item -ItemType Directory -Force $trash | Out-Null
            Move-Item $link (Join-Path $trash "$($skill.Name)-$stamp")
            Write-Host "$($skill.Name): old folder moved to $trash"
        }
    }
    New-Item -ItemType Junction -Path $link -Target $skill.FullName | Out-Null
    Write-Host "linked $($skill.Name)"
    $counts.linked++
}
Write-Host "`n$($counts.linked) linked, $($counts.kept) already linked, $($counts.skipped) skipped. Target: $Target"
