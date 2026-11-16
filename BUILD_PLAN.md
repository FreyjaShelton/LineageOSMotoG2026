# Build Plan

How we get from "locked phone and no tree" to a LineageOS build for the Moto g 2026 (`utah`, XT2613-1). Status of each phase is tracked here. See [README.md](README.md) for the device facts.

## Where we build

**Decision (2026-11-15): build on the user's Linux laptop** (about 900 GB free), not on this Windows PC. Native Linux avoids WSL2 entirely.

Laptop specs (checked 2026-11-15):

| Item | Value |
|------|-------|
| OS | Ubuntu 26.04.1 LTS (`resolute`) |
| CPU | AMD Ryzen AI 9 365, 10 cores / 20 threads |
| RAM | 29 GiB usable, plus 8 GiB swap file (to grow to 40 GiB, see "Memory" below) |
| Disk | 1 TB NVMe SSD (WD SN560), 839 GB free on `/` |
| Tools installed | build dependencies, `repo` (launcher 2.54), `git-lfs` 3.7.1, `adb`/`fastboot` 34.0.5, `ccache` (all from Ubuntu's apt repos, 2026-11-15) |

Good enough for the build, with more swap (see "Memory" below). Ubuntu 26.04 is newer than the releases the LineageOS guides list, so some dependency package names may differ. Still to confirm: keep it on mains power during long builds.

### Memory (lesson from 2026-11-15)

At 20:01 on 2026-11-15 the kernel's out-of-memory killer stopped a build. `soong_build`, the analysis step that runs before any compiling, had reached **about 28 GB of RAM** (`anon-rss:28468104kB` in `journalctl -k`). With 29 GiB of RAM and 8 GiB of swap, nothing was left. Because the build had been started from a Claude session, systemd counted it as part of the Claude app's process group (`app-com.anthropic.Claude-*.scope`), so **the Claude app was killed too**.

Rules for future builds:
- **Swap: 40 GiB.** [scripts/grow-swap.sh](scripts/grow-swap.sh) resizes `/swap.img` in place (`sudo scripts/grow-swap.sh`, or `SIZE=48G` for more). `/etc/fstab` already points at `/swap.img`, so the new size survives reboots. Check with `swapon --show`. Status: script written, **not run yet** (it needs `sudo`).
- **Run every build in its own systemd scope**, so that running out of memory kills only the build, never the terminal or the Claude app. [scripts/build-nevada.sh](scripts/build-nevada.sh) now does this itself: it re-runs inside `systemd-run --user --scope` as a unit named `lineage-build-<timestamp>`, capped at `MemoryMax=26G` and `MemorySwapMax=40G` (change with `MEM_MAX=` / `SWAP_MAX=`, skip with `NO_SCOPE=1`). Tested 2026-11-15: the scope sits outside the Claude app's group, and the caps apply. Any build run by hand with `m`/`mka` should be wrapped the same way.
- Close browsers and other heavy apps while `soong_build` runs (the first few minutes). Lowering `-j` does not help with this step, because `soong_build` is a single process. It only helps during the compile that follows.
- If a build dies with no error in `~/lineage/build.log`, check `journalctl -k | grep -i "killed process"` first.

This Windows PC stays useful for flashing and recovery: `adb`, `fastboot` and Motorola Software Fix already work here, and it holds the stock firmware. It is a fallback build machine too (32 GB RAM, i7-9700K, 545 GB free on D:, WSL2 installed but no distro).

## Phases

### Phase 0: Prepare the build machine (Linux laptop)
- [x] Check the laptop's specs and distro (see above).
- [x] Install the LineageOS build dependencies and `repo`, per the LineageOS build guides on the wiki.
  - Ubuntu 26.04 name changes: `liblz4-tool` → `lz4`, `lib32ncurses5-dev` → `lib32ncurses-dev`, `libncurses5` dropped (not needed for LineageOS 23). No system Java installed; LineageOS 23 ships its own JDK.
  - Install command used: `sudo apt install bc bison build-essential ccache curl flex g++-multilib gcc-multilib git git-lfs gnupg gperf imagemagick lib32readline-dev lib32z1-dev libelf-dev lz4 libsdl1.2-dev libssl-dev libxml2-utils lzop pngcrush rsync schedtool squashfs-tools xsltproc zip zlib1g-dev lib32ncurses-dev libncurses-dev python-is-python3 repo adb fastboot android-sdk-platform-tools-common`
- [x] Install `git-lfs` (the `nevada` vendor repo uses it) and run `git lfs install`.
- [x] Set `ccache` limit to 50 GB. At build time, also `export USE_CCACHE=1` and `export CCACHE_EXEC=/usr/bin/ccache`.
- [x] `adb`/`fastboot` installed with Android udev rules (`51-android.rules`); user is in `plugdev`. Not yet tested with the phone plugged into the laptop. Flashing from the Windows PC works as well.
- [x] Copy the stock firmware (`D:\LineageOS\firmware` on the Windows PC) to the laptop, for blob extraction and comparison.
  - Done 2026-11-15 by USB drive. On the laptop: `~/lineage/firmware/` (59 files, 6.9 GB), outside this repo.
  - SHA-256 list made on Windows before copying (`Get-FileHash`), saved as `~/lineage/firmware.sha256`. All 59 files match (`cd ~/lineage/firmware && sha256sum -c ../firmware.sha256`). This proves the copy matches the Windows PC, not that Motorola's download was intact (no official checksum exists).
  - The unzipped firmware folder is `NEVADA_G_SYS_W1WNS36.18_114_3_2_1_1_1_subsidy_DEFAULT_regulatory_DEFAULT_cid50_CFC.xml/`, next to `Nevada_Fastboot_Flashtool.zip`.

### Phase 1: Back up the phone's stock firmware
Done before any unlock, because we need it for recovery and for extracting blobs.
- [ ] Download the official stock firmware for **XT2613-1 (RETUS)**, build `W1WNS36.18-114-3-2-1-1-1` (matches the phone's fingerprint). Source to be confirmed.
- [ ] Back up everything personal on the phone. Unlocking wipes it.

### Phase 2: Prove the community tree builds (as-is, for `nevada`)
Goal: learn the build system and see how far the existing work goes before changing anything.
- [x] `repo init` for LineageOS 23 and `repo sync` (large download). Started 2026-11-15 in `~/lineage/android`; log in `~/lineage/sync.log`. **Finished successfully in 18.5 minutes**: 1,144 projects, 117 GB on disk, no errors. The 4 Git LFS blobs in `vendor/motorola/nevada` downloaded as real files (no pointer files left).
  - Lesson: piping `repo sync` through `tee` hides its progress bar, so it looks frozen. Watch `du -sh ~/lineage/android/.repo` instead.
  - Branch: **`lineage-23.0`**. The nevada README says to use `lunch ...-bp2a-...`, and only 23.0 has build ID `BP2A` (23.1 is `BP3A`, 23.2 is `BP4A`).
  - Init command: `repo init -u https://github.com/LineageOS/android.git -b lineage-23.0 --git-lfs --no-clone-bundle --depth=1`
  - Sync command: `repo sync -c -j8 --no-tags --no-clone-bundle --optimized-fetch` (re-run the same command to resume if interrupted).
  - Ubuntu's `repo` launcher (2.54) warns that 2.71 exists and cannot self-update. Harmless.
- [x] Clone the `nevada` device tree, vendor repo and kernel repo from the README into the paths it documents. Done through a local manifest, `~/lineage/android/.repo/local_manifests/nevada.xml`, so `repo sync` fetches them with the rest:
  - `device/motorola/nevada`, `vendor/motorola/nevada` (Git LFS), `device/motorola/nevada-kernel` from `crabcakes97`, branch `main`.
  - Dependencies the README names: `hardware/mediatek`, `device/mediatek/sepolicy_vndr`, `hardware/motorola` from LineageOS, branch `lineage-23.0`.
  - **`vendor/mediatek/ims` is a guess.** It is not in the LineageOS org and the README does not say which copy it used. We took `xiaomi-mediatek-devs/android_vendor_mediatek_ims`, branch `android-16`, which has the `ims.mk` that `device.mk` includes. If the build complains about IMS, revisit this first.
- [ ] Build (`lunch lineage_nevada-bp2a-userdebug`, `mka bacon`). First build started 2026-11-15 with [scripts/build-nevada.sh](scripts/build-nevada.sh) (turns on ccache, runs lunch and mka, logs to `~/lineage/build.log`). Result: **not building yet**, failing in Soong analysis (about 1 minute in). Findings:
  - **Fixed:** `fingerprint-gdx` could not see the module `com.motorola.hardware.biometric.fingerprint@1.0`, because the nevada `soong_namespace` did not import `hardware/motorola`. Added it to `imports`. Kept as [patches/device_motorola_nevada/0001-import-hardware-motorola-namespace.patch](patches/device_motorola_nevada/0001-import-hardware-motorola-namespace.patch); apply with `git apply` inside `device/motorola/nevada` after a fresh sync. This is a local change, not pushed upstream.
  - **Open:** the published vendor repo `vendor/motorola/nevada` lists 3 blobs in its `Android.bp`/makefiles that are not in the repo (checked by comparing every referenced `proprietary/...` path against the disk):
    - `proprietary/system_ext/lib64/libhidltcmd.so` (Soong's first error)
    - `proprietary/system/lib64/com.motorola.hardware.biometric.fingerprint-V1-ndk.so`
    - `proprietary/vendor/bin/hw/android.hardware.bluetooth@1.1-service-mediatek`
  - **Done (2026-11-15): extracted all 3 from our own firmware** into `vendor/motorola/nevada/proprietary/` (untracked local files; hashes in [patches/extracted-blobs.sha256](patches/extracted-blobs.sha256)). Method, no `sudo` needed: `simg2img` (prebuilt in `prebuilts/kernel-build-tools/linux-x86/bin`) joins `super.img_sparsechunk.*` into a 9.3 GB raw image in `~/lineage/work/`; a small Python script split it by the LP partition table into `product_a`, `system_a`, `system_dlkm_a`, `system_ext_a`, `vendor_a`, `vendor_dlkm_a` (all EROFS, no `odm`); `fsck.erofs --extract=DIR --no-preserve` unpacked them into `~/lineage/work/x/`. Note the `system` image nests files under `system/system/`, so tree path `system/lib64/X` is `x/system/system/lib64/X`.
  - (Earlier idea, superseded:) pull them from a firmware dump (`extract-files.py`, or by hand from the `super` image). This is the same job as Phase 3's blob extraction. Tools missing on the laptop for unpacking `super`: `simg2img`, `lpunpack`, `fsck.erofs`/`dump.erofs` (check which filesystem the image uses).
  - Caveat: our firmware is XT2613-1 build `114-3-2-1-1-1`, the tree was made from XT2615-1 `114-1`, so blobs taken from ours may differ slightly from the ones the tree expects.
  - **2026-11-15 20:06, with 40 GiB swap and the scope: Soong analysis passed** (about 6 min; it peaked near 50 GB RAM+swap, so the extra swap was needed). Ninja then had 212,356 actions, but failed at step 43 with `ccache: error: Not a directory`: `~/.cache/ccache` (ccache's default cache dir) was an empty *file*. Replaced it with a directory; `ccache -s` and a test compile work. Build restarted 20:16.
  - **Attempt 3 (20:16–20:24): failed at 6% (step 14,351 of 212,324)** in `check_elf_files`: prebuilt `vendor.mediatek.hardware.pq_aidl-V1-ndk.so` needs `android.hardware.graphics.common-V3-ndk.so`, but `Android.bp` lists V6. Cause: the vendor repo's `Android.bp` was generated from *fixed-up* blobs, but the `.so` files it ships are the unfixed originals. `device/motorola/nevada/extract-files.py` has the matching `blob_fixups` (with comments explaining each). 5 blobs are affected: `libtpa`, `librilfusion`, `pq_aidl-V1-ndk`, `libcodec2_vpp_AIMEMC_plugin`, `libcodec2_vpp_AISR_plugin`. The `.rc` fixups and the other ELF fixups *were* applied.
    - **Fixed** with [scripts/apply-nevada-blob-fixups.sh](scripts/apply-nevada-blob-fixups.sh): the same patchelf edits as `extract-files.py`, run with extract-utils' default `patchelf-0_18`. It is safe to re-run, and it keeps the originals in `~/lineage/work/blob-orig/`. **Re-run it after any `repo sync` that resets the vendor repo.**
    - [scripts/check-vendor-needed.py](scripts/check-vendor-needed.py) compares every prebuilt's real `DT_NEEDED` with its `shared_libs`, so all such mismatches are found in seconds instead of one per rebuild. It knows about `stem` renames (`videotelephony@1.0_vendor`, `libprotobuf-cpp-lite-3.9.1-vendorcompat` are fine). Now reports 0. Run it before every build.
    - Build restarted 20:27 (attempt 4); `build-nevada.sh` now runs the blob check first and stops if it fails.
  - Watch builds with [scripts/build-progress.sh](scripts/build-progress.sh). Leave it running: it waits between builds and prints each build's result when it ends. It shows elapsed time, total CPU time of the build, RAM and swap of the build's scope, the Ninja step with its rate and a rough time left, and the latest log line. During Soong analysis there is no step count; rising CPU time is the sign it is working.
  - [scripts/build-live.sh](scripts/build-live.sh) (a launcher for [scripts/build-live.py](scripts/build-live.py)) is the second tab: a full-screen display with a progress bar, one summary line per Ninja step (tens per second, bottom-aligned), about 3x as many green streaks as before (one per ~30 screen cells), at speeds from 0.05 to 1.6 rows per frame (slow ones dim and short, fast ones bright and long), falling through the text (broken into pieces with gaps, mixed with digits and symbols that flicker as they fall; a streak's bright head replaces the text character it passes and its fading tail tints the text green), and failures/errors in red marked `>>>`. Time left is the average since the tab started, shown after the first minute. Redraws about 12 times a second (`FPS=`), `NO_ANIM=1` turns the streaks off, and piped output falls back to plain lines. It follows the log by name, so it survives build restarts. (Python, not awk: Ubuntu's `awk` is mawk, which has no time functions.)
  - **Speed (checked 2026-11-15 21:37):** the laptop is already maxed out (CPU 93% busy, load 40 on 20 threads, performance governor, on AC, 3.75 GHz average), so **a second build would only split the same threads** and double the memory use. Plan: let this first full build finish untouched. For later fix-and-retest builds: (1) let Ninja redo only what changed, (2) consider `WITH_DEXPREOPT=false` (skips the app pre-compile at the end; changing it makes Soong re-analyze, about 6 min and the 50 GB memory peak, so only worth it for several rebuilds in a row; the phone's first boot is slower), and (3) build only the target needed for the test (e.g. the boot image) instead of `bacon`. Close other heavy apps during builds.
  - Never edit a script while it is running (bash reads scripts as it goes, so the running copy can jump to the wrong line). Write a new file and `mv` it into place instead.
  - `TARGET=<target> scripts/build-nevada.sh` builds something smaller than `bacon`, e.g. to retry one failing module.
  - Output zips appear in `~/lineage/android/out/target/product/nevada/`.
- [ ] Record what works and what fails.

### Phase 3: Adapt the tree to `utah`
- [ ] Compare our stock firmware against the `nevada` firmware: display, camera, sensors, storage, partition sizes, device properties.
- [ ] Create `device/motorola/utah` from the `nevada` tree, with the differences found.
- [ ] Regenerate vendor blobs from our own firmware (`extract-files.py`).
- [ ] Build.

### Phase 4: Flash and test
- [ ] Request Motorola's bootloader unlock code and unlock (wipes the phone, may void warranty). Only after a build exists.
- [ ] Test the build on the phone with `fastboot boot` (a temporary boot, nothing written) where possible before flashing for real.
- [ ] Flash, then test: boot, touch, display, Wi-Fi, mobile data and calls, camera, fingerprint, audio, Bluetooth, GPS.
- [ ] Keep stock firmware ready to restore.

### Phase 5: Iterate and document
- [ ] Fix what is broken, one thing at a time, and record each fix.
- [ ] Decide whether to share the `utah` tree publicly.

## Risks to keep in mind

- **Bricking.** A bad flash can leave the phone unusable. A MediaTek phone can often be recovered with stock firmware, but we should not assume it. Test with `fastboot boot` first and keep the phone you depend on as a spare if possible.
- **Locked-down carrier model.** XT2613-1 is the US carrier variant (retus). Motorola's unlock portal may refuse it even though the OEM unlocking toggle is available. We find out when we request the code.
- **Calls and mobile data** on MediaTek phones depend on proprietary IMS pieces; they are the most common failure area.
- **The `nevada` tree is unproven.** It reportedly compiles, but we have no evidence it boots.
- **Android 16 vendor mismatch.** The phone's vendor side is Android 13 based, so the tree and blobs must match it.
