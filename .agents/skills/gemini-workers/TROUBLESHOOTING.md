# Gemini workers: troubleshooting

Health check first: `py -3 C:\Tools\antigravity-mcp\server.py doctor`.

## Failed calls

`ok: false` comes with an `error.code`:

- `error.retryable`: repeat the identical call with the same `request_id`.
- `error.uncertain`: the action may already have happened. Inspect the task with `agy_get` before you do anything else.
- `not_signed_in`: ask the user to run `agy` in a terminal and sign in.
- `quota_exhausted` or `rate_limited`: tell the user and stop. The quota is shared by every worker.
- `workspace_busy`: another task holds that folder, or one inside or around it (`ids.blocking_task_id`, `claims`). A worker that is still working: wait for it, or give the new worker its own worktree (`worktree.py create`). A finished one that still holds it (`claims` kind `subagents` or `background`): `agy_close` it.

## Waiter exits with `error`

The broker call behind it (`server.py call agy_requests` or `agy_list`) failed. Run `doctor`. If the server is down, see the last section.

## Every command prompts

agy asks before each shell command, even with `allow: ["command(*)"]`. Seen on tasks started with a plain `workdir`: `~/.gemini/antigravity-cli/cli.log` shows `toolPermission=request-review`, and a deny rule then turns into a prompt instead of a block (an `Invoke-WebRequest` reached the lead). The waiter's gate handles this: it answers routine commands, and re-checks the deny rules itself, so a deny rule that agy skips still stops at the lead. Run the waiter with the gate on (the default) and read `why` on each request it hands you.

Root cause, tested on agy 1.5.14 with a bare ACP client: the `acp` engine never loads `settings.json` permissions (its log has no `CLI settings initialized` line, whatever `--cli_dir_name` is). Both `git --version` and a denied `curl` reach the client as prompts. The `headless` engine (`agy_start` with `engine: "headless"`) applies them natively. In the same tests, an allowed command ran with no request, a denied one came back `BLOCKED ... Matches user-configured deny rule`, and an `agy_send` follow-up kept the conversation. Headless costs mid-turn questions, mid-turn steering, and the thinking stream. Prefer it for long autonomous turns, or when no waiter will be running to gate the prompts.

## Worktrees

- `agy_start` with `worktree` fails with `worktree_refused` ("Windows could not verify object ownership or permissions"): make the worktrees with `scripts/worktree.py create` and start each worker on its folder with `workdir`.
- `git worktree remove --force` fails with "Directory not empty" (long `node_modules` paths on Windows), leaving the folder and the branch: run `scripts/worktree.py cleanup`, which deletes the folder with long-path support, prunes, and deletes the branch.

## A worker ends its turn with work left

Its summary says it is waiting ("waiting for completion", "running tests") or the done-when criteria are not met. `agy_send` the remaining items, tell it to wait for commands inside the turn, and start the waiter again.

## Interrupted or cut-off tasks

- `needs_resume` or `uncertain`: run `agy_resume`, then read its `reconciliation` (`unknown`, `next_steps`) and `agy_history` before you give it new work.
- `closed` while its `summary` says it was still working: a broker restart cut it off (`server.py stop`, or `setup.ps1` after a config change). Its conversation is kept. Read `git status` and `git log` in its folder for what landed, then `agy_send` a prompt asking it to find where it stopped and finish. `agy_send` reopens the session.
- A task is not found: `scripts/prune.py` deletes the broker's record of a worker whose last message is more than 7 days old, unless the user pinned it. Its Antigravity conversation remains: find it with `agy_sessions` (`action: "list"`) and import it.

## Stuck native subagent

`possible_subagent_wait` means the worker's own subagent may be waiting on an approval that agy 1.5.x does not forward over ACP. `agy_send` a follow-up asking the worker to check its subagents, or interrupt it.

## `allow` is refused

`approval_relay` is off, or the server rejected its config. Run `doctor`, then see SETUP.md (Server config). Until it is fixed, deny the prompt and tell the user.

## Server down: one-shot CLI

This path has no questions, approvals or follow-ups. Use the Bash tool. Put `-p` last, because it takes the next token as the prompt and agy does not read stdin:

```bash
agy --model gemini-4-neon-medium --output-format json --print-timeout 600s --mode accept-edits \
    -p "$(cat "<scratchpad>/brief.md")"
```

Read `.response`. Any `status` other than `"SUCCESS"` is a failure.
