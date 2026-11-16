#!/usr/bin/env bash
# Grow the laptop's swap file so soong_build (about 28 GB at peak) cannot
# exhaust RAM. Resizes the existing /swap.img in place, so /etc/fstab needs
# no change and the new size survives reboots.
# Usage: sudo scripts/grow-swap.sh          (default 40G)
#        sudo SIZE=48G scripts/grow-swap.sh
set -euo pipefail

SWAP="${SWAP:-/swap.img}"
SIZE="${SIZE:-40G}"

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo." >&2
  exit 1
fi

grep -q "^$SWAP[[:space:]]" /etc/fstab || {
  echo "$SWAP is not in /etc/fstab; refusing to guess." >&2
  exit 1
}

echo "== before"; swapon --show; free -h

swapoff "$SWAP"            # moves its pages back into RAM (needs free RAM)
rm -f "$SWAP"
fallocate -l "$SIZE" "$SWAP"
chmod 600 "$SWAP"
mkswap "$SWAP"
swapon "$SWAP"

echo "== after"; swapon --show; free -h
