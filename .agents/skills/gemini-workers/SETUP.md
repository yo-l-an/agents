# Gemini workers: setup

`setup/` is the **source of truth** for everything outside this skill. Change a file there, then re-run the script, so the folder and the machine stay in sync:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\gemini-workers\setup\setup.ps1"
```

Run it from Claude Code inside the Claude desktop app (see "Packaged Claude app" below). The script is safe to re-run. It backs up each file before changing it (`*.bak-<timestamp>`), and it restarts the broker only when the server config changed, because a restart cuts off live workers.

| File | Sets |
|---|---|
| `setup/agy-permissions.json` | agy's `allow` and `deny` lists in `~/.gemini/antigravity-cli/settings.json`, set to exactly the file's contents. `{HOME}` stands for `/Users/<name>`. |
| `setup/antigravity-mcp.config.toml` | the server config at `%APPDATA%\AntigravityMCP\config.toml` |
| `setup/setup.ps1` | also installs antigravity-mcp v0.1.1 in `C:\Tools\antigravity-mcp` with the newest Python 3.11 or later, registers it in Claude Code at user scope, and allows `mcp__antigravity` in `~/.claude/settings.json` |
| `setup/check-rules.py` | an offline test of the deny rules |
| `scripts/viewer.cmd`, `scripts/viewer.py` | the user's live view of every worker. Not started by `setup.ps1` and never runs on its own: the user double-clicks `viewer.cmd`, which opens `http://localhost:7380` in the browser and serves it until its console window is closed. Workers are picked from a dropdown, with finished ones (`closed`, `archived`, `interrupted`) folded under "Finished". Thinking and messages show in full; the tool calls and edits between them fold into one collapsed group each, and only the current group is open. It reads the broker's database read-only, so it never touches a worker, and the lead has no part in it. A bar at the bottom shows the Gemini models' usage as `Session 59% 00:00 (1h01)   Week 94% Fri. 06:00 (4d 7h)`: percentage used, reset time and time left, for the 5-hour window and the week. Hovering it shows when it last updated. It is read with `agy -p /usage` every 2 minutes (a slash command: no model call, no saved conversation). Its one write is the pin list: "do not delete after 7 days" pins a worker (📌 in the list) in `~/.gemini-workers/pinned.json`. It finds the database on its own, the packaged app's copy included; `--db <path>` overrides that. When port 7380 is taken, run `viewer.cmd --port <free port>`. |
| `setup/check-gate.py` | an offline test of the waiter's gate (`scripts/wait.py`) |
| `scripts/prune.py` | retention: deletes the broker's record (transcript and events) of every worker that is not active, not pinned, and whose last message is more than 7 days old, through `agy_close` `forget`. `wait.py` starts it, detached, on each run. `--dry-run` lists what it would delete; `--days` changes the age. Antigravity's own copy in `~/.gemini/antigravity-cli/conversations` stays. |

Running workers keep the rules they started with. New workers, or ones reopened after an idle close, get the new rules.

## The waiter's gate

`scripts/wait.py` allows routine prompts so the lead sees only the rest. It reads its deny regexes from `setup/agy-permissions.json` (one source with agy), and adds its own `LEAD_RULES` and a path check. To change what it allows:

1. Edit `LEAD_RULES` or the localhost and path rules in `scripts/wait.py`. For a folder that only one task needs, pass `--allow-path` instead.
2. Add the command to `ALLOW` or `ESCALATE` in `setup/check-gate.py`, then run `py -3 setup/check-gate.py`. Every case must pass.

Running waiters keep the gate they started with: start the waiter again after a change.

## agy permission rules

The design is `allow: ["command(*)"]` plus `deny` regexes. Deny beats Ask, and Ask beats Allow.

This Windows 10 machine has no agy sandbox, so its Auto mode is unavailable. agy checks each shell command as one whole line (`unsandboxed(<line>)`). Both of these were tested:
- **Prefix rules never match.** `command(git)` fails to match even `git --version`. Only `command(*)` and `command(regex:...)` work.
- **Write each command deny as a whole-line regex anchored at command position.** Command position means line start, after `;`, `&`, `|`, `(` or `{`, or inside a `-c`, `-Command` or `/c` wrapper. Matching there catches the command inside compound PowerShell and leaves the same word alone in arguments and commit messages (`pnpm format`, `-m "document curl"`). Copy the prefix of an existing rule, write `\s+` where the command has spaces, and keep literal spaces out of the pattern.

Path rules (`write_file(...)`, `read_file(...)`) match by path, so their prefix form works.

To change a rule:
1. Edit `setup/agy-permissions.json`.
2. Run `py -3 setup/check-rules.py setup/agy-permissions.json`. Every everyday dev command must pass and every dangerous one must be blocked. Add your new case to its `SAFE` or `DANGER` list.
3. Re-run `setup.ps1`.
4. For live proof, run a one-shot `agy -p` with `--mode accept-edits` in a temp git repo, asking it to run the command exactly. A blocked command reports `Matches user-configured deny rule`.

## Server config

- `approval_relay = true` lets the lead approve one-time permission prompts. `max_live_sessions = 4` caps the workers.
- The config folder and file must be writable by this Windows account only, or the server rejects them with `Configuration must be user-owned`. `setup.ps1` sets this up: owner, SYSTEM and Administrators only, with no inheritance.
- The file is UTF-8 without a BOM. After a manual change, run `server.py stop`.

## Packaged Claude app

The Claude desktop app for Windows is an MSIX package. Windows redirects what its child processes write under `%LOCALAPPDATA%` and `%APPDATA%` into the package's own folder, `%LOCALAPPDATA%\Packages\<Claude package>\LocalCache\{Local,Roaming}`. Inside the app they still see it at the plain path; every other process sees only the plain path. That folder holds the broker the app starts: its state (`Local\AntigravityMCP`) and its config (`Roaming\AntigravityMCP\config.toml`).

- Run `setup.ps1` and `server.py` (`stop`, `doctor`, `call`) from Claude Code inside the app. From a normal terminal they work on the plain-path copies, which the app's broker never reads.
- To edit the config by hand from outside the app, edit the package's copy.
- `~/.gemini` and `~/.claude` sit outside AppData, so every process shares them.

## Upgrade

Run `py -3 C:\Tools\antigravity-mcp\server.py stop`. Then run `git -C C:\Tools\antigravity-mcp fetch --tags`, check out the new tag, update `$Version` in `setup.ps1`, and restart Claude Code.

The Claude Code registration holds the full path to `python.exe`. After a Python upgrade that changes that path, run `claude mcp remove antigravity -s user`, then re-run `setup.ps1` to register the new interpreter.
