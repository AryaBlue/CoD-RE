"""Invisible floors/stairs: walkable BoD clip surfaces (worldspawn clip patches) with no visible shell or prop surface on them -> geo\\invis_floors.json."""
import json, re, sys, collections
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
from door_probe import ray
from floor_gaps import tris

MAP = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\map_source\zm\zm_alcatraz_bodfull.map"
CAT = r"F:\ClaudeWork\bo3\bod_port\t8_world\geo\bod_placements_catalog.json"
BOUNDS = r"F:\ClaudeWork\bo4_recon\rip_bounds.json"
OUT = r"F:\ClaudeWork\bo3\bod_port\geo\invis_floors.json"
BOX = ((-3584, 4352, -512), (11776, 12928, 2688))
BIN, TOL, PAD = 128.0, 8.0, 4.0

def clip_tris():
    t = open(MAP, encoding="utf-8", errors="surrogateescape").read()
    t = t[:t.index("\n// entity 1\n")]
    out = []
    for m in re.finditer(r"\n   clip\n   lightmap_gray\n   2 2 0 8\n   \(\n(.*?)   \)\n   \(\n(.*?)   \)\n", t, re.S):
        r0 = [tuple(map(float, l.split()[1:4])) for l in m.group(1).strip().splitlines()]
        r1 = [tuple(map(float, l.split()[1:4])) for l in m.group(2).strip().splitlines()]
        for a, b, c in ((r0[0], r0[1], r1[0]), (r0[1], r1[1], r1[0])):
            out.append((a, b, c))
    return np.array(out)

def binned(T):
    cen = T.mean(1); bins = collections.defaultdict(list)
    for i, k in enumerate(zip((cen[:, 0] // BIN).astype(int), (cen[:, 1] // BIN).astype(int))): bins[k].append(i)
    return bins

def main():
    S = tris(); sb = binned(S)
    C = clip_tris()
    n = np.cross(C[:, 1] - C[:, 0], C[:, 2] - C[:, 0]); area = np.linalg.norm(n, axis=1) / 2
    nz = np.abs(n[:, 2]) / np.maximum(np.linalg.norm(n, axis=1), 1e-9)
    cen = C.mean(1)
    inbox = np.all((cen >= BOX[0]) & (cen <= BOX[1]), axis=1)
    walk = np.nonzero((nz > 0.7) & (area > 16) & inbox)[0]
    print("clip tris", len(C), "walkable in box", len(walk))
    B = json.load(open(BOUNDS))
    props = []
    for r in json.load(open(CAT)):
        if r.get("use") and r["model"] in B:
            lo, hi = np.array(B[r["model"]][0]), np.array(B[r["model"]][1])
            props.append((np.array(r["origin"]), np.array(r["axis"], float).reshape(3, 3), r.get("scale", 1) or 1, lo - PAD, hi + PAD))
    pb = collections.defaultdict(list)
    for i, p in enumerate(props):
        rad = np.abs(np.concatenate([p[3], p[4]])).max() * p[2] * 1.8
        for bx in range(int((p[0][0] - rad) // BIN), int((p[0][0] + rad) // BIN) + 1):
            for by in range(int((p[0][1] - rad) // BIN), int((p[0][1] + rad) // BIN) + 1): pb[(bx, by)].append(i)
    bad = []
    for i in walk:
        c = cen[i]; k = (int(c[0] // BIN), int(c[1] // BIN))
        idx = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in sb.get((k[0] + dx, k[1] + dy), ())]
        Tn = S[idx] if idx else np.zeros((0, 3, 3))
        if len(Tn) and min(ray(Tn, c + [0, 0, TOL], np.array([0, 0, -1.0]), 2 * TOL), ray(Tn, c - [0, 0, TOL], np.array([0, 0, 1.0]), 2 * TOL)) < 2 * TOL: continue
        if any(np.all((l := (p[1] @ (c - p[0])) / p[2]) >= p[3]) and np.all(l <= p[4]) for p in (props[j] for j in pb.get(k, ()))): continue
        bad.append(int(i))
    tot = area[bad].sum()
    cl = collections.Counter()
    for i in bad: cl[(int(cen[i][0] // 256) * 256, int(cen[i][1] // 256) * 256, int(cen[i][2] // 64) * 64)] += area[i]
    print(f"uncovered walkable clip tris {len(bad)} ({tot / 1e4:.1f} x 100u^2)")
    for k, v in cl.most_common(25): print(" ", k, round(v))
    json.dump({"tris": C[bad].round(2).tolist()}, open(OUT, "w"))

if __name__ == "__main__":
    main()
