#!/usr/bin/env bash
# Rebuilds the gemini-workers setup on macOS or Linux. Safe to re-run: each step skips what is
# already in place, and every settings file it changes is backed up first.
#   bash <this skill>/setup/setup.sh [--version v0.1.1] [--install-dir DIR]
# The install folder defaults to the one Claude Code already runs, else ~/tools/antigravity-mcp.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
version="v0.1.1"
install_dir=""
while [ $# -gt 0 ]; do
    case "$1" in
        --version) version="$2"; shift 2 ;;
        --install-dir) install_dir="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
step() { printf '\n== %s\n' "$1"; }
fail() { echo "$1" >&2; exit 1; }

step "Prerequisites"
command -v agy >/dev/null || fail "agy not found. Install it: curl -fsSL https://antigravity.google/cli/install.sh | bash, then run agy once to sign in."
command -v git >/dev/null || fail "git not found."
command -v claude >/dev/null || fail "claude CLI not found."
python=""
for candidate in python3.15 python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
        python="$(command -v "$candidate")"; break
    fi
done
[ -n "$python" ] || fail "Python 3.11+ not found. Install it (macOS: brew install python, or python.org)."
echo "agy $(agy --version), python $python"
if [ -z "$install_dir" ]; then
    install_dir="$(dirname "$("$python" "$here/../scripts/broker.py" server)")"
fi
mkdir -p "$(dirname "$install_dir")"
install_dir="$(cd "$(dirname "$install_dir")" && pwd)/$(basename "$install_dir")"

step "antigravity-mcp $version in $install_dir"
if [ -f "$install_dir/server.py" ]; then
    echo "already installed: $("$python" "$install_dir/server.py" --version)"
else
    git -c advice.detachedHead=false clone --depth 1 --branch "$version" https://github.com/houyhlouis/antigravity-mcp.git "$install_dir"
fi

step "agy permission rules (all commands allowed, dangerous ones hard-denied)"
"$python" "$here/merge.py" agy "$HOME/.gemini/antigravity-cli/settings.json" "$here/agy-permissions.json" "$HOME"

step "Server config (approval_relay), readable by this account only"
cfg_dir="${XDG_CONFIG_HOME:-$HOME/.config}/antigravity-mcp"
cfg="$cfg_dir/config.toml"
mkdir -p "$cfg_dir"
chmod 700 "$cfg_dir"
changed=0
if ! cmp -s "$here/antigravity-mcp.config.toml" "$cfg"; then
    cp "$here/antigravity-mcp.config.toml" "$cfg"
    changed=1
fi
chmod 600 "$cfg"
# Restarting the broker closes live worker sessions, so only do it when the config changed.
if [ "$changed" = 1 ]; then
    echo "config changed: restarting broker"
    "$python" "$install_dir/server.py" stop >/dev/null || true
fi
"$python" "$install_dir/server.py" doctor | grep -E 'signed_in|acp_available|findings|^ok =' || true

step "Register MCP server in Claude Code (user scope)"
if claude mcp get antigravity >/dev/null 2>&1; then
    echo "already registered"
else
    claude mcp add --transport stdio --scope user antigravity -- "$python" "$install_dir/server.py" serve
fi

step "Claude Code allow rule"
"$python" "$here/merge.py" allow "$HOME/.claude/settings.json" "mcp__antigravity"
chmod +x "$here/../scripts/viewer.command" 2>/dev/null || true

printf '\nDone. Open a new Claude Code session to load the antigravity tools.\n'
