#!/bin/bash
# Double-click in Finder to watch the Gemini workers live. Close this Terminal window to stop the viewer.
cd "$(dirname "$0")" || exit 1
exec python3 viewer.py "$@"
