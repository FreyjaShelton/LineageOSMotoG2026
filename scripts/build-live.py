#!/usr/bin/env python3
"""Live build display: a progress bar, one summary line per Ninja step, and
green streaks falling through the text.

    LineageOS nevada build   * running   elapsed 0h35m
    [███████████░░░░░░░░░░░░░░░░░░░]
     31.5%  62501/197761  ~1h50m left            (each bar's text sits under it)
     │ 4 ┃ │ ; ┃                    (green streaks fall through the lines)
     21:17:56   31%   62501/197761  ~1h50m left | libcodec2_soft_flacenc ...
     >>> FAILED: ...            (failures and errors, in red)
     libcodec2_soft_flacenc license metadata       (footer: current step)

It follows ~/lineage/build.log by name, so it survives build restarts, and it
waits between builds. Ctrl-C quits; the build keeps going. Not a terminal
(piped)? It falls back to plain one-line-per-step output.

Sync mode: the same display for a running `repo sync`, with two bars: projects landed (of the
manifest total) and the size of the source tree on disk against EXPECT_GB (default 117, what a
finished sync came to). The project bar reaches 100% while the last huge projects are still
downloading, which is why the size bar is there too. One line appears per project as it lands,
and the log (~/lineage/sync.log) supplies errors and the final `exit=N`. TOP=<source tree>.
Chosen by `sync` or `--sync` on the command line (`wsl.exe` swallows `--sync`, so use
`build-live.sh sync` from Windows), by SYNC=1, or automatically when a `repo sync` is running
and no build is.

Soong analysis (the first minutes of a build, before Ninja counts steps): while `soong_build` is
running the bar shows elapsed time against a typical SOONG_EST seconds (default 360, an estimate,
capped at 99%) plus soong_build's RAM and CPU time. There is no real step count to show.

Remote mode (`build-live.py remote`, run natively on the Windows PC): show a build that is running
on another machine, over ssh. It copies scripts/build-live-feed.sh to the host (REMOTE_HOST, default
`laptop`, an ssh shortcut), runs it there, and draws the log lines and status it prints (build running
or not, elapsed time, soong_build figures). It reconnects by itself if the connection drops.

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
import threading
import time

def _auto_sync():
    """No build unit running but a `repo sync` is: show the sync."""
    try:
        run = lambda *a: subprocess.run(a, capture_output=True, text=True, timeout=3).stdout.strip()
        return not run("systemctl", "--user", "list-units", "lineage-build-*", "--no-legend", "--plain")             and bool(run("pgrep", "-f", "repo sync"))
    except Exception:
        return False


SYNC = bool({"--sync", "sync"} & set(sys.argv[1:])) or bool(os.environ.get("SYNC")) or _auto_sync()
TOP = os.environ.get("TOP", os.path.expanduser("~/lineage/android"))
REMOTE = "remote" in sys.argv[1:] or bool(os.environ.get("REMOTE"))
REMOTE_HOST = os.environ.get("REMOTE_HOST", "laptop")
SOONG_EST = int(os.environ.get("SOONG_EST", "360"))
EXPECT_MB = float(os.environ.get("EXPECT_GB", "117")) * 1024
LOG = os.environ.get("LOG", os.path.expanduser("~/lineage/sync.log" if SYNC else "~/lineage/build.log"))
FPS = float(os.environ.get("FPS", "12"))
ANIM = not os.environ.get("NO_ANIM")

PROGRESS = re.compile(r"^\[ *(\d+)% (\d+)/(\d+)\] (.*)$")
PROBLEM = re.compile(
    r"^(FAILED:|ninja: |#### |== build )|[Ee]rror[: ]|fatal error|undefined (reference|symbol)"
)
EXIT = re.compile(r"^exit=(\d+)")
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
        self.exit = None  # sync mode: exit code from the log's last line
        self.extra = ""  # sync mode: download figures for the header
        self.soong_hist = []  # build mode: (time, soong_build CPU seconds) samples
        self.soong = None  # build mode: (RAM MB, seconds running, CPU seconds) of soong_build
        self.bar = None  # sync mode: (MB now, MB expected, eta text) drives the bar

    def reset_average(self):
        self.t0 = self.s0 = None
        self.exit = None

    def progress(self, pct, step, total, task, now, quiet=False, use_eta=True):
        """Record progress; add a summary line unless `quiet`."""
        stamp = time.strftime("%H:%M:%S", time.localtime(now))
        self.pct, self.step, self.total, self.task = pct, step, total, task
        if self.t0 is None or self.step < self.s0:
            self.t0, self.s0 = now, self.step
        self.eta = ""
        if use_eta and now - self.t0 >= 60 and self.step > self.s0:
            left = (self.total - self.step) * (now - self.t0) / (self.step - self.s0)
            self.eta = f"~{hm(left)} left"
        if quiet:
            return
        self.lines.append([
            (stamp + " ", DIM_TEXT),
            (f"{self.pct:>4}% ", BOLD),
            (f"{self.step:>7}/{self.total:<7} ", TEXT),
            (f"{self.eta:<13}", YELLOW),
            ("| ", DIM_TEXT),
            (self.task, TEXT),
        ])

    def feed(self, line, now):
        m = PROGRESS.match(line)
        if m:
            self.progress(int(m[1]), int(m[2]), int(m[3]), re.sub(r"^//[^ ]*:", "", m[4]), now)
            return
        m = EXIT.match(line)
        if m:
            self.exit = int(m[1])
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


class RemoteFeed:
    """Remote mode: run build-live-feed.sh on REMOTE_HOST over ssh and collect what it prints."""

    def __init__(self):
        self.lines = collections.deque()  # log lines waiting to be fed to State
        self.status = None  # (unit, start epoch, now epoch, soong RAM MB, soong secs, soong CPU secs)
        self.connected, self.error = False, ""
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        feed = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build-live-feed.sh")
        opts = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=10"]
        while True:
            try:
                subprocess.run(["scp", "-q", *opts, feed, f"{REMOTE_HOST}:/tmp/build-live-feed.sh"],
                               check=True, capture_output=True, timeout=30)
                p = subprocess.Popen(["ssh", *opts, REMOTE_HOST, "bash /tmp/build-live-feed.sh"],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.connected, self.error, buf = True, "", b""
                while True:
                    chunk = p.stdout.read1(65536)
                    if not chunk:
                        break
                    buf += chunk
                    parts = re.split(rb"[\r\n]", buf)
                    buf = parts.pop()
                    for raw in parts:
                        line = raw.decode("utf-8", "replace")
                        if line.startswith("@@STATUS "):
                            f = line.split()[1:]
                            self.status = (f[0], int(f[1]), int(f[2]), int(f[3]), int(f[4]), int(f[5]))
                        elif line:
                            self.lines.append(line)
            except Exception as e:  # ssh or scp failed: say so, then try again
                self.error = str(e)[:80]
            self.connected, self.status = False, None
            time.sleep(3)


class SyncWatcher:
    """Sync mode: count the projects that have landed in the work tree (they get a
    .git entry once checked out) and measure the size of .repo in a helper thread."""

    def __init__(self):
        self.paths, self.seen, self.first = [], set(), True
        self.last_load = self.last_poll = 0.0
        self.mb, self.rate, self._samples, self.start = 0, 0.0, [], None
        threading.Thread(target=self._du_loop, daemon=True).start()

    def _du_loop(self):
        while True:
            try:
                out = subprocess.run(["nice", "-n", "19", "ionice", "-c3", "du", "-sm", TOP], capture_output=True, text=True,
                                     timeout=120).stdout.split()
                now = time.time()
                self.mb = int(out[0])
                if self.start is None:
                    self.start = (now, self.mb)
                self._samples = [x for x in self._samples if now - x[0] < 120] + [(now, self.mb)]
                (t0, m0), (t1, m1) = self._samples[0], self._samples[-1]
                self.rate = (m1 - m0) * 60 / (t1 - t0) if t1 - t0 >= 5 else self.rate
            except Exception:
                pass
            time.sleep(20)  # du of a 100 GB tree costs a core for seconds: keep it rare

    def load(self, now):
        if self.paths or now - self.last_load < 10:
            return
        self.last_load = now
        try:
            out = subprocess.run(["repo", "list", "-p"], cwd=TOP, capture_output=True,
                                 text=True, timeout=60).stdout.split()
            self.paths = sorted(out)
        except Exception:
            pass

    def poll(self, state, now):
        if now - self.last_poll < 2 and not self.first:  # about 1,100 stat calls: not every frame
            return
        self.last_poll = now
        self.load(now)
        if not self.paths:
            return
        new = [p for p in self.paths if p not in self.seen
               and os.path.exists(os.path.join(TOP, p, ".git"))]
        total = len(self.paths)
        if self.first:  # whatever is already there: no lines, just the starting point
            self.seen.update(new)
            state.progress(len(self.seen) * 100 // total, len(self.seen), total, "", now,
                           quiet=True, use_eta=False)
            self.first = False
        for p in new:
            if p in self.seen:
                continue
            self.seen.add(p)
            n = len(self.seen)
            state.progress(n * 100 // total, n, total, p, now, use_eta=False)
        if self.mb:
            eta = ""
            if self.start and now - self.start[0] >= 60 and self.mb > self.start[1]:
                avg = (self.mb - self.start[1]) / (now - self.start[0])  # MB/s since we started
                left = max(0.0, EXPECT_MB - self.mb) / avg
                eta = f"~{hm(left)} left"
            state.bar = (self.mb, EXPECT_MB, eta)
            state.extra = f"   {self.rate:.0f} MB/min"


def sync_proc():
    """(pid, start epoch) of the running `repo sync`, or (None, None)."""
    try:
        pid = subprocess.run(["pgrep", "-of", "repo sync"], capture_output=True, text=True,
                             timeout=3).stdout.split()
        if not pid:
            return None, None
        age = subprocess.run(["ps", "-o", "etimes=", "-p", pid[0]], capture_output=True,
                             text=True, timeout=3).stdout.strip()
        return pid[0], time.time() - int(age)
    except Exception:
        return None, None


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


def soong_info():
    """(RAM MB, seconds running, CPU seconds) of a running soong_build, else None."""
    try:
        out = subprocess.run(["ps", "-C", "soong_build", "-o", "rss=,etimes=,cputimes="],
                             capture_output=True, text=True, timeout=3).stdout.split()
        return (int(out[0]) // 1024, int(out[1]), int(out[2])) if len(out) >= 3 else None
    except Exception:
        return None


def bars_of(state):
    """The progress bars to draw, as (fraction, text after the bar)."""
    bars = []
    if state.soong and not SYNC:
        ram, el, cpu = state.soong
        frac = min(el / SOONG_EST, 0.99)
        h = state.soong_hist
        cores = (h[-1][1] - h[0][1]) / (h[-1][0] - h[0][0]) if len(h) > 1 and h[-1][0] > h[0][0] else 0.0
        # Soong prints nothing; busy cores is the only live signal. Many cores = parsing and
        # generating build actions; about one core = the serial finish (writing the ninja file).
        phase = "parallel part" if cores >= 1.5 else "serial part, about 1 core" if cores >= 0.15 else "waiting / disk"
        return [(frac, f" Soong analysis  {el // 60}m{el % 60:02d}s   {phase} ({cores:.1f} cores busy)   "
                       f"soong_build {ram / 1024:.1f} GB RAM   (no step count: bar = time vs a typical "
                       f"{SOONG_EST // 60} min, an estimate)")]
    if SYNC:
        frac = state.step / state.total if state.total else 0.0
        bars.append((frac, f" Projects  {frac * 100:5.1f}%  {state.step}/{state.total}"))
        cur, tot, eta = state.bar or (0, EXPECT_MB, "")
        frac = min(cur / tot, 0.995)  # the expected size is an estimate: never show 100% early
        bars.append((frac, f" Size on disk  {frac * 100:5.1f}%  {cur / 1024:.0f}/{tot / 1024:.0f} GB  {eta}"))
    else:
        frac = state.step / state.total if state.total else 0.0
        bars.append((frac, f" {frac * 100:5.1f}%  {state.step}/{state.total}  {state.eta}"))
    return bars


def chrome_rows():
    """Rows that are not the scrolling body: header, the bars (two rows each), footer."""
    return 2 + 2 * (2 if SYNC else 1)


def frame(state, streaks, cols, rows, status, elapsed):
    blank = lambda: [(" ", "")] * cols
    lines = []

    # Header
    row = blank()
    put(row, 0, [(" LineageOS sync   " if SYNC else
                  f" LineageOS nevada build on {REMOTE_HOST}   " if REMOTE else " LineageOS nevada build   ", BOLD),
                 (status[0], status[1]),
                 (f"   elapsed {hm(elapsed)}" if elapsed is not None else "", DIM_TEXT),
                 (state.extra, DIM_TEXT)], cols)
    lines.append(row)

    # Progress bars: one per kind of progress (a build has one, a sync has two)
    for frac, suffix in bars_of(state):  # every bar is full width, its text on the row below
        width = max(10, cols - 3)
        filled = frac * width
        full = int(filled)
        row = blank()
        segs = [(" [", DIM_TEXT), ("█" * full, BAR_FILL)]
        if full < width:
            eighths = int((filled - full) * 8)  # a partial block for the fraction
            segs.append((PARTIAL[eighths], BAR_FILL) if eighths else ("░", BAR_EMPTY))
            segs.append(("░" * (width - full - 1), BAR_EMPTY))
        segs += [("]", DIM_TEXT)]
        col = 0
        for text, style in segs:  # the bar row is solid: spaces are written too
            for ch in text:
                if col < cols:
                    row[col] = (ch, style)
                col += 1
        lines.append(row)
        row = blank()
        put(row, 0, [(suffix, BOLD)], cols)
        lines.append(row)

    # Body: animation underneath, log lines on top, bottom-aligned
    body = rows - chrome_rows()
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
    hint = f"Ctrl-C quits ({'sync' if SYNC else 'build'} keeps going) "
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
    watcher = SyncWatcher() if SYNC else None
    remote = RemoteFeed() if REMOTE else None
    if os.name == "nt":  # Windows console: UTF-8 output and ANSI escapes
        os.system("")
        sys.stdout.reconfigure(encoding="utf-8")

    def pump():
        if watcher:
            watcher.poll(state, time.time())
        if remote:
            now = time.time()
            while remote.lines:
                state.feed(remote.lines.popleft(), now)
            return
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
            if watcher:
                watcher.poll(state, time.time())
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
                if remote:
                    st = remote.status
                    unit = st[0] if st and st[0] != "-" else None
                    start = t - (st[2] - st[1]) if unit and st[1] else None  # the host's elapsed time
                elif SYNC:
                    unit, start = sync_proc()
                else:
                    unit, start = build_unit()
                if remote:
                    state.soong = (remote.status[3], remote.status[4], remote.status[5])                         if remote.status and remote.status[4] else None
                if not SYNC and not remote:
                    state.soong = soong_info()
                if not SYNC:
                    if state.soong:
                        state.soong_hist = [x for x in state.soong_hist if t - x[0] < 12] + [(t, state.soong[2])]
                    else:
                        state.soong_hist = []
                last_check = t
            cols, rows = size_now()
            if (cols, rows) != size:
                size, streaks = (cols, rows), Streaks(cols, rows - chrome_rows())
            streaks.step()
            if unit:
                status, elapsed = ("● running", GREEN), (t - start if start else None)
            elif SYNC and state.exit is not None:
                ok = state.exit == 0
                status, elapsed = ((f"✓ sync finished" if ok else f"✗ sync failed (exit {state.exit})"),
                                   GREEN if ok else RED), None
            else:
                what = "no sync running" if SYNC else "no build running, waiting for the next one"
                status, elapsed = (f"○ {what}", YELLOW), None
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
