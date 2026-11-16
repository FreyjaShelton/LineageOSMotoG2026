#!/usr/bin/env bash
# Live status for build-nevada.sh, one short line every INTERVAL seconds.
# Keeps running across builds: waits between them and prints each build's
# result when it ends.
#
#   20:41  0h12m   18%  35210/197761  ~1h05m left  | clang++ foo.cpp
#
# Memory is shown only when it is worth a look (RAM over 22G or any swap use).
# During Soong analysis there is no step count, so it shows CPU time instead
# (rising = working).
#
# Usage: scripts/build-progress.sh      (Ctrl-C stops watching; the build keeps going)
LOG="${LOG:-$HOME/lineage/build.log}"
INTERVAL="${INTERVAL:-10}"
hms() { printf '%dh%02dm' $(($1 / 3600)) $(($1 % 3600 / 60)); }
lastlines() { tail -c 6000 "$LOG" 2>/dev/null | tr '\r' '\n' | grep -v '^$' | tail -"$1"; }

prev_unit="" prev_step="" prev_t="" rate10=""
while true; do
  unit=$(systemctl --user list-units 'lineage-build-*' --no-legend --plain 2>/dev/null | awk '{print $1}' | tail -1)

  if [[ -z "$unit" ]]; then
    if [[ -n "$prev_unit" ]]; then
      echo "$(date +%H:%M)  build ended. Last log lines:"
      lastlines 4 | cut -c1-160 | sed 's/^/    /'
      echo "$(date +%H:%M)  waiting for the next build..."
      prev_unit="" prev_step="" rate10=""
    fi
    sleep "$INTERVAL"
    continue
  fi
  if [[ "$unit" != "$prev_unit" ]]; then
    echo "$(date +%H:%M)  build started ($unit)"
    prev_unit=$unit prev_step="" rate10=""
  fi

  now=$(date +%s)
  start=$(systemctl --user show "$unit" -p ActiveEnterTimestamp --value)
  elapsed=$(( now - $(date -d "$start" +%s 2>/dev/null || echo "$now") ))
  cg="/sys/fs/cgroup$(systemctl --user show "$unit" -p ControlGroup --value)"
  mem=$(( $(systemctl --user show "$unit" -p MemoryCurrent --value | grep -E '^[0-9]+$' || echo 0) / 1073741824 ))
  swap=$(( $(systemctl --user show "$unit" -p MemorySwapCurrent --value | grep -E '^[0-9]+$' || echo 0) / 1073741824 ))
  warn=""
  (( mem > 22 || swap > 0 )) && warn="   mem ${mem}G swap ${swap}G"

  # Ninja progress: "[ 12% 1234/98765] ..."
  pct="" step="" total="" eta=""
  line=$(lastlines 50 | grep -oE '^\[ *[0-9]+% [0-9]+/[0-9]+' | tail -1)
  if [[ -n "$line" ]]; then
    pct=$(grep -oE '[0-9]+%' <<<"$line")
    step=$(grep -oE '[0-9]+/' <<<"$line" | tr -d /)
    total=$(grep -oE '/[0-9]+' <<<"$line" | tr -d /)
    if [[ -n "$prev_step" && $now -gt $prev_t && $step -ge $prev_step ]]; then
      r=$(( (step - prev_step) * 10 / (now - prev_t) ))
      rate10=$(( ${rate10:-$r} * 7 / 10 + r * 3 / 10 ))   # smoothed
      (( rate10 > 0 )) && eta="~$(hms $(( (total - step) * 10 / rate10 ))) left"
    fi
    prev_step=$step prev_t=$now
    prog=$(printf '%4s  %6s/%-6s  %-13s' "$pct" "$step" "$total" "$eta")
  else
    usec=$(awk '/^usage_usec/ {print $2}' "$cg/cpu.stat" 2>/dev/null)
    prog=$(printf 'analysis (cpu %s)' "$([[ -n "$usec" ]] && hms $((usec / 1000000)) || echo -)")
  fi
  last=$(lastlines 1 | sed -E 's/^\[ *[0-9]+% [0-9]+\/[0-9]+\] //; s#^//[^ ]*:##' | cut -c1-55)

  printf '%s  %s  %s%s  | %s\n' "$(date +%H:%M)" "$(hms "$elapsed")" "$prog" "$warn" "$last"
  sleep "$INTERVAL"
done
