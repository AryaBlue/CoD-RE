"""Subset BoD placements to match clip_tris_t8.py terrain cuts (same footprint/box test on origin XY).
Usage: ext_props.py out.json models.txt [--outside-footprint] [--box X0 Y0 X1 Y1] [--off-shell] [--src placements.json]"""
import argparse, collections, json, os
from pathlib import Path

GEO = Path(r"E:\ClaudeWork\bo3\bod_port\t8_world\geo")
RIP = Path(r"E:\ClaudeWork\bo3\greyhound\app\exported_files\black_ops_4\xmodels")
SHELL_FOOTPRINT = ((-2381, -4224), (4257, 10720))  # keep identical to clip_tris_t8.py

ap = argparse.ArgumentParser()
ap.add_argument("out", type=Path)
ap.add_argument("models", type=Path)
ap.add_argument("--src", type=Path, default=GEO / "bod_props_bounds_confident.json")
ap.add_argument("--outside-footprint", action="store_true")
ap.add_argument("--box", type=float, nargs=4)
ap.add_argument("--off-shell", action="store_true", help="also drop placements within 256u of a shell clip brush (XY)")
args = ap.parse_args()


def shell_cells(g=256):
    cells = set()
    for b in json.loads(Path(r"E:\ClaudeWork\bo3\bod_port\geo\clip_world.json").read_text())["brushes"]:
        p = b["planes"][:6]
        x0, x1, y0, y1 = -p[0][3], p[1][3], -p[2][3], p[3][3]
        if x1 < x0 or y1 < y0 or min(x1 - x0, y1 - y0) > 4096:  # skip the buried 22k cube
            continue
        cells.update((i, j) for i in range(int(x0 // g), int(x1 // g) + 1) for j in range(int(y0 // g), int(y1 // g) + 1))
    return lambda o: any((int(o[0] // g) + a, int(o[1] // g) + b) in cells for a in (-1, 0, 1) for b in (-1, 0, 1))


pl = json.loads(args.src.read_text())
keep = pl
if args.outside_footprint:
    (x0, y0), (x1, y1) = SHELL_FOOTPRINT
    keep = [p for p in keep if not (x0 <= p["origin"][0] <= x1 and y0 <= p["origin"][1] <= y1)]
if args.box:
    x0, y0, x1, y1 = args.box
    keep = [p for p in keep if x0 <= p["origin"][0] <= x1 and y0 <= p["origin"][1] <= y1]
if args.off_shell:
    over = shell_cells()
    keep = [p for p in keep if not over(p["origin"])]
args.out.write_text(json.dumps(keep))
h = collections.Counter(p["model"] for p in keep)
args.models.write_text("\n".join(sorted(h)) + "\n")
rip = set(os.listdir(RIP))
miss = sorted(m for m in h if m not in rip)
print(f"{len(keep)} of {len(pl)} placements, {len(h)} models, {len(miss)} missing from rip {miss[:10]} -> {args.out}")
for m, c in h.most_common(20):
    print(f"  {c:5d} {m}")
