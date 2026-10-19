"""Summarise the latest Plutonium T6 zombies crash and the converter's runtime warnings.

Prints the newest crashdumps/*.txt (exception address, last GSC error and position, GSC callstack), the
console_zm.log lines the converter logs at runtime (WAW2BO2 BAD VECTOR / UNSUPPORTED / STUCK ...), and
the last lines the game wrote before it stopped. A known engine address is named (KNOWN_CRASHES).

usage: python313\\python.exe tools\\check_crash.py [--all-warnings]
"""
import argparse
import os
import re
from collections import Counter
from pathlib import Path

PLUTONIUM = Path(os.environ["LOCALAPPDATA"]) / "Plutonium"
LOG = PLUTONIUM / "storage/t6/main/console_zm.log"
# engine exception addresses already traced to converter data (t6zm, Plutonium r5369)
KNOWN_CRASHES = {
    0x00762F63: "spot-light shadow pass read a corrupted GfxShadowGeometry.smodelIndex: the engine fills those "
                "lists at runtime and overflowed lists shipped in the zone (fixed: the bridge linker ships them empty)",
    0x0073C705: "engine appending to a light's GfxShadowGeometry list ran off a list shipped in the zone (fixed: "
                "the bridge linker ships them empty)",
    0x0072671B: "drawing a brush model (door) read past gfxWorld.models: the linker shipped only the world model "
                "(fixed: GfxWorldLinker::LoadModels iterated a destroyed JSON temporary; check the build log for "
                "'Loaded N brush models', N should be 1 + the submodel count)",
}
NOISE = re.compile(r"^(Could not load |WAW2BO2 UNSUPPORTED FX |\s+\w+ \"|'.*' is not a valid value|  Domain is)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-warnings", action="store_true", help="list every WAW2BO2 line, not just counts")
    a = ap.parse_args()
    reports = sorted((PLUTONIUM / "crashdumps").glob("*.txt"), key=lambda p: p.stat().st_mtime)
    if reports:
        report = reports[-1]
        text = report.read_text(encoding="utf-8", errors="replace")
        print(f"== {report.name}\n{text.strip()}")
        address = re.search(r"Exception Address: 0x([0-9A-Fa-f]+)", text)
        if address and int(address[1], 16) in KNOWN_CRASHES:
            print(f"\nKNOWN: {KNOWN_CRASHES[int(address[1], 16)]}")
        print("(the GSC position is the script that was running, not necessarily the cause of a native crash)")
    else:
        print("no crash reports in", PLUTONIUM / "crashdumps")
    if not LOG.is_file():
        return 0
    if reports and LOG.stat().st_mtime < reports[-1].stat().st_mtime - 600:
        print(f"\n!! {LOG.name} is older than the crash report: logging was off for that session, so the"
              "\n!! lines below are from an earlier run. Type logfile 2 in the console before loading the map.")
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    warnings = [l for l in lines if l.startswith("WAW2BO2 ") and not l.startswith("WAW2BO2 UNSUPPORTED FX ")]
    print(f"\n== converter runtime lines in {LOG.name}: {len(warnings)}")
    if a.all_warnings:
        print(*warnings, sep="\n")
    else:
        bad = [l for l in warnings if l.startswith(("WAW2BO2 BAD VECTOR", "WAW2BO2 SPIN"))]
        print(*bad or ["no BAD VECTOR or SPIN lines"], sep="\n")
        kinds = Counter(" ".join(l.split()[:2]) for l in warnings if not l.startswith(("WAW2BO2 BAD VECTOR", "WAW2BO2 SPIN")))
        for kind, count in kinds.most_common():
            print(f"  {count:5}  {kind} ...  (--all-warnings lists them)")
    errors = [l for l in lines if re.search(r"script runtime error|COM_ERROR|Error:|EXE_", l)]
    if errors:
        print("\n== errors", *errors[-15:], sep="\n")
    tail = [l for l in lines if not NOISE.match(l)][-15:]
    print("\n== last lines before the log stopped", *tail, sep="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
