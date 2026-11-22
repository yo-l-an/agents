---
name: gemini-workers
description: Gemini workers via the `antigravity` MCP server (Antigravity `agy` over ACP). Use when the user asks for Gemini or Antigravity, or to fan work out to parallel workers outside Claude.
---

# Gemini workers

You are the **lead**: you split the work, brief each **worker**, follow it, answer it, and verify what it hands back. The workers do the work, and you answer to the user for the result.

You run **unattended**: you settle every question and permission prompt yourself, and the user hears from you at the end. Two layers keep this safe. agy hard-denies dangerous commands with its own `deny` rules in `~/.gemini/antigravity-cli/settings.json`, and those win over any approval. You are the **gatekeeper** for everything else.

The tools are `mcp__antigravity__agy_*`. If they are deferred, load them all with one ToolSearch call: `"+antigravity agy"`, max_results 30.

## Defaults

- Model: `gemini-4-neon-medium`. Go up to `gemini-4-neon-high` for hard reasoning, or down to `gemini-3.8-flash-low` for mechanical work.
- Mode: `plan` for reading and review, `accept-edits` for edits. In `accept-edits`, workspace file edits run without a prompt, and each shell command comes to you as a prompt. agy's own `auto` mode is not available on this Windows 10 PC.
- At most 4 live workers, the server's cap. Give each worker its own folder. In a shared git repo, pass `worktree: {"repo", "name"}` so each worker gets its own worktree.
- Every call that changes something gets a fresh `request_id`. Reuse one only to retry the identical call.

## 1. Brief

A worker starts **cold**: it sees none of this conversation. Each brief carries:

- **Goal**: one sentence that states what done looks like.
- **Context**: file paths, conventions, and decisions already made.
- **Scope**: the files it may touch. All other files, git commits, and installs stay with you.
- **Test**: the command or check that proves the work.
- **Return**: files changed, commands run with their exit codes, and what is uncertain.

Start each worker with `agy_start`, and keep its `task_id`.

## 2. Follow

Poll `agy_events` with the last `cursor` and `wait_seconds: 25`. Fetch again at once while `has_more` is true. To watch several workers, pass `task_ids` with `view: "outcome"`.

Handle every pending request on each page:

- **Question**: answer it yourself with `agy_respond` `{"answers": {...}}`. Use the user's request and this conversation. Where they leave the answer open, pick the conservative choice and note it for the report. Stop and ask the user only when the answer would change the result they asked for.
- **Permission prompt**: decide it as gatekeeper with `agy_respond`.
  - Reply `{"decision": "allow"}` (one-time) when the command **serves the brief**, stays inside the worker's folder, and is **reversible**. Examples: build, test, lint and typecheck runs; read-only inspection (`git status`, `git diff`, `ls`); installing from the project's own manifest.
  - Reply `{"decision": "deny"}` to everything else: anything that leaves scope, reaches the network, deletes outside the worker's folder, rewrites git history or remotes, touches system settings or secrets, or that you cannot read clearly. Follow each denial with `agy_send` naming the safe alternative, and note it for the report.

To redirect a worker, use `agy_send`. Add `steer: true` and `expected_turn_id` to change course mid-turn. To change model or mode, use `agy_settings`. To stop a worker, use `agy_interrupt`.

The step is done when every worker is **settled**: its turn has ended, `activity` is not `"background"`, and no requests are pending.

## 3. Verify

Read `agy_get` with `view: "result"`. It separates the worker's **claims** (`final_message`) from its **evidence** (edits, commands, denied actions). Trust the evidence. Check it yourself with `agy_diff`, and run the tests or build.

For a worktree, use `agy_worktrees` `handoff` and show the patch to the user. The user decides when it is removed.

The step is done when every worker is accounted for as one of: verified, failed (with the reason), or handed to the user. Then `agy_close` each task.

## 4. Report

For each worker, report what it did, what you checked, and what is left. Also list the permission prompts you allowed and denied, and the open questions you answered for the user. `interrupted`, `failed`, and `truncated` count as not done.

## When something breaks

Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) when any of these happen: a call returns `ok: false`, a task is `needs_resume` or `uncertain`, you see a `possible_subagent_wait` warning, an `allow` is refused, the server is down, or the setup needs rebuilding, configuring or upgrading.
