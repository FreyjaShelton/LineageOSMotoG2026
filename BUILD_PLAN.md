# Build Plan

How we get from "locked phone and no tree" to a LineageOS build for the Moto g 2026 (`utah`, XT2613-1). Status of each phase is tracked here. See [README.md](README.md) for the device facts.

## Where we build

**Decision (2026-11-15): build on the user's Linux laptop** (about 900 GB free), not on this Windows PC. Native Linux avoids WSL2 entirely.

Still to confirm about the laptop: distro and version, RAM (16 GB or more is wanted), CPU cores, whether it runs on mains power for long builds, and whether it has a fast SSD.

This Windows PC stays useful for flashing and recovery: `adb`, `fastboot` and Motorola Software Fix already work here, and it holds the stock firmware. It is a fallback build machine too (32 GB RAM, i7-9700K, 545 GB free on D:, WSL2 installed but no distro).

## Phases

### Phase 0: Prepare the build machine (Linux laptop)
- [ ] Check the laptop's specs and distro (see above).
- [ ] Install the LineageOS build dependencies and `repo`, per the LineageOS build guides on the wiki.
- [ ] Install `git-lfs` (the `nevada` vendor repo uses it).
- [ ] Set up `adb`/`fastboot` and udev rules on the laptop if we flash from it. Flashing from this Windows PC works as well.
- [ ] Copy the stock firmware (`D:\LineageOS\firmware` on this PC, 6.8 GB) to the laptop, for blob extraction and comparison.

### Phase 1: Back up the phone's stock firmware
Done before any unlock, because we need it for recovery and for extracting blobs.
- [ ] Download the official stock firmware for **XT2613-1 (RETUS)**, build `W1WNS36.18-114-3-2-1-1-1` (matches the phone's fingerprint). Source to be confirmed.
- [ ] Back up everything personal on the phone. Unlocking wipes it.

### Phase 2: Prove the community tree builds (as-is, for `nevada`)
Goal: learn the build system and see how far the existing work goes before changing anything.
- [ ] `repo init` for LineageOS 23 and `repo sync` (large download).
- [ ] Clone the `nevada` device tree, vendor repo and kernel repo from the README into the paths it documents.
- [ ] Build (`lunch lineage_nevada-bp2a-userdebug`, `mka bacon`).
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
