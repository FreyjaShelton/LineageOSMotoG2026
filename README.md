# LineageOSMotoG2026

A project to build a custom [LineageOS](https://lineageos.org/) ROM for the **Motorola Moto g (2026)**.

> **Working name: Chrysalis.** This is what we call the OS while it is being built. It is a working name, not a final one.

This repo holds the notes, scripts, and configuration we use along the way. It is not a copy of the LineageOS source (that is hundreds of GB and is fetched with the `repo` tool, outside this repo).

## Goal

Produce a flashable LineageOS build that boots and works on a Moto g 2026, and keep the steps documented and repeatable so we can rebuild it later.

> **Newer status (2026-11-17): the build, the unlock and the flashing all happened since this note was written. The current "where we left off" is at the top of [BUILD_PLAN.md](BUILD_PLAN.md). The section below is the 2026-11-15 handoff and is kept as history.**

## Where we left off (2026-11-15)

**Handoff note for the next session** (we are moving the build work to a Linux laptop with about 900 GB free). Read [BUILD_PLAN.md](BUILD_PLAN.md) and [LESSONS.md](LESSONS.md) too.

Done so far:

- Identified the phone over `adb`: XT2613-1, codename `utah`, MT6835, Android 16, bootloader **locked** (details below).
- Found a community LineageOS 23 device tree for the sibling phone `nevada`; no `utah` tree exists.
- Downloaded the official stock firmware through Motorola Software Fix **without flashing** (build `W1WNS36.18-114-3-2-1-1-1`, 6.8 GB, kept on the Windows PC in `D:\LineageOS\firmware`, not in git).
- Freed disk space on the Windows PC and decided to build on the Linux laptop instead.
- Nothing has been flashed, unlocked or built. The OEM unlocking toggle on the phone is available, but we have not requested an unlock code.

Next steps, in order:

1. On the laptop: check distro, RAM, CPU, disk type (`cat /etc/os-release`, `free -h`, `nproc`, `lsblk -d -o NAME,SIZE,ROTA,MODEL`).
2. Install the LineageOS build dependencies, `repo` and `git-lfs`.
3. Copy the stock firmware from the Windows PC to the laptop (USB drive or network).
4. Phase 2 of the build plan: sync LineageOS 23, clone the `nevada` device tree, vendor and kernel repos, and try the build as-is.
5. Compare the firmware against the `nevada` tree and adapt it into a `utah` tree (phase 3).
6. Only then check Motorola's bootloader unlock portal and flash (phase 4).

Open questions:

- Will Motorola's unlock portal accept this US carrier variant (XT2613-1, `retus`)?
- Is the downloaded firmware (product `nevada_g_sys`) really the right restore image for our `nevada_g_sysu` / `utah` phone? Not confirmed.
- Does the `nevada` tree boot at all, and how different is `utah` (display, camera, sensors, storage)?
- Which LineageOS branch does upstream support for Android 16 right now?
- Laptop specs: enough RAM and a fast enough disk for the build?

Rules to follow: do not unlock or flash until recovery is sorted, never flash `nevada` (XT2615) files onto this phone, and do not ask to commit changes unless asked (see `LESSONS.md`).

## Status

Early planning. Nothing has been built yet.

### Device facts so far

Read directly from our phone over `adb` (read-only) on 2026-11-15:

| Item | Value |
|------|-------|
| Model | moto g - 2026, **XT2613-1** (US, carrier `retus`) |
| Device codename | **`utah`** (product `nevada_g_sysu`, board `nevada`) |
| SoC | MediaTek **MT6835** (Dimensity 6300), platform `mt6835`, arm64 |
| Kernel | Linux **5.15** (`android13` GKI branch) |
| Software | Android **16** (SDK 36), security patch 2026-09-01 |
| Vendor image | built from **Android 13** (`nevada_g_vext`), Treble enabled |
| Partitions | A/B with virtual A/B and dynamic partitions; current slot `_b` |
| Bootloader | **locked** (`flash.locked=1`, verified boot `green`) |
| RAM | about 4 GB (MemTotal 3.7 GB) |

Notes:

- Android 16 on top of a vendor image and 5.15 kernel from Android 13 is normal for a newly launched Treble phone, and it matters for porting: the device tree and blobs must match that older vendor side.
- The XT2613-1 is reported on XDA to be a US carrier variant (MetroPCS). See [this XDA bootloader thread](https://xdaforums.com/t/motorola-moto-g-2026-xt2613-1-metropcs-bootloader-unlock.4789459/).

### Existing community work (found 2026-11-15)

No `utah` tree exists, but our phone shares its platform with a sibling device, **`nevada`** (Moto G Play 2026, XT2615-1, same MT6835 SoC, same board name `nevada`, same stock build line `W1WNS36.18-114`). Both phones report product `nevada_g_sysu`.

- [crabcakes97/android_device_motorola_nevada_lineage](https://github.com/crabcakes97/android_device_motorola_nevada_lineage): LineageOS 23 / Android 16 device tree. Last commits (Sept 2026) mention a "green bacon build", meaning it compiles. We have **not** confirmed it boots or works on any phone.
  - Companion repos: `android_vendor_motorola_nevada` (blobs, uses Git LFS) and `android_device_motorola_nevada-kernel` (prebuilt stock kernel).
  - Kernel source it points to: [MotorolaMobilityLLC/kernel-mtk](https://github.com/MotorolaMobilityLLC/kernel-mtk), branch `android-16-release-w1wn36.18-114`.
- [Lg-PWNd/android_device_motorola_nevada](https://github.com/Lg-PWNd/android_device_motorola_nevada): TWRP recovery tree.
- XDA: [unofficial LineageOS thread for the G Play 2026](https://xdaforums.com/t/unofficial-lineage-os-lineage-recovery-g-play-2026.4801191/), [TWRP/OrangeFox for G Play / G 2026](https://xdaforums.com/t/recovery-twrp-orangefox-moto-g-play-moto-g-2026.4799348/).
- A forum user reports a LineageOS 23.2 GSI working with T-Mobile calling on this phone ([/e/OS forum](https://community.e.foundation/t/note-to-colors-about-using-the-gsi-16-on-a-moto-g-2026/84777)), unverified by us.

Likely path: adapt the `nevada` tree to `utah` (differences expected in display, camera, storage and sensors; our stock firmware is the XT2613-1 build) instead of writing a tree from nothing. This needs a build machine and our own stock firmware dump to compare.

### Open questions

- [x] **Exact variant and codename.** XT2613-1, codename `utah`.
- [ ] **Is the device already supported?** Searches found no LineageOS device page and no device tree for `utah` or `nevada`, but that is not conclusive. Check the [LineageOS device list](https://wiki.lineageos.org/devices/) and search XDA/GitHub directly. If there is no tree, we are porting from scratch.
- [ ] **Can the bootloader be unlocked?** Required for flashing. The phone is currently locked, but the **OEM unlocking** toggle in Developer options is available (a good sign). Next step is to request an unlock code from Motorola's unlock portal. Unlocking wipes the phone and may void the warranty, so back up first. Not done yet.
- [ ] **Kernel source.** Motorola publishes kernel sources for released devices; we need the one for `utah`/`nevada`.
- [ ] **Which LineageOS version to target.** Android 16 corresponds to LineageOS 23.x. Check what upstream currently supports.

## How a LineageOS build works (high level)

Based on the [LineageOS contributing docs](https://wiki.lineageos.org/contributing) and the per-device build guides on the wiki.

1. **Prepare a build machine.** The Android build system needs Linux. On this Windows PC that means WSL2 (or a Linux box/VM). Expect to need roughly 16 GB+ RAM and several hundred GB of free disk, and builds take hours.
2. **Install the build dependencies** and the `repo` tool (Google's multi-git manager).
3. **Fetch the LineageOS source** with `repo init` / `repo sync` (a very large download).
4. **Add the device-specific pieces** for the Moto g 2026:
   - a *device tree* (hardware configuration),
   - a *kernel* source,
   - *vendor blobs* (proprietary files, typically extracted from the phone or a stock firmware image).
5. **Build** (`breakfast <codename>` then `brunch <codename>`), producing a flashable zip and a recovery image.
6. **Flash** to the phone: unlock the bootloader, flash the LineageOS recovery, then sideload the zip.
7. **Test and iterate** on whatever does not work (camera, modem, Wi-Fi, etc. are the usual trouble spots).

If the device has no existing device tree, step 4 is the hard part. It is real porting work and a much bigger project than a plain build.

## Repo layout

| File | Purpose |
|------|---------|
| `README.md` | This overview |
| `BUILD_PLAN.md` | Phased build plan, build machine check and risks |
| `LESSONS.md` | Working rules and lessons learned for this project |

More will be added as the project grows.

## Recovery and stock firmware

Our phone's exact identity, needed to pick the right firmware:

- Model **XT2613-1**, codename `utah`, product `nevada_g_sysu`, channel `retus` (US)
- Current build: `W1WNS36.18-114-3-2-1-1-1` (full fingerprint in the device facts above)

Findings so far (2026-11-15):

- **The community firmware mirror has no `utah` folder.** The [lolinet mirror](https://mirrors.lolinet.com/firmware/lenomola/2026/) lists a `nevada` folder, whose only US (RETUS) file is `XT2615-1_NEVADA_RETUS_16_W1WNS36.18-114-1_...xml.zip` (about 5.5 GB). That is the **Moto G Play 2026 (XT2615-1)**, a different phone. **Never flash it to our phone.** It is only useful later for comparing against the `nevada` device tree.
- **Third-party firmware sites** (NeedROM, motostockrom and similar) list XT2613-1 builds but are unofficial, often have ad walls, and offer no checksums. The RETUS build they list is `-114-1`, not our exact build. Avoid them for recovery.
- **Official recovery tool: Motorola Software Fix** (formerly Rescue and Smart Assistant / LMSA), Windows only.
  - Page: [Download Software Fix (PC only)](https://en-us.support.motorola.com/app/answers/detail/a_id/158726/~/download-rescue-&-smart-assistant-(pc-only)). The older `support.motorola.com/us/en/solution/MS126499` link is dead.
  - Installer linked there: `https://download.lenovo.com/lsa/Releases/Rescue_and_Smart_Assistant_v6.2.2.4_prod_setup.exe` (143.8 MB, file dated September 2022, so the version may be old). **Not downloaded or installed yet.**
  - It detects the connected phone and **reflashes it, which wipes it**. Use it to recover from a bad flash, not casually.
  - It does keep the downloaded firmware (unzipped) in `C:\ProgramData\RSA\Download\RomFiles`, so we could copy it out.
- **Stock firmware downloaded (2026-11-15)** through Software Fix, **without flashing**. Software Fix stores it unzipped at `C:\ProgramData\RSA\Download\RomFiles\`, and we copied it to `D:\LineageOS\firmware` (58 files, 6.8 GB, plus `Nevada_Fastboot_Flashtool.zip`). Outside this repo on purpose.
  - Package: `NEVADA_G_SYS_W1WNS36.18-114-3-2-1-1-1_subsidy-DEFAULT_regulatory-DEFAULT_cid50_CFC.xml.zip`, Android 16, modem `MT6835N_NR17.RC.MP.V18.6.6.P144.02.348.01R`. Motorola's server chose it for our connected phone automatically.
  - **Matches the phone:** the build ID and bootloader string (`MBM-3.1-nevada_g_vext-390596-W1WNS36.18-114-3-2-1-1-1-bb91ee`) are identical to what `adb` read from the phone.
  - **One mismatch to understand:** the package's product is `nevada_g_sys` (device `nevada`), while our phone reports `nevada_g_sysu` (device `utah`). Probably one package serves both, but we have **not** confirmed it. Do not flash it by hand; if recovery is ever needed, use Software Fix, which picks the image for the connected phone itself.
  - Contents include `flashfile.xml`, `super.img_sparsechunk.*`, `boot`-related images, `lk.img`, `preloader.img`, `vbmeta*.img`. The `super` image holds system, vendor and product, which is where blobs come from later.
  - No checksum was provided (`MD5` field empty), so integrity is unverified beyond the tool's own unzip success.

Tools on this PC: Google platform-tools (`adb`, `fastboot`) in `%USERPROFILE%\platform-tools-extract\platform-tools`. Read-only `adb` commands only so far.

## Safety notes

- Back up everything on the phone first. Unlocking the bootloader wipes it.
- Do not unlock or flash anything until we have a working way to restore stock firmware for this exact phone (see above).
- Only flash builds made for your exact device and variant. `nevada` (XT2615) files are not for this phone.
