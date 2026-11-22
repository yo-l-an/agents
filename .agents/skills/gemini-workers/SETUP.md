# Gemini workers: setup

`setup/` is the **source of truth** for everything outside this skill. Change a file there, then re-run the script, so the folder and the machine stay in sync:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\gemini-workers\setup\setup.ps1"
```

The script is safe to re-run. It backs up each file before changing it (`*.bak-<timestamp>`), and it restarts the broker only when the server config changed, because a restart cuts off live workers.

| File | Sets |
|---|---|
| `setup/agy-permissions.json` | agy's `allow` and `deny` lists in `~/.gemini/antigravity-cli/settings.json`, set to exactly the file's contents. `{HOME}` stands for `/Users/<name>`. |
| `setup/antigravity-mcp.config.toml` | the server config at `%APPDATA%\AntigravityMCP\config.toml` |
| `setup/setup.ps1` | also installs antigravity-mcp v0.1.1 in `C:\Tools\antigravity-mcp` with the newest Python 3.11 or later, registers it in Claude Code at user scope, and allows `mcp__antigravity` in `~/.claude/settings.json` |
| `setup/check-rules.py` | an offline test of the deny rules |

Running workers keep the rules they started with. New workers, or ones reopened after an idle close, get the new rules.

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

## Upgrade

Run `py -3 C:\Tools\antigravity-mcp\server.py stop`. Then run `git -C C:\Tools\antigravity-mcp fetch --tags`, check out the new tag, update `$Version` in `setup.ps1`, and restart Claude Code.

The Claude Code registration holds the full path to `python.exe`. After a Python upgrade that changes that path, run `claude mcp remove antigravity -s user`, then re-run `setup.ps1` to register the new interpreter.
