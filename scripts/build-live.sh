#!/usr/bin/env bash
# Live progress display: progress bar(s), one summary line per step, and green
# streaks drifting behind the text. See scripts/build-live.py for details.
# Usage: scripts/build-live.sh [sync]   (Ctrl-C quits; the build or sync keeps going)
#   sync  show a running `repo sync` (two bars: projects, size on disk). It is also
#         chosen automatically when a sync is running and no build is. From Windows
#         use the bare word: wsl.exe swallows --sync.
exec python3 -I "$(dirname "$(readlink -f "$0")")/build-live.py" "$@"
