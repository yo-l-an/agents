# Gemini workers: troubleshooting

The server code is in `C:\Tools\antigravity-mcp` (v0.1.1) and runs on `py -3.15`. `py -3` points to 3.10, which is too old.

## Failed calls

`ok: false` comes with an `error.code`.

- `error.retryable`: repeat the identical call with the same `request_id`.
- `error.uncertain`: the action may already have happened. Inspect the task with `agy_get` before you do anything else.
- `not_signed_in`: ask the user to run `agy` in a terminal and sign in.
- `quota_exhausted` or `rate_limited`: tell the user and stop. The quota is shared by every worker.
- `workspace_busy`: `agy_get` shows the holder in `claims`. Close finished tasks to release it.

## Resuming

A task in `needs_resume` or `uncertain` state: run `agy_resume`, then read its `reconciliation` (`unknown`, `next_steps`) and `agy_history` before you give it new work.

A task that shows `closed` while its `summary` says it was still working was cut off by a broker restart (`server.py stop`, or `setup.ps1` after a config change). Its conversation is kept. Check `git status` and `git log` in its folder for what landed, then `agy_send` a prompt asking it to check where it stopped and finish. `agy_send` reopens the session.

## Stuck native subagent

`possible_subagent_wait` means the worker's own subagent may be waiting on an approval that agy 1.5.x does not forward over ACP. Send a follow-up asking the worker to check its subagents, or interrupt it.

## Allow is refused

If `agy_respond` with `allow` fails, `approval_relay` is off or the config was rejected. Run `doctor` and check the config notes below. Until it is fixed, deny the prompt and tell the user.

## Server down: one-shot CLI

This path has no questions, approvals, or follow-ups. Use the Bash tool, and put `-p` last, because `-p` takes the next token as the prompt and agy does not read stdin:

```bash
agy --model gemini-4-neon-medium --output-format json --print-timeout 600s --mode accept-edits \
    -p "$(cat "<scratchpad>/brief.md")"
```

Read `.response`. Any `status` other than `"SUCCESS"` is a failure.

## Setting up again

The `setup/` folder holds the whole setup:

- `agy-permissions.json`: agy's rules. `allow` covers the trusted dev tools that run without a prompt, and `deny` is the hard blocks. `{HOME}` stands for `/Users/<name>`.
- `antigravity-mcp.config.toml`: the server config.
- `setup.ps1`: applies both, installs and registers the server, and adds the Claude Code allow rule. Re-running it is safe, and it backs up each file before changing it.

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\gemini-workers\setup\setup.ps1"
```

To change a deny rule or a server setting, edit the file in `setup/` first, then re-run the script. That keeps the folder and the machine in sync. Re-running adds rules but never removes them, so delete a rule from both places.

## Configuration and upgrade

- Health check: `py -3.15 C:\Tools\antigravity-mcp\server.py doctor`
- Server settings: `%APPDATA%\AntigravityMCP\config.toml`. `approval_relay = true` is what lets the lead approve prompts. The folder and file must be writable by this Windows account only, or the server rejects them with `Configuration must be user-owned`. Fix the permissions with `icacls <path> /inheritance:d`, then remove any other SIDs. Write the file as UTF-8 without a BOM. After any change, run `server.py stop`.
- agy rules: the `permissions.allow` and `permissions.deny` lists in `~/.gemini/antigravity-cli/settings.json`. Deny beats Ask, and Ask beats Allow. On this Windows 10 machine there is no sandbox, so agy checks each shell command as one whole line (`unsandboxed(<line>)`). Two consequences, both tested:
  - Prefix rules such as `command(git)` never match, not even `git --version`. Only `command(*)` and `command(regex:...)` work.
  - Write every command deny as a whole-line regex that finds the words anywhere in the line, case-insensitive, so it also catches them inside compound PowerShell: `command(regex:(?i).*(?:^|[^\w-])git\s+push(?:[^\w-]|$).*)`. Keep spaces out of the pattern. Use `\s+`.
  - A deny rule matches the word anywhere, so a harmless line that happens to contain one (for example `Write-Output "format"`) is blocked too. Reword the command, or narrow the rule.

  To change a rule, edit `setup/agy-permissions.json`, then re-run `setup.ps1`. To prove a deny rule works, run a one-shot `agy -p` with `--mode accept-edits` in a temp git repo, asking it to run the command exactly. It reports `BLOCKED ... Matches user-configured deny rule`. Timestamped backups sit next to the file as `settings.json.bak-*`. New workers pick up rule changes, and running ones keep the old rules.
- Waiter: `scripts/wait.py` calls `server.py call agy_requests` and `agy_list`. If it exits with `error`, run `doctor`.
- Upgrade: run `server.py stop`, then `git -C C:\Tools\antigravity-mcp fetch --tags`, check out the new tag, and restart Claude Code.
