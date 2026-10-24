"""Stairs/rubble/rock collision lives in worldspawn CLIP BRUSHES (invis_floors only read patches). Polygonise every full-clip brush, cut faces
into small tris, keep the pieces with no shell surface on them -> geo\\brush_skin.json (make_fill merges it).
clip_player/clip_ai are deliberate invisible walls, so they're left out."""
import itertools, json, re, sys, collections
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
from door_probe import ray
from floor_gaps import tris
from invis_floors import binned, BOX, BIN, MAP

OUT = r"F:\ClaudeWork\bo3\bod_port\geo\brush_skin.json"
MATS = {"clip"}
TOL, PIECE, MAX_FACE = 6.0, 3000.0, 4e6

def brushes():
    t = open(MAP, encoding="utf-8", errors="surrogateescape").read()
    t = t[:t.index("\n// entity 1\n")]
    num = r"(-?[\d.eE+-]+)"
    face = re.compile(r"^ \( " + " ".join([num] * 3) + r" \) \( " + " ".join([num] * 3) + r" \) \( " + " ".join([num] * 3) + r" \) (\S+) ", re.M)
    for blk in re.split(r"\n// brush [^\n]*\n", t)[1:]:
        f = face.findall(blk.split("\n}", 1)[0])
        if len(f) >= 4 and all(x[9] in MATS for x in f):
            yield np.array([[float(v) for v in x[:9]] for x in f]).reshape(-1, 3, 3)

def polys(P):
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True)
    d = (n * P[:, 0]).sum(1)
    pts = []
    for i, j, k in itertools.combinations(range(len(n)), 3):
        A = n[[i, j, k]]
        if abs(np.linalg.det(A)) < 1e-6: continue
        pts.append(np.linalg.solve(A, d[[i, j, k]]))
    if not pts: return []
    pts = np.array(pts); s = pts @ n.T - d
    for sign in (1, -1):  # winding convention decides which side is inside
        ok = pts[np.all(sign * s <= 0.05, axis=1)]
        if len(ok) >= 4: break
    else: return []
    ok = np.unique(ok.round(2), axis=0); c = ok.mean(0); out = []
    for i in range(len(n)):
        on = ok[np.abs(ok @ n[i] - d[i]) < 0.05]
        if len(on) < 3: continue
        u = on[1] - on[0]; u /= np.linalg.norm(u); v = np.cross(n[i], u)
        fc = on.mean(0); ang = np.arctan2((on - fc) @ v, (on - fc) @ u)
        out.append(on[np.argsort(ang)])
    return out

def split(t):
    a = np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) / 2
    if a <= PIECE: return [t]
    m = [(t[0] + t[1]) / 2, (t[1] + t[2]) / 2, (t[2] + t[0]) / 2]
    return [s for q in ((t[0], m[0], m[2]), (m[0], t[1], m[1]), (m[2], m[1], t[2]), (m[0], m[1], m[2])) for s in split(np.array(q))]

CELL = 64.0

def shell():
    import glob
    from shell_texfix import load
    G = r"F:\ClaudeWork\bo3\bod_port\geo\shell_chunks_v3"
    return np.array([t for p in sorted(glob.glob(G + r"\bodgfx_0*_LOD0.XMODEL_EXPORT")) if int(p[-22:-19]) < 16 for _, t in load(p)])  # no fill chunks

def grid(S):
    # every shell tri goes in each xy cell its AABB overlaps
    lo = np.floor(S[:, :, :2].min(1) / CELL).astype(int); hi = np.floor(S[:, :, :2].max(1) / CELL).astype(int)
    g = collections.defaultdict(list)
    for i in range(len(S)):
        for x in range(lo[i, 0], hi[i, 0] + 1):
            for y in range(lo[i, 1], hi[i, 1] + 1): g[(x, y)].append(i)
    return g

def covered(S, C, N):
    # segment C-N*TOL .. C+N*TOL vs all tris S, per piece: any hit
    o = C[:, None] - N[:, None] * TOL; d = N[:, None] * (2 * TOL)
    v0, e1, e2 = S[None, :, 0], S[None, :, 1] - S[None, :, 0], S[None, :, 2] - S[None, :, 0]
    p = np.cross(d, e2); det = (e1 * p).sum(-1); ok = np.abs(det) > 1e-9; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = o - v0; u = (s * p).sum(-1) * inv; q = np.cross(s, e1); v = (q * d).sum(-1) * inv; t = (q * e2).sum(-1) * inv
    return (ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)).any(1)

def main():
    import time; t0 = time.time()
    pieces, nb = [], 0
    for P in brushes():
        nb += 1
        for poly in polys(P):
            c = poly.mean(0)
            if not all(BOX[0][i] <= c[i] <= BOX[1][i] for i in range(3)): continue
            for k in range(1, len(poly) - 1):
                t = np.array([poly[0], poly[k], poly[k + 1]])
                if np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) / 2 > MAX_FACE: continue
                pieces += split(t)
    T = np.array(pieces); n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); L = np.linalg.norm(n, axis=1)
    T, N = T[L > 1e-6], n[L > 1e-6] / L[L > 1e-6, None]; C = T.mean(1)
    print("clip brushes", nb, "pieces", len(T), f"{time.time() - t0:.0f}s", flush=True)
    S = shell(); g = grid(S)
    print("shell tris", len(S), f"{time.time() - t0:.0f}s", flush=True)
    cell = collections.defaultdict(list)
    for i, k in enumerate(zip((C[:, 0] // CELL).astype(int), (C[:, 1] // CELL).astype(int))): cell[k].append(i)
    hit = np.zeros(len(T), bool)
    for k, ix in cell.items():
        sx = g.get(k)
        if not sx: continue
        ix = np.array(ix); Sk = S[sx]
        Sk = Sk[(Sk[:, :, 2].min(1) <= C[ix, 2].max() + TOL) & (Sk[:, :, 2].max(1) >= C[ix, 2].min() - TOL)]
        for j in range(0, len(ix), 256):
            b = ix[j:j + 256]
            for m in range(0, len(Sk), 2048): hit[b] |= covered(Sk[m:m + 2048], C[b], N[b])
    K = T[~hit]
    print(f"{time.time() - t0:.0f}s", flush=True)
    cen = K.mean(1)
    cl = collections.Counter((int(x // 512) * 512, int(y // 512) * 512) for x, y, _ in cen)
    print(f"uncovered pieces {len(K)}; hot cells {cl.most_common(8)}")
    json.dump({"tris": K.round(2).tolist()}, open(OUT, "w"))

if __name__ == "__main__":
    main()
