"""Block until the Gemini models' quota is usable again. The lead runs it in the background when a
worker stops on `quota_exhausted` or `rate_limited`, then resumes the workers.

    py -3 quota_wait.py [--min-wait 0] [--interval 900] [--timeout 0]

Reads the quota with `agy -p /usage`, a slash command that spends no quota and saves no conversation.
While a Gemini bucket (5-hour or weekly) is used up, it sleeps until that bucket's reset time, re-checking
at least every --interval seconds. --min-wait holds it that long first (use 120 after `rate_limited`, whose
cause the quota does not show). --timeout 0 waits as long as it takes.

Exits with one JSON line:
  0  available   every Gemini bucket has quota left: `usage` lists each bucket's percentage used
  3  timeout     still used up after --timeout seconds
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime

EMPTY = 0.01  # a bucket with less than 1% left counts as used up


def gemini_buckets():
    agy = shutil.which("agy")
    out = subprocess.run([agy, "--output-format", "json", "-p", "/usage"], capture_output=True, text=True,
                         encoding="utf-8", timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    groups = json.loads(out.stdout)["command"]["data"]["groups"]
    group = next((g for g in groups if g["name"].lower() == "gemini models"), None) \
        or next(g for g in groups if "gemini" in g["name"].lower())
    return group["buckets"]


def reset_at(bucket):
    try:
        return datetime.fromisoformat(bucket["reset_time"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError):
        return None


def summary(buckets):
    return {b.get("window") or b.get("id"): {"used": round(100 * (1 - b.get("remaining_fraction", 1))),
                                             "reset_time": b.get("reset_time")} for b in buckets}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-wait", type=int, default=0)
    ap.add_argument("--interval", type=int, default=900)
    ap.add_argument("--timeout", type=int, default=0)
    a = ap.parse_args()
    start = time.time()
    time.sleep(a.min_wait)
    while True:
        try:
            buckets = gemini_buckets()
        except Exception:  # agy busy, offline or signed out: try again later
            buckets = None
        if buckets is not None:
            empty = [b for b in buckets if b.get("remaining_fraction", 1) < EMPTY]
            if not empty:
                print(json.dumps({"result": "available", "waited_minutes": round((time.time() - start) / 60),
                                  "usage": summary(buckets)}))
                return 0
            resets = [r for r in map(reset_at, empty) if r]
            pause = min(a.interval, max(60, (max(resets) if resets else 0) - time.time() + 60))
        else:
            pause = 300
        if a.timeout and time.time() + pause - start > a.timeout:
            print(json.dumps({"result": "timeout", "usage": summary(buckets or [])}))
            return 3
        time.sleep(pause)


if __name__ == "__main__":
    sys.exit(main())
