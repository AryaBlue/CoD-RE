"""Progress bars for a running converter build, read from its log.

usage: python313\\python.exe tools\\build_status.py [log=build_bo1.log] [--watch]
"""
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# build steps in order, and the log line that starts each
STEPS = [
    ("Prepare sources", "== 0."),
    ("Staging", "== 2."),
    ("Build mod", "== 3a."),
    ("Compile scripts", "== 3b."),
    ("Link map", "== 4."),
    ("Audit + install", "== 5."),
]
# staging parts (phase names as logged; the material phase runs twice: map, then weapons/effects)
STAGING_PHASES = 21
ITEM = re.compile(r"^\[staging\] (.+?) (\d+)/(\d+)(?::|$| )")
PHASE_DONE = re.compile(r"^\[staging\] (.+) finished in ([\d.]+)s")
PHASE_START = re.compile(r"^\[staging\] ([^\[\]]+?)\.\.\.$")
ERROR = re.compile(r"^(waw2bo2: error: .*|RuntimeError: .*|Traceback .*)")


def bar(done: int, total: int, width: int = 30) -> str:
    total = max(total, 1)
    filled = round(width * min(done, total) / total)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {100 * min(done, total) // total:3d}%"


def side_jobs() -> list[str]:
    """BO2 All2Raw extractions (tmp/all2raw_*.log) and the early script compile (compile_scripts.log)
    touched in the last hour: running while their log keeps changing."""
    now = time.time()
    lines = []
    logs = sorted((ROOT / "tmp").glob("all2raw_*.log")) + [ROOT / "compile_scripts.log"]
    for log in logs:
        if not log.is_file() or now - log.stat().st_mtime > 3600:
            continue
        text = log.read_text(encoding="utf-8", errors="replace").splitlines()
        last = next((l.strip() for l in reversed(text) if l.strip()), "")
        if log.name.startswith("all2raw_"):
            name = "extract BO2 " + log.stem.removeprefix("all2raw_")
            done = any(l.startswith("Timing: total") or "Finished" in l for l in text)
        else:
            name = "early script compile"
            done = last.startswith("exit") or any(l.startswith("compiled ") for l in text[-3:]) and \
                now - log.stat().st_mtime > 20
        state = "done" if done or now - log.stat().st_mtime > 120 else "running"
        lines.append(f"  {name:<24} {state:<8} {last[:90]}")
    return lines


def status(log: Path) -> str:
    if not log.is_file():
        return f"no log at {log}"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    step = -1
    for line in lines:
        for i, (_, marker) in enumerate(STEPS):
            if line.startswith(marker):
                step = max(step, i)
    phases_done = [m for m in map(PHASE_DONE.match, lines) if m]
    # latest phase start, item counter and phase end, by line position
    starts = [(i, m[1]) for i, m in enumerate(map(PHASE_START.match, lines)) if m]
    ends = [i for i, line in enumerate(lines) if PHASE_DONE.match(line)]
    items = [(i, m) for i, m in enumerate(map(ITEM.match, lines)) if m]
    current = starts[-1][1] if starts and (not ends or starts[-1][0] > ends[-1]) else None
    item = items[-1][1] if items and (not ends or items[-1][0] > ends[-1]) else None
    error = next((m[1] for m in map(ERROR.match, reversed(lines)) if m), None)
    out = ["Kino build status  (" + log.name + ", updated " + time.strftime("%H:%M:%S",
           time.localtime(log.stat().st_mtime)) + ")", ""]
    out.append(f"Overall   {bar(step + 1, len(STEPS))}  step {max(step, 0) + 1}/{len(STEPS)}: "
               f"{STEPS[max(step, 0)][0]}")
    resumed = any(line.startswith("== resuming") for line in lines)
    if resumed:
        out.append("Staging   reused from the last build (resumed with --from)")
    elif step >= 1:
        done = len(phases_done)
        out.append(f"Staging   {bar(done if step == 1 else STAGING_PHASES, STAGING_PHASES)}  "
                   f"{min(done, STAGING_PHASES)}/{STAGING_PHASES} parts")
        if step == 1:
            remaster = sum(1 for line in lines if line.startswith("[staging] Remaster: reading"))
            if current:
                out.append(f"          now: {current}")
            elif remaster and not item:
                out.append(f"          now: extracting BO2 materials (one time per map), {remaster} zones started")
            if item:
                out.append(f"          {item[1][:14]:<15}{bar(int(item[2]), int(item[3]))}  {item[2]}/{item[3]}")
    if phases_done:
        slow = sorted(phases_done, key=lambda m: -float(m[2]))[:3]
        out.append("")
        out.append("Slowest parts so far: " + ", ".join(f"{m[1]} {float(m[2]):.0f}s" for m in slow))
    jobs = side_jobs()
    if jobs:
        out += ["", "Side jobs (separate from the main build):"] + jobs
    if error:
        out += ["", "STOPPED: " + error[:200] + ("  (main build paused; side jobs above are fixing it)"
                                                 if any("running" in j for j in jobs) else "")]
    else:
        tail = next((l for l in reversed(lines) if l.strip()), "")
        out += ["", "last: " + tail[:150]]
    return "\n".join(out)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    log = Path(args[0]) if args else ROOT / "build_bo1.log"
    if "--watch" not in sys.argv:
        print(status(log))
        return
    while True:
        text = status(log)
        sys.stdout.write("\x1b[2J\x1b[H" + text + "\n\n(Ctrl+C to stop watching; the build keeps running)\n")
        sys.stdout.flush()
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
