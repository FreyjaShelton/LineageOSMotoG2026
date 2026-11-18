# Lessons

Working rules and lessons learned for this project. Add to this file as new lessons come up.

## Start of every new chat: read these files first

When a new chat is told to "read the lessons file", read all of these before doing anything else, then continue from the latest status:

1. `LESSONS.md` (this file): working rules.
2. `README.md`: device facts (Moto g 2026, `utah`, XT2613-1), the `nevada` community tree, firmware and recovery notes.
3. `BUILD_PLAN.md`: where we build (the Linux laptop), the memory and crash rules, and each phase's status. The newest status is the section "Where we left off" at the very top of the file (read it first); the phase sections below it are the history.
4. `scripts/`: skim the header comment of each script (`build-nevada.sh` is the main entry point; `build-live.sh` is the watcher for builds, and `build-live.sh sync` for `repo sync`).

Then look outside the repo for live state: `tail ~/lineage/build.log`, `systemctl --user list-units 'lineage-build-*'` (is a build running?), and `journalctl --list-boots` (did the laptop crash or reboot since the last notes?).

**Why:** the user only wants to say "read the lessons file" at the start of a chat, and not list the other files each time.

## Use Sonnet 5.5 by default

This project's chats should run on Sonnet 5.5 (`claude-sonnet-5-5`), not Opus. A chat cannot switch its own model. If a new chat finds it is running on another model, say so at the start, so the user can pick Sonnet in the app's model menu. To make Sonnet the default for new chats, set `"model": "claude-sonnet-5-5"` in `~/.claude/settings.json`.

**Why:** the user's choice. Sonnet is enough for this work.

## Don't ask to commit changes unless asked

Do not offer or ask to commit (or push) changes. Make the edits and leave them in the working tree. Only run git commit/push when the user explicitly asks for it.

**Why:** The user decides when work is ready to be committed. Prompting for it every time is noise.

## Progress displays: always use build-live

When asked to show progress for a build or a `repo sync`, run `scripts/build-live.sh` (add `sync` for a `repo sync`; it also switches on by itself when only a sync is running) in a terminal tab. Do not write new progress scripts. If `build-live.py` cannot show something, extend it instead.

**Why:** the user wants one progress display, not several.

## Whenever a build is running, its progress display must be open

Every time a build (or a `repo sync`) is started, in the same step open `build-live` in a terminal tab (run_in_terminal, with the title naming the build, e.g. "Laptop build 5"), without being asked, so the user can watch it. For a build on the laptop, run `python -I scripts\build-live.py remote` from the PC's repo folder; locally `scripts\build-live.sh` (`sync` for a sync). A restarted build needs its display checked again: look with `list_terminal_tabs` that a tab for it exists and is still running, and open a new one if it is gone. Only then say "it is in the tab ...": never name a tab without having checked it is there.

`build-live` also reports how a build ENDED (finished, failed, killed for memory by systemd-oomd or by the kernel's cap, machine restarted, stopped without a result) in the header and a red/green box, and says "no contact with the laptop" when the ssh link drops; it comes from `build-live-feed.sh` (`outcome`). If a build ends in some way the display does not name, extend that script, do not explain it from memory.

**Why:** the user wants to see the progress of every build themselves. On 2026-11-18 several rebuilds ran with no display open, while I told the user the progress was in a tab that no longer existed.

## Getting a log out of a phone that will not boot

Use the logger that runs on the phone and writes into `/metadata/dbg` every 20 s (`trees/device_motorola_utah/debug/`, built in with `UTAH_DEBUG_PANIC=1`). `/metadata` is unencrypted and our recovery mounts it, so the log survives any restart and a forced power-off; read `dbg` and `dbg.prev` (the previous boot) after getting to recovery. Do not go back to panic timers or to holding a key through a restart: they depend on exact timing and cost hours on 2026-11-18. Each boot moves `dbg` to `dbg.prev` and deletes the older `dbg.prev`, so read the logs before letting the phone restart again.

**Why:** it was the first method that gave real evidence (the composer crash loop, the 32-bit zygote kill loop, the audio effects crash), after many rounds of blind tests.

## Check a build on the build machine before it goes on the phone

After every build, before flashing: run `scripts/make-release.sh <name>` (logger present, boot image headers, and that `vendor.img` is stock's byte for byte), and fetch it with `scripts/fetch-release.ps1`. If the vendor is ever built again from blobs, also run `scripts/check-vendor-libs.sh` and `python3 -I scripts/check-vendor-symbols.py`. A check that is too lenient is worse than none: the first library check passed two bad builds because it counted `/system/lib64` as visible to vendor code, and an early version of a check reported "0 problems" because it had checked 0 files. Make a checker fail when it verified nothing.

**Why:** three builds were flashed that a stricter check on the laptop would have rejected, each costing a 10 to 15 minute flash cycle that needs the user's hands on the phone.
