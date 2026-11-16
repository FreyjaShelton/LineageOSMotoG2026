# Lessons

Working rules and lessons learned for this project. Add to this file as new lessons come up.

## Start of every new chat: read these files first

When a new chat is told to "read the lessons file", read all of these before doing anything else, then continue from the latest status:

1. `LESSONS.md` (this file): working rules.
2. `README.md`: device facts (Moto g 2026, `utah`, XT2613-1), the `nevada` community tree, firmware and recovery notes.
3. `BUILD_PLAN.md`: where we build (the Linux laptop), the memory and crash rules, and each phase's status. The newest status is in the open Phase 2 items. This is where we left off.
4. `scripts/`: skim the header comment of each script (`build-nevada.sh` is the main entry point; `build-progress.sh` and `build-live.sh` are the watchers).

Then look outside the repo for live state: `tail ~/lineage/build.log`, `systemctl --user list-units 'lineage-build-*'` (is a build running?), and `journalctl --list-boots` (did the laptop crash or reboot since the last notes?).

**Why:** the user only wants to say "read the lessons file" at the start of a chat, and not list the other files each time.

## Use Sonnet 5.5 by default

This project's chats should run on Sonnet 5.5 (`claude-sonnet-5-5`), not Opus. A chat cannot switch its own model. If a new chat finds it is running on another model, say so at the start, so the user can pick Sonnet in the app's model menu. To make Sonnet the default for new chats, set `"model": "claude-sonnet-5-5"` in `~/.claude/settings.json`.

**Why:** the user's choice. Sonnet is enough for this work.

## Don't ask to commit changes unless asked

Do not offer or ask to commit (or push) changes. Make the edits and leave them in the working tree. Only run git commit/push when the user explicitly asks for it.

**Why:** The user decides when work is ready to be committed. Prompting for it every time is noise.
