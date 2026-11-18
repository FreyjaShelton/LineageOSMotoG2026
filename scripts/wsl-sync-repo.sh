#!/usr/bin/env bash
# Make an LF-only working copy of this repo inside WSL, at ~/LineageOSMotoG2026.
#
# Why: on Windows, git (core.autocrlf=true) checks text files out with CRLF line
# endings. Linux then fails on them ("env: 'bash\r': No such file"), and CRLF .rc
# and .mk files copied into the Android tree would break init and the build.
# So WSL builds must run from this copy, never from /mnt/c/... directly.
# Uncommitted edits are included (it copies the working tree, not git history).
# Re-run after editing anything in the repo on Windows. Safe to repeat.
#
# Usage (from Windows): wsl -d lineage -- bash /mnt/c/Users/freyj/LineageOSMotoG2026/scripts/wsl-sync-repo.sh
set -euo pipefail
SRC="${SRC:-/mnt/c/Users/freyj/LineageOSMotoG2026}"
DST="${DST:-$HOME/LineageOSMotoG2026}"

mkdir -p "$DST"
rsync -a --delete --exclude=.git "$SRC"/ "$DST"/
# Strip CRs from text files only (binaries such as bootanimation.zip stay untouched).
find "$DST" -type f \( -name '*.sh' -o -name '*.py' -o -name '*.mk' -o -name '*.rc' \
  -o -name '*.bp' -o -name '*.patch' -o -name '*.xml' -o -name '*.md' -o -name '*.txt' \
  -o -name '*.prop' -o -name '*.sha256' -o -name '*.json' -o -name '*.cfg' -o -name '*.conf' \) \
  -print0 | xargs -0 sed -i 's/\r$//'
chmod +x "$DST"/scripts/*.sh "$DST"/scripts/*.py 2>/dev/null || true
echo "LF copy of the repo is at $DST ($(find "$DST" -type f | wc -l) files)"
