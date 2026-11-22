"""Block until Gemini workers need the lead, polling the antigravity broker locally. Gates routine prompts on the way.

    py -3 wait.py TASK_ID [TASK_ID ...] [--any] [--shared] [--allow-path DIR ...] [--no-gate] [--log FILE]
                  [--interval 20] [--timeout 14400]

The gate answers a worker's shell-command prompt with a one-time `allow` when the command is routine: it matches no
deny rule of setup/agy-permissions.json (web requests to localhost excepted), none of LEAD_RULES below, and names no
absolute path outside the worker's folder, the --allow-path folders, and agy's own brain folder. Every other request
(a risky command, another tool, a question) ends the wait for the lead.

Exits with one JSON line:
  0  settled      every task (or one, with --any) finished its turn with no background work
  2  attention    a request needs the lead: `requests` (compact, with `why`), `allowed` (what the gate let through)
  3  timeout      still working after --timeout seconds (just run it again)
  1  error        the broker call failed
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SERVER = r"C:\Tools\antigravity-mcp\server.py"
RULES_FILE = Path(__file__).resolve().parent.parent / "setup" / "agy-permissions.json"
BRAIN = str(Path.home() / ".gemini" / "antigravity-cli" / "brain")
DONE = {"completed", "failed", "interrupted", "truncated", "cancelled", "error"}

# What the lead keeps for itself even where agy allows it: branch and history moves, deletes, escapes, machine state.
LEAD_RULES = [
    r"git\s+(checkout|switch|merge|cherry-pick|reset|rebase|tag|remote|config|update-ref|stash\s+(drop|clear))\b",
    r"git\s+commit\b.*--amend",
    r"git\s+branch\s+-[dDmMfc]",
    r"git\s+worktree\s+(add|remove|prune|move)",
    r"(Remove-Item|\brm|\bri|\bdel|\berase|\brd|\brmdir)\b[^;|&]*\s[-/](r|s|Recurse|fr|rf)\b",
    r"(Remove-Item|\brm|\bdel|Move-Item|\bmv)\b[^;|&]*([A-Za-z]:[\\/]|\.\.[\\/])",
    r"\.\.[\\/]\.\.[\\/]",
    r"\b(npm|pnpm|yarn)\s+(i|install|add)\b[^;|&]*\s(-g|--global)\b",
    r"docker\s+(rm|rmi|system|volume|network|image|compose\s+down)\b",
    r"\[Environment\]::Set|Set-ItemProperty|New-ItemProperty",
]
# With --shared (workers on one branch in one checkout): commands that sweep up or hide other workers' files.
SHARED_RULES = [
    r"git\s+add\s+(-A|--all|\.|:/|-u|--update)(\s|$|;)",
    r"git\s+commit\b[^;|&]*\s-[a-zA-Z]*a",
    r"git\s+stash\b",
]
WEB_TOOLS = re.compile(r"(?i)curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm")
URL = re.compile(r"(?i)https?://([^/\s\"':]+)")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
# Stops at spaces and shell separators, not at `'` (a Windows user folder may hold one); trailing quotes are stripped.
ABS_PATH = re.compile(r"(?<![\w/])([A-Za-z]:[\\/][^\s\";|&<>]*)")


def call(tool, args):
    out = subprocess.run([sys.executable, SERVER, "call", tool, "--args", json.dumps(args)],
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    data = json.loads(out.stdout or "{}")
    if not data.get("ok"):
        raise RuntimeError(out.stdout.strip() or out.stderr.strip())
    return data


def deny_rules():
    """agy's command deny regexes, each flagged when it targets a web tool."""
    rules = []
    if RULES_FILE.exists():
        for rule in json.loads(RULES_FILE.read_text(encoding="utf-8")).get("deny", []):
            m = re.fullmatch(r"command\(regex:(.+)\)", rule)
            if m:
                is_web = bool(WEB_TOOLS.search(m.group(1).replace("\\", "")))  # rules escape hyphens: Invoke\-WebRequest
                rules.append((is_web, re.compile(m.group(1).replace("(?i)", ""), re.I)))
    return rules


def norm(path):
    return os.path.normcase(os.path.normpath(path.rstrip("\\/")))


def risk(command, workdir, allowed_paths, rules, shared=False):
    """Why the gate leaves this command to the lead, or None when it is routine."""
    hosts = URL.findall(command)
    local_only = bool(hosts) and all(host.lower() in LOCAL_HOSTS for host in hosts)
    for is_web, rx in rules:
        if rx.fullmatch(command) and not (is_web and local_only):
            return "matches an agy deny rule that agy did not enforce"
    for pattern in LEAD_RULES:
        if re.search(pattern, command, re.I):
            return f"lead rule: {pattern}"
    for pattern in SHARED_RULES if shared else []:
        if re.search(pattern, command):
            return f"shared checkout rule: {pattern}"
    roots = [norm(p) for p in [workdir, BRAIN, *allowed_paths] if p]
    for path in ABS_PATH.findall(command):
        path = path.rstrip("')")
        p = norm(path)
        if not any(p == r or p.startswith(r + os.sep) for r in roots):
            return f"path outside the worker's folders: {path}"
    return None


def compact(request, why):
    row = {k: request.get(k) for k in ("request_id", "task_name", "kind", "tool_name") if request.get(k)}
    row["command"] = (request.get("command") or request.get("title") or "")[:500]
    row["why"] = why
    if request.get("kind") != "permission":
        row["request"] = request
    return row


def settled(task):
    return task.get("turn_status") in DONE and task.get("activity") != "background"


def brief(task):
    keys = ("task_id", "name", "status", "turn_status", "activity", "stop_reason", "error")
    row = {k: task.get(k) for k in keys if task.get(k) is not None}
    row["summary"] = (task.get("summary") or "").strip()[-600:]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_ids", nargs="+")
    ap.add_argument("--any", action="store_true", help="return when the first task settles")
    ap.add_argument("--allow-path", action="append", default=[], help="extra folder a command may name (repeat)")
    ap.add_argument("--no-gate", action="store_true", help="report every request instead of gating")
    ap.add_argument("--shared", action="store_true", help="workers share one checkout: escalate add -A, commit -a, stash")
    ap.add_argument("--log", help="append each allowed command to this file")
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=4 * 3600)
    a = ap.parse_args()

    # Housekeeping, detached so it never delays the wait: forget workers idle for over 7 days.
    subprocess.Popen([sys.executable, str(Path(__file__).with_name("prune.py"))],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)

    rules = deny_rules()
    allowed = []
    deadline = time.time() + a.timeout
    while True:
        try:
            pending = [r for tid in a.task_ids for r in call("agy_requests", {"task_id": tid}).get("requests", [])
                       if r.get("status", "pending") == "pending"]
            escalate = []
            for r in pending:
                if a.no_gate:
                    why = "gate off"
                elif r.get("kind") != "permission" or r.get("tool_name") != "run_command":
                    why = "not a shell command"
                else:
                    why = risk(r.get("command") or "", r.get("workdir") or "", a.allow_path, rules, a.shared)
                if why:
                    escalate.append(compact(r, why))
                    continue
                call("agy_respond", {"request_id": r["request_id"], "response": {"decision": "allow"}})
                line = f"{r.get('task_name')}: {(r.get('command') or '')[:200]}"
                allowed.append(line)
                if a.log:
                    with open(a.log, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
            tasks = {t["task_id"]: t for t in call("agy_list", {"limit": 100}).get("tasks", [])}
        except Exception as exc:  # broker down or bad id: report, let the lead decide
            print(json.dumps({"result": "error", "error": str(exc)[:1000]}))
            return 1
        watched = [tasks.get(tid, {"task_id": tid, "status": "unknown"}) for tid in a.task_ids]
        gated = {"allowed_count": len(allowed), "allowed": allowed[-20:]}

        if escalate:
            print(json.dumps({"result": "attention", "requests": escalate, **gated,
                              "tasks": [brief(t) for t in watched]}, ensure_ascii=False))
            return 2
        done = [settled(t) for t in watched]
        if (any(done) if a.any else all(done)):
            print(json.dumps({"result": "settled", **gated, "tasks": [brief(t) for t in watched]}, ensure_ascii=False))
            return 0
        if time.time() > deadline:
            print(json.dumps({"result": "timeout", **gated, "tasks": [brief(t) for t in watched]}, ensure_ascii=False))
            return 3
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
