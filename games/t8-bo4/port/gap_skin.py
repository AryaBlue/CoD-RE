"""Unripped BoD models (bod_rip_gap.json: size + position only) still have their collision in the clip map: skin every clip tri inside a gap
record's box that has no shell surface on it -> geo\\gap_skin.json (make_fill merges it with invis_floors.json)."""
import json, sys, collections
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
from door_probe import ray
from floor_gaps import tris
from invis_floors import clip_tris, binned, BOX, BIN

GAP = r"F:\ClaudeWork\bo3\bod_port\t8_world\geo\bod_rip_gap.json"
OUT = r"F:\ClaudeWork\bo3\bod_port\geo\gap_skin.json"
PAD, TOL, MAX_AREA = 8.0, 6.0, 2e4

def main():
    S = tris(); sb = binned(S)
    C = clip_tris()
    n = np.cross(C[:, 1] - C[:, 0], C[:, 2] - C[:, 0]); L = np.linalg.norm(n, axis=1); area = L / 2
    n = n / np.maximum(L, 1e-9)[:, None]; cen = C.mean(1)
    G = [g for g in json.load(open(GAP)) if all(BOX[0][i] <= g["centre"][i] <= BOX[1][i] for i in range(3))]
    lo = np.array([np.array(g["centre"]) - np.array(g["aabb"]) / 2 - PAD for g in G]); hi = np.array([np.array(g["centre"]) + np.array(g["aabb"]) / 2 + PAD for g in G])
    inside = np.zeros(len(C), bool)
    for a, b in zip(lo, hi):
        inside |= np.all((cen >= a) & (cen <= b), axis=1)
    cand = np.nonzero(inside & (area > 4) & (area < MAX_AREA))[0]
    print("gap records", len(G), "clip tris inside them", len(cand))
    keep = []
    for i in cand:
        c = cen[i]; k = (int(c[0] // BIN), int(c[1] // BIN))
        idx = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in sb.get((k[0] + dx, k[1] + dy), ())]
        if idx:
            Tn = S[idx]
            if min(ray(Tn, c + n[i] * TOL, -n[i], 2 * TOL), ray(Tn, c - n[i] * TOL, n[i], 2 * TOL)) < 2 * TOL: continue
        keep.append(int(i))
    cl = collections.Counter((int(cen[i][0] // 512) * 512, int(cen[i][1] // 512) * 512) for i in keep)
    print(f"skin tris {len(keep)} ({area[keep].sum() / 1e4:.0f} x 100u^2); hot cells {cl.most_common(8)}")
    json.dump({"tris": C[keep].round(2).tolist()}, open(OUT, "w"))

if __name__ == "__main__":
    main()
