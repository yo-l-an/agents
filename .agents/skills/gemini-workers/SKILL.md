---
name: gemini-workers
description: Gemini workers via the `antigravity` MCP server (Antigravity `agy` over ACP). Use when the user asks for Gemini or Antigravity, or to fan work out to parallel workers outside Claude.
---

# Gemini workers

You are the **lead**: you brief each **worker**, leave it alone while it works, and review what it **commits**. Gemini 4 Neon is a peer-level model. Trust it to plan, decide, and test on its own. Your tokens go into briefs and reviews, and none go into watching. You answer to the user for the result.

Two layers make **hands-off** safe:
- agy's own rules in `~/.gemini/antigravity-cli/settings.json` run every shell command without a prompt (`command(*)`), and hard-deny the dangerous ones: push, reset, recursive deletes, web requests, remote code, system changes, and writes to secrets and agent configs. Deny wins over any approval.
- You are the **gatekeeper** for the rare prompt left over, such as a URL, an MCP tool, or a file outside the workspace.

The tools are `mcp__antigravity__agy_*`. If they are deferred, load them all with one ToolSearch call: `"+antigravity agy"`, max_results 30.

## Defaults

- Model: `gemini-4-neon-medium`. Go up to `gemini-4-neon-high` for hard reasoning, or down to `gemini-3.8-flash-low` for mechanical work.
- Mode: `accept-edits` for work that changes files, `plan` for pure research. agy's `auto` mode is not available on this Windows 10 PC.
- At most 4 live workers, the server's cap. Give each worker its own folder. In a shared git repo, pass `worktree: {"repo", "name"}` so each worker gets its own branch.
- Every call that changes something gets a fresh `request_id`. Reuse one only to retry the identical call.

## 1. Brief

A worker starts **cold**: it sees none of this conversation. Each brief carries:

- **Goal**: one sentence that states what done looks like.
- **Context**: file paths, conventions, and decisions already made.
- **Scope**: the files and folders it owns.
- **Test**: the command or check that proves the work.
- **Autonomy**: "Work to the end without asking. Where a choice is open, take the conservative option and record it in the commit message."
- **Commit policy**: work it out before you brief, then write it out in full. The worker commits on its own by following it. The first source that speaks wins:
  1. **The user's request**, for example "one commit per component", "don't commit", or "squash at the end".
  2. **Project guidelines**: commit rules in the repo's `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or `CONTRIBUTING.md`, including any in subfolders on the worker's path. Look for message format (Conventional Commits, gitmoji, ticket prefixes), granularity, branch rules, and required checks before committing. Also check `git log -10 --format=%s` for the house style.
  3. **Default**: commit at each milestone and when done. Each message gives what changed, why, the decisions taken, and the test results.

  Always add: "Never push, never amend or rewrite existing commits, and let the hooks run." Also tell the worker to read the project's `CLAUDE.md` or `AGENTS.md` itself before it starts.

Before `agy_start`, record the base commit: `git -C <repo> rev-parse HEAD`. Keep the `task_id` and the base for each worker.

## 2. Wait

Start one background waiter for all your workers. Use the Bash tool with `run_in_background: true`:

```bash
py -3.15 "$(cygpath -w "$HOME/.claude/skills/gemini-workers/scripts/wait.py")" <task_id> [<task_id> ...] [--any]
```

It checks the broker every 30 s, locally and for free, and exits once with a compact JSON report. You are notified when it exits. Until then, stay idle or do other work, and leave `agy_events` alone.

- `settled` (exit 0): go to Review. With `--any`, review that worker, then start a new waiter for the rest.
- `attention` (exit 2): handle the pending requests (see below), then start the waiter again.
- `timeout` (exit 3): still working. Start it again.
- `error` (exit 1): see TROUBLESHOOTING.md.

Requests:
- **Question**: answer it with `agy_respond` `{"answers": {...}}`, using the user's request. Take the conservative option where it's open. Stop for the user only when the answer would change the result they asked for.
- **Permission prompt**: decide it with `agy_respond`.
  - `{"decision": "allow"}` (one-time) when the command serves the brief, stays in the worker's folder, and is reversible.
  - `{"decision": "deny"}` for anything else, followed by `agy_send` naming the safe alternative.

## 3. Review

Read the **checkpoints**: `git log --stat <base>..HEAD` in the worker's folder or worktree branch, then the diffs of the files that matter. Add `git status` and `git diff` for the work the policy left uncommitted. The commits and the diff are the evidence. Check the commits follow the policy you gave. Read `agy_get` `view: "result"` only when the evidence leaves something unexplained, for example a failed test, or changes the policy says should have been committed.

Then either:
- **Accept** the worker: it is done.
- **Request changes**: `agy_send` with specific changes or questions, then back to Wait.

The step is done when every worker is accepted, failed (with the reason), or handed to the user. For a worktree, use `agy_worktrees` `handoff` and show the patch to the user. Then `agy_close` each task.

## 4. Report

For each worker, report its commits (hash and subject), what you checked, the decisions it recorded, any prompts you allowed or denied, and what is left. `interrupted`, `failed`, and `truncated` count as not done.

## When something breaks

Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) when any of these happen: a call returns `ok: false`, the waiter exits with `error`, a task is `needs_resume`, `uncertain` or unexpectedly `closed`, you see a `possible_subagent_wait` warning, an `allow` is refused, the server is down, or the setup needs rebuilding, configuring or upgrading.
