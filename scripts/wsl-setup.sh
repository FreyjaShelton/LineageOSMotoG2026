#!/usr/bin/env bash
# One-time setup of the WSL2 build machine (Ubuntu 24.04, distro "lineage" on D:).
# Run inside WSL as the normal user: bash scripts/wsl-setup.sh
# Installs the LineageOS build dependencies, repo, git-lfs, ccache (50 GB),
# and writes the git identity placeholders repo needs. adb/fastboot are NOT
# installed here: flashing is done from Windows.
set -euo pipefail

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  bc bison build-essential ccache curl flex g++-multilib gcc-multilib git git-lfs \
  gnupg gperf imagemagick lib32readline-dev lib32z1-dev libelf-dev lz4 libssl-dev \
  libxml2-utils lzop pngcrush rsync schedtool squashfs-tools xsltproc zip unzip \
  zlib1g-dev lib32ncurses-dev libncurses-dev python-is-python3 python3 repo \
  erofs-utils android-sdk-libsparse-utils

git lfs install
git config --global user.name  >/dev/null 2>&1 || git config --global user.name  "Freyja Shelton"
git config --global user.email >/dev/null 2>&1 || git config --global user.email "build@localhost"
git config --global color.ui false

mkdir -p "$HOME/lineage/android" "$HOME/lineage/release" "$HOME/lineage/work"
ccache -M 50G
grep -q USE_CCACHE "$HOME/.bashrc" || cat >> "$HOME/.bashrc" <<'EOF'
export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
EOF
repo --version | head -2
echo "wsl-setup done"
