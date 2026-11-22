"""Deletes the broker's record (transcript, events, artifacts) of every worker that is not
active, not pinned in the viewer, and whose last message is older than --days (default 7).
wait.py starts it on each run.

    py -3 prune.py [--days 7] [--dry-run]

Deletion goes through the broker (`agy_close` with `action: "forget"`). Antigravity keeps
its own copy of each conversation in ~/.gemini/antigravity-cli.
"""
import argparse
import glob
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

SERVER = r"C:\Tools\antigravity-mcp\server.py"
ACTIVE = {"starting", "running", "waiting", "interrupting"}
# Pinned workers are never deleted. The file sits in the home folder, outside AppData, so the
# viewer (started from Explorer) and this script (started inside the Claude app) share it.
PINS = Path.home() / ".gemini-workers" / "pinned.json"


def load_pins():
    try:
        return set(json.loads(PINS.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def save_pins(pins):
    PINS.parent.mkdir(parents=True, exist_ok=True)
    tmp = PINS.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(pins)), encoding="utf-8")
    os.replace(tmp, PINS)


def find_db():
    """The broker's store. A broker started by a packaged (MSIX) app, such as the Claude desktop
    app, writes into that app's LocalCache, which only the app's own processes see at the plain
    path. Take the most recently written of the plain path and every package copy."""
    local = os.environ.get("LOCALAPPDATA", "")
    found = [os.path.join(local, "AntigravityMCP", "state.sqlite3")]
    found += glob.glob(os.path.join(local, "Packages", "*", "LocalCache", "Local", "AntigravityMCP", "state.sqlite3"))

    def written(p):
        return max((os.path.getmtime(f) for f in (p, p + "-wal") if os.path.exists(f)), default=-1)

    return max(found, key=written)


def stale(db, days):
    """(task_id, name, status, idle days) for every inactive, unpinned task whose last message
    is older than `days`. Without a message, its last event counts, then its creation."""
    c = sqlite3.connect(Path(db).as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        rows = c.execute("select id, status, created, data, "
                         "(select max(ts) from events where task = tasks.id and kind = 'message'), "
                         "(select max(ts) from events where task = tasks.id) from tasks").fetchall()
    finally:
        c.close()
    pins = load_pins()
    now = time.time()
    out = []
    for tid, status, created, data, last_message, last_event in rows:
        idle = (now - (last_message or last_event or created or now)) / 86400
        if status not in ACTIVE and tid not in pins and idle > days:
            out.append((tid, json.loads(data).get("name") or tid[:8], status, idle))
    return out


def forget(task_id):
    out = subprocess.run([sys.executable, SERVER, "call", "agy_close", "--args",
                          json.dumps({"task_id": task_id, "request_id": str(uuid.uuid4()), "action": "forget"})],
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    data = json.loads(out.stdout or "{}")
    return data.get("ok"), (data.get("error") or {}).get("message") or out.stderr.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    db = find_db()
    if not os.path.exists(db):
        return 0
    for tid, name, status, idle in stale(db, a.days):
        if a.dry_run:
            print(f"would forget {name} ({status}, idle {idle:.1f} days)")
            continue
        ok, err = forget(tid)
        print(f"{'forgot' if ok else 'FAILED'} {name} ({status}, idle {idle:.1f} days){'' if ok else ': ' + err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
