#!/usr/bin/env bash
# Second build tab: progress bar, one summary line per Ninja step, and green
# streaks drifting behind the text. See scripts/build-live.py for details.
# Usage: scripts/build-live.sh      (Ctrl-C quits; the build keeps going)
exec python3 -I "$(dirname "$(readlink -f "$0")")/build-live.py" "$@"
