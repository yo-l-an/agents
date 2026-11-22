"""Block until Gemini workers need the lead, polling the antigravity broker locally.

    py -3 wait.py TASK_ID [TASK_ID ...] [--any] [--interval 30] [--timeout 14400]

Exits with one compact JSON report:
  0  settled      every task (or one, with --any) finished its turn with no background work
  2  attention    a question or permission prompt is pending
  3  timeout      still working after --timeout seconds (just run it again)
  1  error        the broker call failed
"""
import argparse
import json
import subprocess
import sys
import time

SERVER = r"C:\Tools\antigravity-mcp\server.py"
DONE = {"completed", "failed", "interrupted", "truncated", "cancelled", "error"}


def call(tool, args):
    out = subprocess.run([sys.executable, SERVER, "call", tool, "--args", json.dumps(args)],
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    data = json.loads(out.stdout or "{}")
    if not data.get("ok"):
        raise RuntimeError(out.stdout.strip() or out.stderr.strip())
    return data


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
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--timeout", type=int, default=4 * 3600)
    a = ap.parse_args()

    deadline = time.time() + a.timeout
    while True:
        try:
            pending = [r for tid in a.task_ids for r in call("agy_requests", {"task_id": tid}).get("requests", [])]
            tasks = {t["task_id"]: t for t in call("agy_list", {"limit": 100}).get("tasks", [])}
        except Exception as exc:  # broker down or bad id: report, let the lead decide
            print(json.dumps({"result": "error", "error": str(exc)[:1000]}))
            return 1
        watched = [tasks.get(tid, {"task_id": tid, "status": "unknown"}) for tid in a.task_ids]

        if pending:
            print(json.dumps({"result": "attention", "requests": pending, "tasks": [brief(t) for t in watched]}, ensure_ascii=False))
            return 2
        done = [settled(t) for t in watched]
        if (any(done) if a.any else all(done)):
            print(json.dumps({"result": "settled", "tasks": [brief(t) for t in watched]}, ensure_ascii=False))
            return 0
        if time.time() > deadline:
            print(json.dumps({"result": "timeout", "tasks": [brief(t) for t in watched]}, ensure_ascii=False))
            return 3
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
