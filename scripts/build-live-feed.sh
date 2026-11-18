#!/usr/bin/env bash
# Feed for `build-live.py remote`: run on the build machine (the PC sends it over ssh on stdin,
# so nothing has to be installed there). It prints the build log as it grows, and every 2 s a status
# line for the display:
#   @@STATUS <unit or -> <unit start epoch> <now epoch> <soong_build RAM MB> <soong secs running> <soong CPU secs>
# Use: build-live.py remote   (env REMOTE_HOST=laptop, REMOTE_LOG=~/lineage/build.log)
LOG="${REMOTE_LOG:-$HOME/lineage/build.log}"

status() {
  while :; do
    u=$(systemctl --user list-units 'lineage-build-*' --no-legend --plain 2>/dev/null | awk '{print $1}' | head -1)
    start=0
    if [ -n "$u" ]; then
      ts=${u#lineage-build-}; ts=${ts%.scope}
      start=$(date -d "${ts:0:8} ${ts:9:2}:${ts:11:2}:${ts:13:2}" +%s 2>/dev/null || echo 0)
    fi
    set -- $(ps -C soong_build -o rss=,etimes=,cputimes= 2>/dev/null | head -1)
    echo "@@STATUS ${u:--} $start $(date +%s) $(( ${1:-0} / 1024 )) ${2:-0} ${3:-0}"
    sleep 2
  done
}

status &
exec tail -n 60 -F "$LOG" 2>/dev/null
