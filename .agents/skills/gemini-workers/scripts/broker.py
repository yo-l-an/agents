"""Where antigravity-mcp lives on this machine, for the skill's scripts. Works on Windows, macOS and Linux.

- server_path(): the server.py Claude Code runs, read from its MCP registration (~/.claude.json, server
  "antigravity"). Override with the ANTIGRAVITY_MCP_SERVER environment variable.
- find_db(): the broker's state.sqlite3, from the server's own rules: `state_dir` in its config, else
  %LOCALAPPDATA%\\AntigravityMCP (Windows) or $XDG_STATE_HOME/antigravity-mcp, ~/.local/state/antigravity-mcp.
"""
import glob
import json
import os
from pathlib import Path

DEFAULT_INSTALL = Path.home() / "tools" / "antigravity-mcp"
WINDOWS = os.name == "nt"


def server_path():
    env = os.environ.get("ANTIGRAVITY_MCP_SERVER")
    if env:
        return Path(env)
    try:
        entry = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))["mcpServers"]["antigravity"]
        for arg in entry.get("args", []):
            if arg.endswith("server.py"):
                return Path(arg)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return DEFAULT_INSTALL / "server.py"


def config_paths():
    """The server's config file. On Windows, the Claude desktop app (MSIX) keeps its own copy."""
    if WINDOWS:
        roaming = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return [Path(roaming) / "AntigravityMCP" / "config.toml",
                *map(Path, glob.glob(os.path.join(local, "Packages", "*", "LocalCache", "Roaming",
                                                  "AntigravityMCP", "config.toml")))]
    return [Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "antigravity-mcp" / "config.toml"]


def state_dirs():
    dirs = []
    for cfg in config_paths():
        try:
            import tomllib
            state = tomllib.loads(cfg.read_text(encoding="utf-8")).get("state_dir")
            if state:
                dirs.append(Path(state).expanduser())
        except (OSError, ValueError, ImportError):
            pass
    if WINDOWS:
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        dirs.append(Path(local) / "AntigravityMCP")
        # A broker started by a packaged (MSIX) app, such as the Claude desktop app, writes into that app's
        # LocalCache, which only the app's own processes see at the plain path.
        dirs += map(Path, glob.glob(os.path.join(local, "Packages", "*", "LocalCache", "Local", "AntigravityMCP")))
    else:
        dirs.append(Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "antigravity-mcp")
    return dirs


def find_db():
    """The most recently written state.sqlite3 among the candidate state folders."""
    found = [str(d / "state.sqlite3") for d in state_dirs()]

    def written(p):
        return max((os.path.getmtime(f) for f in (p, p + "-wal") if os.path.exists(f)), default=-1)

    return max(found, key=written)


if __name__ == "__main__":
    # For the setup scripts: `python broker.py server` prints the server.py in use (or the default).
    import sys
    print(server_path() if sys.argv[1:] == ["server"] else find_db())
