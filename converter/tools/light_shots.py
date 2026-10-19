"""Screenshot fixed Kino spots with console settings applied, for lighting comparisons.

    python313\\python.exe tools\\light_shots.py <tag> ["dvar value" ...]

Opens the console (UK key), runs the commands, then for each spot runs
setviewpos and saves tmp/shots/<tag>_<spot>.png (+ _small). Needs sv_cheats 1
and noclip on; never sends god/noclip itself.
"""
import subprocess
import sys
import time
from pathlib import Path

UM = Path.home() / ".claude/plugins/marketplaces/universal-modder/bin/um"
PROC = "plutonium-bootstrapper-win32"
OUT = Path(__file__).resolve().parent.parent / "tmp" / "shots"
CONSOLE = "0xDF"
SPOTS = {
    "spawn": "-1 -1379 190 90 0",
    "balcony": "1400 -450 420 135 10",
    "theater": "60 200 140 90 0",
}


def drive(*steps: str):
    subprocess.run(["bash", str(UM), "win", "drive", "--proc", PROC, "focus", *steps],
                   check=True, capture_output=True, text=True, timeout=120)


def console(*commands: str):
    steps = [f"key {CONSOLE}", "sleep 900", "key 0x08", "key 0x08"]
    for c in commands:
        steps += [f"type {c}", "sleep 150", "key 0x0D", "sleep 250"]
    drive(*steps, f"key {CONSOLE}", "sleep 300")


def shot(name: str) -> Path:
    path = OUT / f"{name}.png"
    subprocess.run(["bash", str(UM), "win", "shot", "--exe", f"{PROC}.exe", str(path), "--scale", "0.5"],
                   check=True, capture_output=True, text=True, timeout=60)
    return path


def main() -> int:
    tag, commands = sys.argv[1], sys.argv[2:]
    OUT.mkdir(parents=True, exist_ok=True)
    if commands:
        console(*commands)
    for spot, pos in SPOTS.items():
        console(f"setviewpos {pos}")
        time.sleep(1.0)
        print(shot(f"{tag}_{spot}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
