#!/usr/bin/env bash
# Feed for `build-live.py remote`: run on the build machine (the PC sends it over ssh on stdin,
# so nothing has to be installed there). It prints the build log as it grows, and every 2 s a status
# line for the display:
#   @@STATUS <unit or -> <unit start epoch> <now epoch> <soong_build RAM MB> <soong secs running> <soong CPU secs>
# and, ONCE each time a build has ended (and once at start-up for the most recent one), how it ended:
#   @@END <unit or -> <kind> <epoch> <text>
#     kind: OK (finished fine) | FAILED (ninja reported errors) | OOM (killed for memory, by
#           systemd-oomd or by the cgroup's own limit) | REBOOT (the machine restarted) | STOPPED
#           (the unit failed for another reason, or it is simply gone with no result: stopped by hand)
# `build-live.py` (local mode) calls `build-live-feed.sh outcome <unit|latest>` for the same text.
# Use: build-live.py remote   (env REMOTE_HOST=laptop, REMOTE_LOG=~/lineage/build.log)
LOG="${REMOTE_LOG:-${LOG:-$HOME/lineage/build.log}}"

unit_start() {   # lineage-build-20261118-152037.scope -> epoch seconds
  local ts=${1#lineage-build-}; ts=${ts%.scope}
  date -d "${ts:0:8} ${ts:9:2}:${ts:11:2}:${ts:13:2}" +%s 2>/dev/null || echo 0
}

latest_unit() {  # the newest build unit that is NOT running (a finished OK one is gone; a failed one stays)
  systemctl --user list-units 'lineage-build-*' --all --no-legend --plain 2>/dev/null | awk '$3 != "active" {print $1}' | sort | tail -1
}

outcome() {      # outcome UNIT|latest|"" -> prints one @@END line (nothing if no build is known)
  local u=$1 now start=0 st="" res="" last logm boot since j who peak kind="" text="" ref
  [ "$u" = latest ] && u=$(latest_unit)
  now=$(date +%s)
  boot=$(date -d "$(uptime -s)" +%s 2>/dev/null || echo 0)
  logm=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
  last=$(grep -a '^#### ' "$LOG" 2>/dev/null | tail -1)
  if [ -n "$u" ]; then
    start=$(unit_start "$u")
    st=$(systemctl --user show -p ActiveState --value "$u" 2>/dev/null)
    res=$(systemctl --user show -p Result --value "$u" 2>/dev/null)
    since=$(date -d "@$start" '+%Y-%m-%d %H:%M:%S')
  fi
  if [ "$st" = failed ]; then
    if [ "$res" = oom-kill ]; then
      j=$(journalctl -b 0 --since "$since" --no-pager 2>/dev/null)
      if printf '%s\n' "$j" | grep -F "$u" | grep -qi oomd; then
        who="killed by systemd-oomd because of memory pressure (the build was using all its RAM and swap)"
      else
        who="killed by the kernel out-of-memory killer (the build reached its memory cap)"
      fi
      peak=$(printf '%s\n' "$j" | grep -F "$u" | grep -o 'Consumed.*' | tail -1)
      kind=OOM; text="BUILD KILLED, OUT OF MEMORY: $who. $peak"
    else
      kind=STOPPED; text="BUILD STOPPED: its systemd unit failed (result: ${res:-unknown})"
    fi
  elif [ -n "$last" ] && [ "$logm" -ge "$start" ] && { [ "$start" -gt 0 ] || [ "$boot" -le "$logm" ]; }; then
    # the log was written after this build started (or no unit is known) and ends with a result line
    case "$last" in
      *"completed successfully"*) kind=OK; text="BUILD FINISHED: $(printf '%s' "${last#\#\#\#\# }" | sed 's/ *#\{4\}$//')" ;;
      *)                          kind=FAILED; text="BUILD FAILED: $(printf '%s' "${last#\#\#\#\# }" | sed 's/ *#\{4\}$//')" ;;
    esac
  elif ref=$([ "$start" -gt 0 ] && echo "$start" || echo "$logm"); [ "$ref" -gt 0 ] && [ "$boot" -gt "$ref" ]; then
    # the machine booted after this build started (or after the log was last written)
    kind=REBOOT; text="THE MACHINE RESTARTED at $(date -d "@$boot" +%H:%M) (power loss, crash or shutdown) and the build did not finish"
  elif [ -n "$u" ] || [ -s "$LOG" ]; then
    kind=STOPPED; text="BUILD STOPPED without a result: it was killed or stopped by hand (no failure was recorded)"
  fi
  [ -n "$kind" ] && echo "@@END ${u:--} $kind $now $text"
}

status() {
  local prev="" first=1 u start
  while :; do
    u=$(systemctl --user list-units 'lineage-build-*' --state=running --no-legend --plain 2>/dev/null | awk '{print $1}' | head -1)
    if [ -n "$u" ]; then
      prev=$u; first=0
      start=$(unit_start "$u")
    else
      start=0
      if [ -n "$prev" ]; then outcome "$prev"; prev=""; first=0
      elif [ "$first" = 1 ]; then outcome latest; first=0; fi
    fi
    set -- $(ps -C soong_build -o rss=,etimes=,cputimes= 2>/dev/null | head -1)
    echo "@@STATUS ${u:--} $start $(date +%s) $(( ${1:-0} / 1024 )) ${2:-0} ${3:-0}"
    sleep 2
  done
}

if [ "$1" = outcome ]; then outcome "${2-latest}"; exit 0; fi
status &
exec tail -n 60 -F "$LOG" 2>/dev/null
