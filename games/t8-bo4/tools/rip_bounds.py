"""Local-space LOD0 vertex AABB of every Greyhound BoD rip model -> rip_bounds.json {model: [min3, max3, numverts]}.
Usage (64-bit Python): rip_bounds.py [rip_xmodels_dir] [out.json]"""
import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

RIP = Path(r"PATH/TO/exported_xmodels")  # set this to your own path
OUT = Path(r"PATH/TO/rip_bounds.json")  # set this to your own path
OFFSET = re.compile(rb"^OFFSET (\S+), (\S+), (\S+)", re.M)


def bounds(folder):
    xme = next(folder.glob("*_LOD0.XMODEL_EXPORT"), None)
    if xme is None:
        return folder.name, None
    text = xme.read_bytes()
    start = text.find(b"\nNUMVERTS ")
    end = text.find(b"\nNUMFACES ", start)
    if start < 0 or end < 0:
        return folder.name, None
    pts = [tuple(map(float, m)) for m in OFFSET.findall(text, start, end)]
    if not pts:
        return folder.name, None
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return folder.name, [lo, hi, len(pts)]


if __name__ == "__main__":
    rip = Path(sys.argv[1]) if len(sys.argv) > 1 else RIP
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    folders = [p for p in rip.iterdir() if p.is_dir()]
    with Pool() as pool:
        results = pool.map(bounds, folders, chunksize=16)
    table = {name: b for name, b in results if b}
    out.write_text(json.dumps(table))
    print(f"{len(table)} of {len(folders)} models bounded; {len(folders) - len(table)} without a readable LOD0 -> {out}")
