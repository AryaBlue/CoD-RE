"""Compare a converted map's linked GfxWorld against stock BO2 zombies maps (hardening audit).

The bridge unlinker writes <map>.d3dbsp.gfxworld_audit.json next to the map entities (MapEntsDumperT6
DumpGfxWorldAudit): every world array's count/null state and every stored index against its limit. Two classes
of engine crash are flagged:
  RUNTIME-OWNED  a field every stock map ships empty/null but the port fills (the engine may fill it itself at
                 runtime and overflow ours: the GfxShadowGeometry crash)
  OUT OF RANGE   an index past what it indexes (beyond what stock maps also do, e.g. "none" sentinels)

usage: python313\\python.exe tools\\check_world.py <map.ff> [--stock zm_nuked,zm_prison,zm_tomb,zm_highrise]
exit 1 when anything is flagged.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNLINKER = ROOT / "reference/b2w/vendor/OpenAssetToolsT6/build/bin/Release_x86/Unlinker.exe"
BO2_ZONE = Path(r"D:\SteamLibrary\steamapps\common\Call of Duty Black Ops II\zone\all")
CACHE = ROOT / "tmp/worldaudit"
STOCK = "zm_nuked,zm_prison,zm_tomb,zm_highrise"
# differences from stock already checked in game: noted, not flagged
KNOWN = {
    "lightGrid.colors": "the bridge linker ships the source colour light grid where stock maps use SH coefficients "
                        "(Kino renders with it)",
}


def audit(ff: Path, refresh: bool) -> dict:
    out = CACHE / ff.stem
    found = sorted(out.glob("maps/mp/*.gfxworld_audit.json"))
    if refresh or not found or found[0].stat().st_mtime < ff.stat().st_mtime:
        subprocess.run([str(UNLINKER), "--no-color", "--skip-obj", "--search-path", str(BO2_ZONE),
                        "--include-assets", "mapents", "--output-folder", str(out), str(ff)],
                       check=False, capture_output=True)
        found = sorted(out.glob("maps/mp/*.gfxworld_audit.json"))
    if not found:
        raise SystemExit(f"no gfxworld audit for {ff} (unlinker at {UNLINKER} too old?)")
    return json.loads(found[0].read_text(encoding="utf-8"))


def empty(value) -> bool:
    return value["null"] or value["count"] == 0 if isinstance(value, dict) else value == 0


def check(port: dict, stock: dict[str, dict]) -> list[str]:
    flagged = []
    for name, value in sorted(port["fill"].items()):
        stock_values = [s["fill"].get(name) for s in stock.values() if name in s["fill"]]
        if stock_values and all(empty(v) for v in stock_values) and not empty(value):
            if name in KNOWN:
                print(f"note: {name}: {KNOWN[name]}")
                continue
            flagged.append(f"RUNTIME-OWNED? {name}: every stock map ships it empty, this map fills it ({value})")
    for name, value in sorted(port["ranges"].items()):
        if not value["bad"]:
            continue
        # stock maps exceeding the same limit show a sentinel ("none") the engine handles
        stock_max = max((s["ranges"][name]["max"] - s["ranges"][name]["limit"] for s in stock.values()
                         if name in s["ranges"] and s["ranges"][name]["bad"]), default=None)
        if stock_max is not None and value["max"] - value["limit"] <= stock_max:
            continue
        flagged.append(f"OUT OF RANGE {name}: {value['bad']} of {value['n']} values >= {value['limit']} (max {value['max']})")
    return flagged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ff", type=Path)
    ap.add_argument("--stock", default=STOCK)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--table", action="store_true", help="print every field next to the stock values")
    a = ap.parse_args()
    stock = {name: audit(BO2_ZONE / f"{name}.ff", a.refresh) for name in a.stock.split(",")}
    port = audit(a.ff.resolve(), True)
    if a.table:
        show = lambda v: "-" if v is None else (f"{v['count']}{' null' if v['null'] else ''}" if isinstance(v, dict) else str(v))
        for name in sorted(port["fill"]):
            print(f"  {name:32} {' | '.join(show(s['fill'].get(name)) for s in stock.values()):55} -> {show(port['fill'][name])}")
        for name, v in sorted(port["ranges"].items()):
            cols = " | ".join(f"{s['ranges'][name]['max']}/{s['ranges'][name]['limit']}" for s in stock.values() if name in s["ranges"])
            print(f"  {name:32} {cols:55} -> {v['max']}/{v['limit']} bad {v['bad']}")
    flagged = check(port, stock)
    print(*flagged or [f"{port['name']}: no runtime-owned or out-of-range world data vs {', '.join(stock)}"], sep="\n")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
