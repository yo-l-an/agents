"""Idempotent JSON merges for setup.ps1. Each run backs up the target first.

    merge.py agy    <agy settings.json> <agy-permissions.json> <home as /Users/name>
    merge.py allow  <claude settings.json> <rule>
"""
import json
import shutil
import sys
import time
from pathlib import Path


def load(path):
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def save(path, data):
    p = Path(path)
    if p.exists():
        shutil.copy2(p, p.with_name(p.name + ".bak-" + time.strftime("%Y%m%d-%H%M%S")))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_rules(data, key, rules):
    perm = data.setdefault("permissions", {})
    current = perm.setdefault(key, [])
    added = [r for r in rules if r not in current]
    current.extend(added)
    return added


def main():
    cmd = sys.argv[1]
    if cmd == "agy":
        target, template, home = sys.argv[2:5]
        spec = load(template)
        data = load(target)
        added = []
        for key in ("allow", "deny"):
            added += add_rules(data, key, [r.replace("{HOME}", home) for r in spec.get(key, [])])
    elif cmd == "allow":
        target, rule = sys.argv[2:4]
        data = load(target)
        added = add_rules(data, "allow", [rule])
    else:
        sys.exit(f"unknown command {cmd}")
    if added:
        save(target, data)
    print(f"{cmd}: {len(added)} rule(s) added to {target}")


if __name__ == "__main__":
    main()
