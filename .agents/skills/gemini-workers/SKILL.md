---
name: gemini-workers
description: Gemini workers through the `antigravity` MCP server (Antigravity `agy` over ACP). Use when the user asks for Gemini or Antigravity, or to fan work out to parallel workers outside Claude.
---

# Gemini workers

You are the **lead**: you brief each **worker**, leave it alone while it works, review what it **commits**, and land the result. Gemini 4 Neon is a peer-level model. Trust it to plan, decide, test, format and commit on its own. Your tokens go into briefs and reviews, none into watching. You answer to the user for the result.

Work is **hands-off**: agy hard-denies the dangerous commands (push, history rewrites, recursive deletes, web requests, system changes, secrets) by its own rules, and the waiter's **gate** answers every routine prompt agy still raises. Some sessions prompt for every shell command; the gate absorbs that. You are the **gatekeeper** only for what the gate hands you.

The tools are `mcp__antigravity__agy_*`. If they are deferred, load them all with one ToolSearch call: `"+antigravity agy"`, max_results 30. The scripts are in `scripts/` beside this file; call them with `py -3 "$(cygpath -w "$HOME/.claude/skills/gemini-workers/scripts/<script>")"`.

## Defaults

- Model: `gemini-4-neon-medium`. Go up to `gemini-4-neon-high` for hard reasoning, or down to `gemini-3.8-flash-low` for mechanical work.
- Mode: `accept-edits` for work that changes files, `plan` for pure research.
- At most 4 live workers, the server's cap.
- Pick a **layout** per run, and name it in every brief:
  - **Worktrees**: one per worker, made with `worktree.py create <repo> <base-branch> <name> ...` (folders in `<repo>-wt/<name>`, branch `<name>`); pass each path as `workdir`. agy's own `worktree` option is refused on Windows ("could not verify object ownership"). Isolated: workers may touch neighbouring files, and each one builds and tests alone. Costs a dependency install per worktree, a land step, and shared services that see none of it until landed.
  - **Shared checkout**: workers on the current branch, in the main checkout (`workdir` = the repo). Dependencies, untracked local files and shared services are there already, and commits land as they are made. **One worker at a time**: the broker reserves a worker's folder while its turn runs, a prompt waits, or its background work or native subagents may still run, and refuses any other task in that folder, or in a folder inside or around it, with `workspace_busy` (by design, with no setting to lift it). Follow-ups to the same worker are not affected. Start the next worker once the previous one has settled.

  The user's request or the project's guidelines decide first. Otherwise take the shared checkout for one worker, or for workers that run one after another; take worktrees for workers that run at the same time.
- Every call that changes something gets a fresh `request_id`. Reuse one only to retry the identical call.

## 1. Brief

A worker starts **cold**: it sees none of this conversation. Each brief carries:

- **Goal**: one sentence that states what done looks like.
- **Context**: file paths, conventions, decisions already made, and the project's hard rules (names it must never write, files it must never format). Tell it to read the project's `CLAUDE.md` or `AGENTS.md` first.
- **Scope**: the files and folders it owns. With parallel workers, also name the files the others edit, so it keeps out of them.
- **Environment**, by layout:
  - Worktrees: a fresh worktree has no installed dependencies and none of the untracked local files (`node_modules`, `vendor/`, `.env`). Tell it to install them, or where the main checkout's copy is. A shared local service (a Docker site, a running dev server) serves the main checkout, not the worktree: tests against it check old code, so leave them to the lead, who runs them after landing.
  - Shared checkout: "The user and earlier workers commit on this branch too. Stay on the branch. Stage only your own files, by path (never `git add -A` or `git add .`), and commit them by path. When git reports `index.lock`, wait a few seconds and retry. A test that fails in a file outside your scope may be someone else's work in progress: report it, leave it." Keep commands that rewrite many files (formatters, codegen run with write) on the worker's own paths.
- **Test**: the tests, typecheck, lint and formatter runs that prove the work. Take them from the project's scripts (`package.json`, `composer.json`, `pyproject.toml`).
- **Autonomy**: "Work to the end in one turn, without asking. Wait for long commands inside the turn. End the turn only when everything is committed and the tests pass, or when you are blocked, and then say why. Where a choice is open, take the conservative option and record it in the commit message."
- **Commit policy**, written out in full. The first source that speaks wins:
  1. **The user's request**, for example "one commit per component", "don't commit", or "squash at the end".
  2. **Project guidelines**: commit rules in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or `CONTRIBUTING.md`, including copies in subfolders on the worker's path. Look for message format (Conventional Commits, gitmoji, ticket prefixes), granularity, branch rules, and required checks. Match the house style in `git log -10 --format=%s`.
  3. **Default**: commit at each milestone and when done. Each message gives what changed, why, the decisions taken, and the test results.

  Always close the policy with: "Commits stay local: leave pushing, amending and history rewrites to the lead, and let the hooks run. A fix to an earlier commit goes in a new commit that names the commit it belongs to; the lead folds it."

Record the base commit with `git -C <repo> rev-parse HEAD`, then call `agy_start`. Keep each worker's `task_id` and base.

## 2. Wait

Start one background waiter for all your workers. Use the Bash tool with `run_in_background: true`:

```bash
py -3 "$(cygpath -w "$HOME/.claude/skills/gemini-workers/scripts/wait.py")" <task_id> [<task_id> ...] \
    [--any] [--shared] [--allow-path "<main checkout>"] --log "<scratchpad>/allowed.log"
```

The waiter is your only watch. It polls the broker locally and for free, and exits once with a JSON line (the output file adds a `[exited with code N]` line after it: read the first line). Its gate allows a worker's shell command, once, when the command matches no agy deny rule (requests to localhost excepted), none of the gate's lead rules (branch moves, amend, recursive or out-of-folder deletes, global installs, Docker cleanup), and names no absolute path outside the worker's folder, the `--allow-path` folders and agy's brain folder. Pass `--allow-path` for each folder workers may read outside their worktree, such as the main checkout. In a shared checkout, pass `--shared`: the gate then also hands you `git add -A` / `.` / `-u`, `git commit -a` and `git stash`, which would sweep up or hide files the user or an earlier worker left uncommitted. Until the waiter exits, stay idle or do other work.

- `settled` (exit 0): go to Review. With `--any`, review that worker, then start a new waiter for the rest.
- `attention` (exit 2): each request comes with `why` the gate left it to you. Settle it, then start the waiter again. Answer with `agy_respond`, the request's id as `request_id`.
  - **Question**: answer `{"answers": {...}}` from the user's request, taking the conservative option where the request is silent. Stop for the user only when the answer would change the result they asked for.
  - **Permission prompt**: reply `{"decision": "allow"}` (one-time) when the action serves the brief, stays in the worker's folder, and is reversible (deleting files git tracks is). Otherwise reply `{"decision": "deny"}` and `agy_send` the safe alternative. When the gate stops on a safe command class again and again, widen `LEAD_RULES` or `--allow-path` rather than answering each one (SETUP.md).
- `timeout` (exit 3): still working. Start it again.
- `error` (exit 1): see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 3. Review

The **evidence** is the worker's commits and diff:
- `git log --stat <base>..HEAD` in its worktree, then the diffs of the files that matter. In a shared checkout, the branch holds every worker's commits and the user's: take this worker's from the hashes its summary names, or `git log <base>..HEAD -- <its scope>`.
- `git status` and `git diff` for anything the policy left uncommitted.
- For a `plan` worker, which has no commits, `agy_get` `view: "result"`.

Check the work against the brief, every done-when criterion and every test the brief listed (a worker may skip one), and the commits against the policy. Open `agy_get` `view: "result"` only when the evidence leaves a gap, such as a failed test, missing commits, or a turn that ended with work left. A test that fails is pre-existing only when it fails the same way at the base commit: check out the base, rebuild, run it, return.

Then **accept** the worker, or **request changes** with `agy_send` (specific changes or questions) and go back to Wait. With worktrees, a worker that needs another worker's landed result: while it is idle, rebase its branch onto the target branch yourself, and tell it the new hashes in the next `agy_send`. In a shared checkout it already has that result.

## 4. Land

- **Worktrees**: bring every accepted commit onto the target branch, in dependency order, with `git cherry-pick` from the main checkout. Fold a worker's fix commit into the commit it names, when the project's rules allow the fold: `git cherry-pick <commit>`, `git cherry-pick -n <fix>`, `git commit --amend --no-edit` (interactive rebase is unavailable).
- **Shared checkout**: the commits are on the branch already. Fold a fix commit only once every worker is idle, and only when the project's rules allow a rewrite of the commits between the two; otherwise leave it on top.

Then run the full test list on the target branch, the shared-service tests included.

Clean up every time, without being asked: `agy_close` each task. With worktrees, then run `worktree.py cleanup <repo> <name> ...` (add `--into <branch>` when the target is not the main checkout's current branch). It deletes the folders, git's records and the branches, and keeps any branch with a change not on the target.

## 5. Report

For each worker, report its commits as landed (hash and subject), what you checked, the decisions it recorded, how many prompts the gate allowed and which ones you allowed or denied yourself, and what is left. `interrupted`, `failed` and `truncated` count as not done.

## When something breaks or changes

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md): a call returns `ok: false`, the waiter exits with `error`, every command prompts, a worktree is refused or will not delete, a task is `needs_resume`, `uncertain` or unexpectedly `closed`, a `possible_subagent_wait` warning appears, an `allow` is refused, or the server is down.
- [SETUP.md](SETUP.md): the user wants to change what workers may run or what the gate allows, a command is blocked or prompted when it shouldn't be, or the setup needs rebuilding or upgrading.
