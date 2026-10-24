"""Measure doorway openings at BoD door spots by raycasting the shell: narrowest opposite-ray pair = door width, perpendicular = passage."""
import glob, json, math, re, sys
import numpy as np

SHELL = r"F:\ClaudeWork\bo3\bod_port\geo\shell_chunks_zfix2"
VERT_RE = re.compile(r'^VERT (\d+)\s*\nOFFSET ([-\d.eE]+),\s*([-\d.eE]+),\s*([-\d.eE]+)', re.M)

def load_tris():
    tris = []
    for p in sorted(glob.glob(SHELL + r"\*.XMODEL_EXPORT")):
        t = open(p, encoding="utf-8", errors="replace").read()
        off = {int(m.group(1)): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in VERT_RE.finditer(t)}
        for blk in re.split(r'^TRI ', t, flags=re.M)[1:]:
            vs = [int(x) for x in re.findall(r'^VERT (\d+)', blk, re.M)[:3]]
            if len(vs) == 3: tris.append([off[v] for v in vs])
    return np.array(tris, dtype=np.float64)

def ray(T, o, d, far=2000.0):
    # Möller–Trumbore against all tris, double-sided
    v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    p = np.cross(d, e2); det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-9; inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
    s = o - v0; u = (s * p).sum(1) * inv
    q = np.cross(s, e1); v = (q * d).sum(1) * inv; t = (q * e2).sum(1) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.5) & (t < far)
    return float(t[hit].min()) if hit.any() else far

def probe(T, o):
    o = np.array(o, dtype=np.float64)
    near = T[(np.abs(T[:, :, 0] - o[0]).min(1) < 1500) & (np.abs(T[:, :, 1] - o[1]).min(1) < 1500) & (np.abs(T[:, :, 2] - o[2]).min(1) < 800)]
    best = None
    for a in range(0, 180, 10):
        d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0])
        w1, w2 = ray(near, o, d), ray(near, o, -d)
        if best is None or w1 + w2 < best[0]: best = (w1 + w2, a, w1, w2)
    w, a, w1, w2 = best
    d = np.array([math.cos(math.radians(a)), math.sin(math.radians(a)), 0.0])
    centre = o + d * (w1 - w2) / 2
    floor = ray(near, centre, np.array([0, 0, -1.0]), 400); ceil = ray(near, centre, np.array([0, 0, 1.0]), 600)
    return {"width": round(w), "across_yaw": a, "centre": [round(c) for c in centre], "floor_z": round(centre[2] - floor), "height": round(floor + ceil)}

if __name__ == "__main__":
    T = load_tris()
    print("tris", len(T))
    pts = json.loads(sys.argv[1])
    for name, o in pts.items(): print(name, probe(T, o))
