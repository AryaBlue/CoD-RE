"""Missing floors: unnamed BoD placements shaped like slabs, validated by floor-resting props that float (nothing beneath in the shell)."""
import glob, json, re, sys
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
from door_probe import ray, VERT_RE

SHELL = r"F:\ClaudeWork\bo3\bod_port\geo\shell_chunks_v3"
GAP = r"F:\ClaudeWork\bo3\bod_port\t8_world\geo\bod_rip_gap.json"
CAT = r"F:\ClaudeWork\bo3\bod_port\t8_world\geo\bod_placements_catalog.json"
OUT = r"F:\ClaudeWork\bo3\bod_port\geo\floor_slabs.json"
FLOORISH = re.compile(r"paper|chair|rubble|debris|bed|crate|table|trash|bottle|pallet|box|bucket|mattress|toilet|desk|cabinet|barrel")
CORE = ((-3600, 4300, -600), (11800, 13000, 2700))

def tris():
    out = []
    for p in sorted(glob.glob(SHELL + r"\*.XMODEL_EXPORT")):
        t = open(p, encoding="utf-8", errors="replace").read()
        off = {int(m.group(1)): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in VERT_RE.finditer(t)}
        for blk in re.split(r'^TRI ', t, flags=re.M)[1:]:
            vs = [int(x) for x in re.findall(r'^VERT (\d+)', blk, re.M)[:3]]
            if len(vs) == 3: out.append([off[v] for v in vs])
    return np.array(out)

def inside(p): return all(CORE[0][i] <= p[i] <= CORE[1][i] for i in range(3))

def main():
    T = tris()
    slabs = []
    for g in json.load(open(GAP)):
        sx, sy, sz = g["aabb"]
        if min(sx, sy) >= 24 and sz <= 24 and inside(g["centre"]): slabs.append(g)
    floating = []
    for r in json.load(open(CAT)):
        if not r.get("use") or not FLOORISH.search(r["model"]) or not inside(r["origin"]): continue
        o = np.array(r["origin"], float)
        near = T[(np.abs(T[:, :, 0] - o[0]).min(1) < 300) & (np.abs(T[:, :, 1] - o[1]).min(1) < 300) & (np.abs(T[:, :, 2] - o[2]).min(1) < 300)]
        if ray(near, o + np.array([0, 0, 6.0]), np.array([0, 0, -1.0]), 30) >= 30: floating.append((r["model"], list(o)))
    explained, used = 0, set()
    for m, o in floating:
        for i, g in enumerate(slabs):
            c, a = g["centre"], g["aabb"]
            if abs(o[0] - c[0]) <= a[0] / 2 + 8 and abs(o[1] - c[1]) <= a[1] / 2 + 8 and -12 <= o[2] - (c[2] + a[2] / 2) <= 16:
                explained += 1; used.add(i); break
    print(f"slab-shaped unnamed records {len(slabs)}; floating floor props {len(floating)}; explained by a slab {explained} (slabs used {len(used)})")
    from collections import Counter
    cells = Counter((int(o[0] // 512) * 512, int(o[1] // 512) * 512, int(o[2] // 128) * 128) for _, o in floating)
    print("floating hot spots:", cells.most_common(12))
    json.dump({"slabs": slabs, "floating": floating, "used": sorted(used)}, open(OUT, "w"))

if __name__ == "__main__":
    main()
