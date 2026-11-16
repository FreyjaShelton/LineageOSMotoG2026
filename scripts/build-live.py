#!/usr/bin/env python3
"""Live build display: a progress bar, one summary line per Ninja step, and
green streaks falling through the text.

    LineageOS nevada build   * running   elapsed 0h35m
    [███████████░░░░░░░░░░░░░░░░░░░]  31.5%  62501/197761  ~1h50m left
     │ 4 ┃ │ ; ┃                    (green streaks fall through the lines)
     21:17:56   31%   62501/197761  ~1h50m left | libcodec2_soft_flacenc ...
     >>> FAILED: ...            (failures and errors, in red)
     libcodec2_soft_flacenc license metadata       (footer: current step)

It follows ~/lineage/build.log by name, so it survives build restarts, and it
waits between builds. Ctrl-C quits; the build keeps going. Not a terminal
(piped)? It falls back to plain one-line-per-step output.

Environment: LOG=path  FPS=12  NO_ANIM=1 (bar and text, no streaks)
Self-test:   build-live.py --frames N --size WxH   (prints one frame, no screen takeover)
"""
import collections
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import time

LOG = os.environ.get("LOG", os.path.expanduser("~/lineage/build.log"))
FPS = float(os.environ.get("FPS", "12"))
ANIM = not os.environ.get("NO_ANIM")

PROGRESS = re.compile(r"^\[ *(\d+)% (\d+)/(\d+)\] (.*)$")
PROBLEM = re.compile(
    r"^(FAILED:|ninja: |#### |== build )|[Ee]rror[: ]|fatal error|undefined (reference|symbol)"
)
UNIT_TIME = re.compile(r"lineage-build-(\d{8}-\d{6})")

GREENS = [22, 28, 34, 40, 46, 82]  # dim -> bright
BOLD, DIM_TEXT, TEXT, BAR_FILL, BAR_EMPTY = "1", "38;5;245", "38;5;252", "38;5;45", "38;5;238"
RED, YELLOW, GREEN = "1;38;5;196", "38;5;220", "1;38;5;46"
PARTIAL = " ▏▎▍▌▋▊▉"


def hm(s):
    s = int(s)
    return f"{s // 3600}h{s % 3600 // 60:02d}m"


class State:
    """What the log says so far."""

    def __init__(self):
        self.lines = collections.deque(maxlen=500)  # each: list of (text, style) segments
        self.pct = self.step = self.total = 0
        self.eta, self.task = "", ""
        self.t0 = self.s0 = None

    def reset_average(self):
        self.t0 = self.s0 = None

    def feed(self, line, now):
        stamp = time.strftime("%H:%M:%S", time.localtime(now))
        m = PROGRESS.match(line)
        if m:
            self.pct, self.step, self.total = int(m[1]), int(m[2]), int(m[3])
            self.task = re.sub(r"^//[^ ]*:", "", m[4])
            if self.t0 is None or self.step < self.s0:
                self.t0, self.s0 = now, self.step
            self.eta = ""
            if now - self.t0 >= 60 and self.step > self.s0:
                left = (self.total - self.step) * (now - self.t0) / (self.step - self.s0)
                self.eta = f"~{hm(left)} left"
            self.lines.append([
                (stamp + " ", DIM_TEXT),
                (f"{self.pct:>4}% ", BOLD),
                (f"{self.step:>7}/{self.total:<7} ", TEXT),
                (f"{self.eta:<13}", YELLOW),
                ("| ", DIM_TEXT),
                (self.task, TEXT),
            ])
        elif PROBLEM.search(line):
            self.lines.append([(f">>> {line[:300]}", RED)])


class Follower:
    """Follow a file by name; notice when a new build truncates it."""

    def __init__(self, path):
        self.path, self.pos, self.partial = path, None, ""

    def read(self):
        """Return (new_lines, was_truncated)."""
        try:
            size = os.stat(self.path).st_size
        except OSError:
            return [], False
        truncated = False
        if self.pos is None:  # first look: start 12 KB before the end, for context
            self.pos = max(0, size - 12288)
            self.partial = "skip"  # the first chunk may begin mid-line
        elif size < self.pos:
            self.pos, self.partial, truncated = 0, "", True
        if size == self.pos:
            return [], truncated
        with open(self.path, "rb") as f:
            f.seek(self.pos)
            raw = f.read(1 << 20)
        self.pos += len(raw)
        data = raw.decode("utf-8", "replace")
        parts = re.split(r"[\r\n]", (self.partial if self.partial != "skip" else "") + data)
        skip_first = self.partial == "skip"
        self.partial = parts.pop()  # incomplete last line
        if skip_first and parts:
            parts.pop(0)
        return [p for p in parts if p], truncated


def build_unit():
    """(unit name, start epoch) of the running build, or (None, None)."""
    try:
        out = subprocess.run(
            ["systemctl", "--user", "list-units", "lineage-build-*", "--no-legend", "--plain"],
            capture_output=True, text=True, timeout=3).stdout.split()
    except Exception:
        return None, None
    if not out:
        return None, None
    m = UNIT_TIME.search(out[0])
    start = time.mktime(time.strptime(m[1], "%Y%m%d-%H%M%S")) if m else None
    return out[0], start


SYMBOLS = "!#$%&*+-/:;<=>?@[]^~|\\{}()"


class Streaks:
    """Green streaks falling down the screen. Each is broken into pieces with
    gaps, made of line segments, digits and symbols that re-roll as it falls.
    Speeds vary widely (slow and dim to fast and bright); the head is brightest and the tail fades."""

    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        n = max(12, cols * rows // 30) if rows > 0 else 0
        self.s = [self.new(True) for _ in range(n)]

    @staticmethod
    def new_cell():
        r = random.random()
        if r < 0.22:
            return None  # a gap
        if r < 0.60:
            return "L"  # a line segment
        if r < 0.82:
            return random.choice("0123456789")
        return random.choice(SYMBOLS)

    def new(self, anywhere):
        fast = random.random()  # 0 = slowest, 1 = fastest
        speed = 0.05 * 32 ** fast  # 0.05 to 1.6 rows per frame, an even spread of speeds
        length = 3 + int(fast * 12) + random.randint(0, 4)  # faster ones are longer
        cells = [self.new_cell() for _ in range(length)]
        cells[0] = random.choice(["L", random.choice("0123456789"), random.choice(SYMBOLS)])
        y = random.uniform(-length, self.rows) if anywhere else -length - random.random() * 8
        return {"x": random.randrange(max(1, self.cols)), "y": y, "v": speed,
                "cells": cells, "base": int(fast * 4.99)}

    def step(self):
        for i, s in enumerate(self.s):
            s["y"] += s["v"]
            if random.random() < 0.15:  # flicker: one piece changes
                s["cells"][random.randrange(1, len(s["cells"]))] = self.new_cell()
            if s["y"] - len(s["cells"]) > self.rows:
                self.s[i] = self.new(False)

    def cells(self):
        grid = {}
        for s in self.s:
            n = len(s["cells"])
            for i, c in enumerate(s["cells"]):  # i = 0 is the head
                cy = int(s["y"]) - i
                if c is None or not 0 <= cy < self.rows:
                    continue
                shade = max(0, s["base"] - (i * 3) // n)
                ch = ("┃" if shade >= 3 else "│") if c == "L" else c
                grid[(cy, s["x"])] = (ch, f"38;5;{GREENS[shade]}", shade)
        return grid


def put(row, col, segments, cols):
    """Write text segments into a row of cells, skipping spaces (so the
    animation shows through them)."""
    for text, style in segments:
        for ch in text:
            if col >= cols:
                return
            if ch != " ":
                row[col] = (ch, style)
            col += 1


def render_row(cells):
    out, cur = [], None
    for ch, style in cells:
        if style != cur:
            out.append("\x1b[0m" + (f"\x1b[{style}m" if style else ""))
            cur = style
        out.append(ch)
    out.append("\x1b[0m\x1b[K")
    return "".join(out)


def frame(state, streaks, cols, rows, status, elapsed):
    blank = lambda: [(" ", "")] * cols
    lines = []

    # Header
    row = blank()
    put(row, 0, [(" LineageOS nevada build   ", BOLD), (status[0], status[1]),
                 (f"   elapsed {hm(elapsed)}" if elapsed is not None else "", DIM_TEXT)], cols)
    lines.append(row)

    # Progress bar
    frac = state.step / state.total if state.total else 0.0
    suffix = f" {frac * 100:5.1f}%  {state.step}/{state.total}  {state.eta}"
    width = max(10, cols - len(suffix) - 3)
    filled = frac * width
    full = int(filled)
    row = blank()
    segs = [(" [", DIM_TEXT), ("█" * full, BAR_FILL)]
    if full < width:
        eighths = int((filled - full) * 8)  # a partial block for the fraction
        segs.append((PARTIAL[eighths], BAR_FILL) if eighths else ("░", BAR_EMPTY))
        segs.append(("░" * (width - full - 1), BAR_EMPTY))
    segs += [("]", DIM_TEXT), (suffix, BOLD)]
    col = 0
    for text, style in segs:  # the bar row is solid: spaces are written too
        for ch in text:
            if col < cols:
                row[col] = (ch, style)
            col += 1
    lines.append(row)

    # Body: animation underneath, log lines on top, bottom-aligned
    body = rows - 3
    grid = streaks.cells() if (streaks and ANIM) else {}
    shown = list(state.lines)[-body:] if body > 0 else []
    for r in range(body):
        row = [grid[(r, c)][:2] if (r, c) in grid else (" ", "") for c in range(cols)]
        k = r - (body - len(shown))
        if 0 <= k < len(shown):
            under = row[:]
            put(row, 0, [(" ", "")] + shown[k], cols)
            for c in range(cols):  # streaks fall through the words
                g = grid.get((r, c))
                if g and row[c] != under[c]:  # a text character is here
                    ch, style, shade = g
                    # bright head replaces the character; the fading tail tints it
                    row[c] = (ch, "1;" + style) if shade >= 3 else (row[c][0], style)
        lines.append(row)

    # Footer
    row = blank()
    hint = "Ctrl-C quits (build keeps going) "
    room = max(0, cols - len(hint) - len(" now: ") - 2)
    put(row, 0, [(" now: ", DIM_TEXT), (state.task[:room], TEXT)], cols)
    if cols > len(hint) + 20:
        put(row, cols - len(hint), [(hint, DIM_TEXT)], cols)
    lines.append(row)
    return lines


def main():
    args = sys.argv[1:]
    test_frames, test_size = 0, None
    if "--frames" in args:
        test_frames = int(args[args.index("--frames") + 1])
    if "--size" in args:
        w, h = args[args.index("--size") + 1].lower().split("x")
        test_size = (int(w), int(h))

    follower, state = Follower(LOG), State()

    def pump():
        new, truncated = follower.read()
        if truncated:
            state.reset_average()
        now = time.time()
        for line in new:
            state.feed(line, now)

    if not sys.stdout.isatty() and not test_frames:  # plain mode
        while True:
            new, truncated = follower.read()
            if truncated:
                state.reset_average()
            for line in new:
                before = len(state.lines)
                state.feed(line, time.time())
                for segs in list(state.lines)[before:]:
                    print("".join(t for t, _ in segs), flush=True)
            time.sleep(0.2)

    streaks, size = None, None
    unit, start, last_check = None, None, 0.0

    def size_now():
        if test_size:
            return test_size
        s = shutil.get_terminal_size((100, 30))
        return s.columns, s.lines

    if not test_frames:
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        n = 0
        while True:
            t = time.time()
            pump()
            if t - last_check > 2:
                unit, start = build_unit()
                last_check = t
            cols, rows = size_now()
            if (cols, rows) != size:
                size, streaks = (cols, rows), Streaks(cols, rows - 3)
            streaks.step()
            if unit:
                status, elapsed = ("● running", GREEN), (t - start if start else None)
            else:
                status, elapsed = ("○ no build running, waiting for the next one", YELLOW), None
            rows_out = frame(state, streaks, cols, rows, status, elapsed)
            text = "\x1b[H" + "\r\n".join(render_row(r) for r in rows_out)
            n += 1
            if test_frames:
                if n >= test_frames:
                    print(text)
                    return
                continue
            sys.stdout.write(text)
            sys.stdout.flush()
            time.sleep(max(0.0, 1.0 / FPS - (time.time() - t)))
    except KeyboardInterrupt:
        pass
    finally:
        if not test_frames:
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:  # e.g. piped into `head`
        sys.stderr.close()
