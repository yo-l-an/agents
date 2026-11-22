"""Worker worktrees for a git repo, in a sibling folder `<repo>-wt/<name>`, one branch each.

    py -3 worktree.py create  REPO BASE NAME [NAME ...]
    py -3 worktree.py cleanup REPO NAME [NAME ...] [--into BRANCH] [--force]

create   adds a worktree and a branch NAME from BASE for each name; prints {name: path} as JSON.
cleanup  deletes each worktree folder (long node_modules paths included, where `git worktree remove` fails on
         Windows), prunes git's records, and deletes the branch. It refuses a branch with a commit whose change is not
         in --into (default: the repo's current branch; cherry-picked commits count as in), unless --force.
         It removes `<repo>-wt` once empty.
"""
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def git(repo, *args, check=True):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if check and out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout.strip()


def root_of(repo):
    return Path(git(repo, "rev-parse", "--show-toplevel"))


def home_of(root):
    return root.parent / f"{root.name}-wt"


def long_path(path):
    p = str(Path(path).resolve())
    return "\\\\?\\" + p if os.name == "nt" and not p.startswith("\\\\?\\") else p


def force_remove(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def create(a):
    root = root_of(a.repo)
    made = {}
    for name in a.names:
        path = home_of(root) / name
        git(root, "worktree", "add", "-b", name, str(path), a.base)
        made[name] = str(path)
    print(json.dumps(made, indent=1))


def cleanup(a):
    root = root_of(a.repo)
    into = a.into or git(root, "branch", "--show-current")
    report = {}
    for name in a.names:
        exists = git(root, "branch", "--list", name)
        unmerged = [l for l in git(root, "cherry", into, name).splitlines() if l.startswith("+")] if exists else []
        if unmerged and not a.force:
            report[name] = f"kept: {len(unmerged)} commit(s) not in {into} (use --force to drop them)"
            continue
        path = home_of(root) / name
        if path.exists():
            shutil.rmtree(long_path(path), onerror=force_remove)
        git(root, "worktree", "prune")
        if exists:
            git(root, "branch", "-D", name)
        report[name] = "removed"
    home = home_of(root)
    if home.exists() and not any(home.iterdir()):
        home.rmdir()
    print(json.dumps(report, indent=1))
    return 1 if any(v.startswith("kept") for v in report.values()) else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("repo")
    c.add_argument("base")
    c.add_argument("names", nargs="+")
    d = sub.add_parser("cleanup")
    d.add_argument("repo")
    d.add_argument("names", nargs="+")
    d.add_argument("--into")
    d.add_argument("--force", action="store_true")
    a = ap.parse_args()
    return create(a) if a.cmd == "create" else cleanup(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
