# Gemini workers: setup

In this file, `<python>` is `py -3` on Windows and `python3` on macOS and Linux, and `<skill>` is this skill's folder (usually `~/.claude/skills/gemini-workers`).

## Install

The skill drives Gemini through **Antigravity MCP**, an open-source MCP server by houyhlouis: <https://github.com/houyhlouis/antigravity-mcp> (MIT). It is not made by Google or Anthropic. It starts Google's Antigravity CLI (`agy`) as a local agent and exposes it to Claude Code as the `mcp__antigravity__agy_*` tools. The skill is tested with its release **v0.1.1**.

### What you need

- **Antigravity CLI (`agy`)**, signed in once, on the same computer and OS account that runs Claude Code. Windows: `irm https://antigravity.google/cli/install.ps1 | iex` in PowerShell. macOS and Linux: `curl -fsSL https://antigravity.google/cli/install.sh | bash`. Then open a new terminal and run `agy` once to sign in. Workers spend that account's Antigravity quota (`agy` then `/usage` shows it).
- **Python 3.11 or later**. Windows: python.org (the `py` launcher comes with it). macOS: `brew install python` or python.org.
- **git** and the **Claude Code CLI** (`claude`).

### Where things go

| What | Windows | macOS and Linux |
|---|---|---|
| The server (a git checkout) | `~\tools\antigravity-mcp` by default | `~/tools/antigravity-mcp` by default |
| Its config | `%APPDATA%\AntigravityMCP\config.toml` | `~/.config/antigravity-mcp/config.toml` |
| Its state (tasks, transcripts) | `%LOCALAPPDATA%\AntigravityMCP` | `~/.local/state/antigravity-mcp` |
| agy's permission rules | `~\.gemini\antigravity-cli\settings.json` | `~/.gemini/antigravity-cli/settings.json` |

Any install folder works: Claude Code's registration (`~/.claude.json`, server `antigravity`) records it, and the skill's scripts read it from there (`scripts/broker.py`). The `ANTIGRAVITY_MCP_SERVER` environment variable, set to the full path of `server.py`, overrides it. `<python> <skill>/scripts/broker.py server` prints the one in use.

With the Claude desktop app on Windows, the config and state live in the app's package folder instead: see "Packaged Claude app" below.

### Install with the setup script

The setup script does every step below. It is safe to re-run: it skips what is in place, backs up each file it changes (`*.bak-<timestamp>`), and restarts the broker only when the server config changed, because a restart cuts off live workers.

Windows (from Claude Code inside the Claude desktop app, if you use it):

```powershell
powershell -ExecutionPolicy Bypass -File "<skill>\setup\setup.ps1"
```

macOS and Linux:

```bash
bash <skill>/setup/setup.sh
```

Both take the release (`-Version` / `--version`, default `v0.1.1`) and the install folder (`-InstallDir` / `--install-dir`). Then open a new Claude Code session.

### What it does, step by step

1. Clones the server: `git clone --depth 1 --branch v0.1.1 https://github.com/houyhlouis/antigravity-mcp.git <install dir>`. Nothing else to install: `server.py` runs from the folder.
2. Sets agy's allow and deny lists from `setup/agy-permissions.json` (`setup/merge.py agy`).
3. Copies `setup/antigravity-mcp.config.toml` to the config path above, readable by your account only.
4. Checks the install with `<python> <install dir>/server.py doctor`, which also checks the agy sign-in without spending quota.
5. Registers the server in Claude Code at user scope: `claude mcp add --transport stdio --scope user antigravity -- <full path to python> <install dir>/server.py serve`.
6. Allows its tools without a prompt: adds `mcp__antigravity` to `permissions.allow` in `~/.claude/settings.json`.

## Files

`setup/` is the **source of truth** for everything outside this skill. Change a file there, then re-run the setup script, so the folder and the machine stay in sync.

| File | Sets |
|---|---|
| `setup/agy-permissions.json` | agy's `allow` and `deny` lists in `~/.gemini/antigravity-cli/settings.json`, set to exactly the file's contents. `{HOME}` stands for the home folder as agy writes it: `/Users/<name>` on Windows and macOS, `$HOME` on Linux. |
| `setup/antigravity-mcp.config.toml` | the server config (path in "Where things go") |
| `setup/setup.ps1`, `setup/setup.sh` | the install above, for Windows and for macOS and Linux |
| `setup/check-rules.py` | an offline test of the deny rules |
| `setup/check-gate.py` | an offline test of the waiter's gate (`scripts/wait.py`) |
| `scripts/broker.py` | where the server and its state are on this machine, for the other scripts |
| `scripts/viewer.cmd`, `scripts/viewer.command`, `scripts/viewer.py` | the user's live view of every worker. Not started by setup and never runs on its own: the user double-clicks `viewer.cmd` (Windows) or `viewer.command` (macOS), or runs `<python> viewer.py`. It opens `http://localhost:7380` in the browser and serves it until its window is closed. Workers are picked from a dropdown, with finished ones (`closed`, `archived`, `interrupted`) folded under "Finished". Thinking and messages show in full; the tool calls and edits between them fold into one collapsed group each, and only the current group is open. It reads the broker's database read-only, so it never touches a worker, and the lead has no part in it. A bar at the bottom shows the Gemini models' usage as `Session 59% 00:00 (1h01)   Week 94% Fri. 06:00 (4d 7h)`: percentage used, reset time and time left, for the 5-hour window and the week. Hovering it shows when it last updated. It is read with `agy -p /usage` every 2 minutes (a slash command: no model call, no saved conversation). Its one write is the pin list: "do not delete after 7 days" pins a worker (📌 in the list) in `~/.gemini-workers/pinned.json`. `--db <path>` overrides the database it finds; `--port <free port>` when 7380 is taken. |
| `scripts/prune.py` | retention: deletes the broker's record (transcript and events) of every worker that is not active, not pinned, and whose last message is more than 7 days old, through `agy_close` `forget`. `wait.py` starts it, detached, on each run. `--dry-run` lists what it would delete; `--days` changes the age. Antigravity's own copy in `~/.gemini/antigravity-cli/conversations` stays. |

Running workers keep the rules they started with. New workers, or ones reopened after an idle close, get the new rules.

## The waiter's gate

`scripts/wait.py` allows routine prompts so the lead sees only the rest. It reads its deny regexes from `setup/agy-permissions.json` (one source with agy), and adds its own `LEAD_RULES` and a path check. To change what it allows:

1. Edit `LEAD_RULES` or the localhost and path rules in `scripts/wait.py`. For a folder that only one task needs, pass `--allow-path` instead.
2. Add the command to `ALLOW` or `ESCALATE` in `setup/check-gate.py`, then run `<python> setup/check-gate.py`. Every case must pass.

Running waiters keep the gate they started with: start the waiter again after a change.

## agy permission rules

The design is `allow: ["command(*)"]` plus `deny` regexes. Deny beats Ask, and Ask beats Allow.

Without agy's terminal sandbox (Windows before 11 24H2; Linux without unprivileged user namespaces), Auto mode is unavailable and agy checks each shell command as one whole line (`unsandboxed(<line>)`). Both of these were tested on Windows 10:
- **Prefix rules never match.** `command(git)` fails to match even `git --version`. Only `command(*)` and `command(regex:...)` work.
- **Write each command deny as a whole-line regex anchored at command position.** Command position means line start, after `;`, `&`, `|`, `(` or `{`, or inside a `-c`, `-Command` or `/c` wrapper. Matching there catches the command inside compound shell lines and leaves the same word alone in arguments and commit messages (`pnpm format`, `-m "document curl"`). Copy the prefix of an existing rule, write `\s+` where the command has spaces, and keep literal spaces out of the pattern.

Path rules (`write_file(...)`, `read_file(...)`) match by path, so their prefix form works.

To change a rule:
1. Edit `setup/agy-permissions.json`.
2. Run `<python> setup/check-rules.py setup/agy-permissions.json`. Every everyday dev command must pass and every dangerous one must be blocked. Add your new case to its `SAFE` or `DANGER` list.
3. Re-run the setup script.
4. For live proof, run a one-shot `agy -p` with `--mode accept-edits` in a temp git repo, asking it to run the command exactly. A blocked command reports `Matches user-configured deny rule`.

## Server config

- `approval_relay = true` lets the lead approve one-time permission prompts. `max_live_sessions = 4` caps the workers.
- The config folder and file must be writable by your account only, or the server rejects them with `Configuration must be user-owned`. The setup scripts set this up: on Windows, owner, SYSTEM and Administrators only, with no inheritance; on macOS and Linux, `700` on the folder and `600` on the file.
- The file is UTF-8 without a BOM. After a manual change, run `<python> <install dir>/server.py stop`.

## Packaged Claude app

Windows only. The Claude desktop app for Windows is an MSIX package. Windows redirects what its child processes write under `%LOCALAPPDATA%` and `%APPDATA%` into the package's own folder, `%LOCALAPPDATA%\Packages\<Claude package>\LocalCache\{Local,Roaming}`. Inside the app they still see it at the plain path; every other process sees only the plain path. That folder holds the broker the app starts: its state (`Local\AntigravityMCP`) and its config (`Roaming\AntigravityMCP\config.toml`).

- Run `setup.ps1` and `server.py` (`stop`, `doctor`, `call`) from Claude Code inside the app. From a normal terminal they work on the plain-path copies, which the app's broker never reads.
- To edit the config by hand from outside the app, edit the package's copy.
- `~/.gemini`, `~/.claude` and the install folder sit outside AppData, so every process shares them. The skill's scripts look in both places.

## Upgrade

Run `<python> <install dir>/server.py stop`. Then run `git -C <install dir> fetch --tags`, check out the new tag, change the default version in the setup scripts, and restart Claude Code.

The Claude Code registration holds the full path to the Python executable. After a Python upgrade that changes that path, run `claude mcp remove antigravity -s user`, then re-run the setup script to register the new interpreter.

## Uninstall

1. `<python> <install dir>/server.py stop`
2. `claude mcp remove antigravity -s user`, and remove `mcp__antigravity` from `~/.claude/settings.json`.
3. Delete the install folder, and optionally the state folder and the config file.

Antigravity's own conversations stay in its history (`~/.gemini/antigravity-cli`).
