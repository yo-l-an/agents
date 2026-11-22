---
name: gemini-workers
description: Gemini workers through the `antigravity` MCP server (Antigravity `agy` over ACP). Use when the user asks for Gemini or Antigravity, or to fan work out to parallel workers outside Claude.
---

# Gemini workers

You are the **lead**: you brief each **worker**, leave it alone while it works, and review what it **commits**. Gemini 4 Neon is a peer-level model. Trust it to plan, decide, test, format and commit on its own. Your tokens go into briefs and reviews, none into watching. You answer to the user for the result.

Work is **hands-off** because agy runs every shell command without a prompt and hard-denies the dangerous ones (push, history rewrites, recursive deletes, web requests, system changes, secrets) by its own rules, which no approval overrides. You are the **gatekeeper** for the rare prompt left over.

The tools are `mcp__antigravity__agy_*`. If they are deferred, load them all with one ToolSearch call: `"+antigravity agy"`, max_results 30.

## Defaults

- Model: `gemini-4-neon-medium`. Go up to `gemini-4-neon-high` for hard reasoning, or down to `gemini-3.8-flash-low` for mechanical work.
- Mode: `accept-edits` for work that changes files, `plan` for pure research.
- At most 4 live workers, the server's cap. Give each worker its own folder. In a shared git repo, pass `worktree: {"repo", "name"}` so each worker gets its own branch.
- Every call that changes something gets a fresh `request_id`. Reuse one only to retry the identical call.

## 1. Brief

A worker starts **cold**: it sees none of this conversation. Each brief carries:

- **Goal**: one sentence that states what done looks like.
- **Context**: file paths, conventions, decisions already made. Tell it to read the project's `CLAUDE.md` or `AGENTS.md` first.
- **Scope**: the files and folders it owns.
- **Test**: the tests, typecheck, lint and formatter runs that prove the work. Take them from the project's scripts (`package.json`, `composer.json`, `pyproject.toml`).
- **Autonomy**: "Work to the end without asking. Where a choice is open, take the conservative option and record it in the commit message."
- **Commit policy**, written out in full. The first source that speaks wins:
  1. **The user's request**, for example "one commit per component", "don't commit", or "squash at the end".
  2. **Project guidelines**: commit rules in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or `CONTRIBUTING.md`, including copies in subfolders on the worker's path. Look for message format (Conventional Commits, gitmoji, ticket prefixes), granularity, branch rules, and required checks. Match the house style in `git log -10 --format=%s`.
  3. **Default**: commit at each milestone and when done. Each message gives what changed, why, the decisions taken, and the test results.

  Always close the policy with: "Commits stay local: leave pushing, amending and history rewrites to the lead, and let the hooks run."

Record the base commit with `git -C <repo> rev-parse HEAD`, then call `agy_start`. Keep each worker's `task_id` and base.

## 2. Wait

Start one background waiter for all your workers. Use the Bash tool with `run_in_background: true`:

```bash
py -3 "$(cygpath -w "$HOME/.claude/skills/gemini-workers/scripts/wait.py")" <task_id> [<task_id> ...] [--any]
```

The waiter is your only watch. It checks the broker every 30 s, locally and for free, and exits once with a compact JSON report. You are notified when it exits. Until then, stay idle or do other work.

- `settled` (exit 0): go to Review. With `--any`, review that worker, then start a new waiter for the rest.
- `attention` (exit 2): settle each pending request, then start the waiter again.
  - **Question**: answer it with `agy_respond` `{"answers": {...}}` from the user's request, taking the conservative option where the request is silent. Stop for the user only when the answer would change the result they asked for.
  - **Permission prompt**: reply `{"decision": "allow"}` (one-time) when the action serves the brief, stays in the worker's folder, and is reversible. Otherwise reply `{"decision": "deny"}` and `agy_send` the safe alternative.
- `timeout` (exit 3): still working. Start it again.
- `error` (exit 1): see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 3. Review

The **evidence** is the worker's commits and diff:
- `git log --stat <base>..HEAD` in its folder or worktree branch, then the diffs of the files that matter.
- `git status` and `git diff` for anything the policy left uncommitted.
- For a `plan` worker, which has no commits, `agy_get` `view: "result"`.

Check the work against the brief and the commits against the policy. Open `agy_get` `view: "result"` for a committing worker only when the evidence leaves a gap, such as a failed test or missing commits.

Then **accept** the worker, or **request changes** with `agy_send` (specific changes or questions) and go back to Wait.

The step is done when every worker is accepted, failed with a reason, or handed to the user. For a worktree, use `agy_worktrees` `handoff` and show the patch to the user. Then `agy_close` each task.

## 4. Report

For each worker, report its commits (hash and subject), what you checked, the decisions it recorded, the prompts you allowed or denied, and what is left. `interrupted`, `failed` and `truncated` count as not done.

## When something breaks or changes

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md): a call returns `ok: false`, the waiter exits with `error`, a task is `needs_resume`, `uncertain` or unexpectedly `closed`, a `possible_subagent_wait` warning appears, an `allow` is refused, or the server is down.
- [SETUP.md](SETUP.md): the user wants to change what workers may run, a command is blocked or prompted when it shouldn't be, or the setup needs rebuilding or upgrading.
