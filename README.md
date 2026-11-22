# agents

## Install

Link every skill in `.agents\skills` into Claude Code (`~\.claude\skills`) as directory junctions, so edits here are live. From the repo root, and again after adding a skill:

```powershell
powershell -ExecutionPolicy Bypass -File bin\install-skills.ps1
```

An existing folder or link of the same name is left alone and reported; `-Force` moves it to `~\.claude\skills\.trash` (or replaces the link). `-Target <folder>` installs elsewhere, for example `-Target $env:USERPROFILE\.agents\skills`.
