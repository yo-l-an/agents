"""Offline check of the waiter's gate: routine commands allowed, risky ones escalated.

    py -3 setup/check-gate.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import wait

W = r"F:\work\repo-wt\step1"
rules = wait.deny_rules()
ALLOW = [
    "cd wp/x; git status -sb; git log -10 --format=\"%h %s\"",
    "cd wp/x; pnpm install",
    "git worktree list; Test-Path \"F:\\work\\repo\\vendor\\autoload.php\"",
    "cd wp/x; Remove-Item src/a.page.ts, src/b.page.ts",
    "try { (Invoke-WebRequest -Uri \"http://localhost:8080/wp-admin/\" -UseBasicParsing).StatusCode } catch { 1 }",
    "Select-String -Path \"" + wait.BRAIN + "\\abc\\output.txt\" -Pattern OK",
    "pnpm test:e2e overlays",
    "git add -A; git commit -m \"Tests: x\"",
    "Get-Content F:\\work\\repo-wt\\step1\\wp\\a.ts",
]
ESCALATE = [
    "git push",
    "git checkout main",
    "git commit --amend --no-edit",
    "git reset --hard HEAD~1",
    "Remove-Item -Recurse -Force dist",
    "Remove-Item F:\\work\\repo\\a.ts",
    "curl https://example.com",
    "Invoke-WebRequest https://example.com -OutFile y",
    "Get-Content C:\\Users\\me\\.ssh\\id_rsa",
    "Set-Content ..\\..\\x.txt a",
    "npm install -g foo",
    "git worktree add ../x",
]
bad = 0
for c in ALLOW:
    why = wait.risk(c, W, [r"F:\work\repo"], rules)
    if why:
        bad += 1
        print("WRONGLY ESCALATED:", c, "->", why)
for c in ESCALATE:
    if not wait.risk(c, W, [r"F:\work\repo"], rules):
        bad += 1
        print("WRONGLY ALLOWED:", c)
# --shared: workers on one branch in one checkout.
SHARED_ALLOW = [
    "git add src/a.ts src/b.ts; git commit -m \"Feat: a\" -- src/a.ts src/b.ts",
    "git add -- docs/x.md",
    "git commit -m \"Docs: x\"",
    "git status --short",
]
SHARED_ESCALATE = [
    "git add -A; git commit -m \"Feat: a\"",
    "git add .",
    "git add -u",
    "git commit -am \"Feat: a\"",
    "git stash",
    "git stash pop",
]
for c in SHARED_ALLOW:
    why = wait.risk(c, r"F:\work\repo", [], rules, shared=True)
    if why:
        bad += 1
        print("WRONGLY ESCALATED (shared):", c, "->", why)
for c in SHARED_ESCALATE:
    if not wait.risk(c, r"F:\work\repo", [], rules, shared=True):
        bad += 1
        print("WRONGLY ALLOWED (shared):", c)
total = len(ALLOW) + len(ESCALATE) + len(SHARED_ALLOW) + len(SHARED_ESCALATE)
print(f"{total} cases ({len(SHARED_ALLOW) + len(SHARED_ESCALATE)} shared), {bad} wrong")
sys.exit(1 if bad else 0)
