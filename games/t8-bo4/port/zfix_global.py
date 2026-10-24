"""Cross-chunk z-fight fix: coplanar faces of different materials (from any chunk) in the same local cell get stacked layers.
Local dominant material (by area) stays put; each other material is lifted rank*STEP along its normal."""
import glob, math, os, re, shutil, sys
from collections import defaultdict

SRC = r"F:/ClaudeWork/bo3/bod_port/geo/shell_chunks_clean"
DST = r"F:/ClaudeWork/bo3/bod_port/geo/shell_chunks_zfix2"
STEP, MAXRANK, CELL = 0.4, 6, 256.0
VERT_RE = re.compile(r'^VERT (\d+)\s*\nOFFSET ([-\d.eE]+),\s*([-\d.eE]+),\s*([-\d.eE]+)', re.M)

def load(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    off = {int(m.group(1)): [float(m.group(2)), float(m.group(3)), float(m.group(4))] for m in VERT_RE.finditer(t)}
    mats = re.findall(r'^MATERIAL \d+ "([^"]+)"', t, re.M)
    faces = []
    for blk in re.split(r'^TRI ', t, flags=re.M)[1:]:
        mat = int(blk.split(None, 3)[1])
        vs = [int(x) for x in re.findall(r'^VERT (\d+)', blk, re.M)[:3]]
        if len(vs) == 3: faces.append((mats[mat] if mat < len(mats) else str(mat), vs))
    return t, off, faces

def geom(off, vs):
    a, b, c = (off[v] for v in vs)
    u = [b[i]-a[i] for i in range(3)]; w = [c[i]-a[i] for i in range(3)]
    n = [u[1]*w[2]-u[2]*w[1], u[2]*w[0]-u[0]*w[2], u[0]*w[1]-u[1]*w[0]]
    L = math.sqrt(sum(x*x for x in n))
    if L < 1e-9: return None
    n = [x/L for x in n]; cen = [(a[i]+b[i]+c[i])/3 for i in range(3)]
    return n, sum(n[i]*a[i] for i in range(3)), L/2, cen

FINE = 16.0

def project(off, vs, n):
    # drop the normal's dominant axis to get 2D coords in the plane
    ax = max(range(3), key=lambda i: abs(n[i])); keep = [i for i in range(3) if i != ax]
    return [(off[v][keep[0]], off[v][keep[1]]) for v in vs]

def bbox_cells(tr):
    xs = [p[0] for p in tr]; ys = [p[1] for p in tr]
    for gx in range(int(min(xs)//FINE), int(max(xs)//FINE)+1):
        for gy in range(int(min(ys)//FINE), int(max(ys)//FINE)+1):
            yield (gx, gy)

def cell_of(s): return (int(s[0]//FINE), int(s[1]//FINE))

def samples(tr):
    (ax, ay), (bx, by), (cx, cy) = tr
    out = [((ax+bx+cx)/3, (ay+by+cy)/3)]
    for wa, wb, wc in ((0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6)):
        out.append((wa*ax+wb*bx+wc*cx, wa*ay+wb*by+wc*cy))
    return out

def inside(s, tr):
    (ax, ay), (bx, by), (cx, cy) = tr; px, py = s
    d1 = (px-bx)*(ay-by)-(ax-bx)*(py-by); d2 = (px-cx)*(by-cy)-(bx-cx)*(py-cy); d3 = (px-ax)*(cy-ay)-(cx-ax)*(py-ay)
    return not ((d1 < -1e-6 or d2 < -1e-6 or d3 < -1e-6) and (d1 > 1e-6 or d2 > 1e-6 or d3 > 1e-6))

def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.XMODEL_EXPORT")))
    data = {p: load(p) for p in files}
    groups = defaultdict(list)  # (plane, cell) -> [(file, faceidx, mat, area)]
    info = {}
    for p, (t, off, faces) in data.items():
        for i, (mat, vs) in enumerate(faces):
            g = geom(off, vs)
            if not g: continue
            n, d, area, cen = g
            info[(p, i)] = n
            key = (round(n[0]*20), round(n[1]*20), round(n[2]*20), round(d*4), int(cen[0]//CELL), int(cen[1]//CELL), int(cen[2]//CELL))
            groups[key].append((p, i, mat, area))
    lift = {}  # (file, faceidx) -> distance
    for members in groups.values():
        area = defaultdict(float)
        for _, _, m, a in members: area[m] += a
        if len(area) < 2: continue
        rank = {m: min(r, MAXRANK) for r, m in enumerate(sorted(area, key=lambda m: -area[m]))}
        tri2d = [project(data[p][1], data[p][2][i][1], info[(p, i)]) for p, i, _, _ in members]
        index = defaultdict(list)
        for k, tr in enumerate(tri2d):
            for c in bbox_cells(tr): index[c].append(k)
        for k, (p, i, m, _) in enumerate(members):
            if not rank[m]: continue
            # true overlay only: a sample point of this face lies inside a lower-ranked material's face
            if any(rank[members[j][2]] < rank[m] and inside(s, tri2d[j])
                   for s in samples(tri2d[k]) for j in index[cell_of(s)]):
                lift[(p, i)] = rank[m] * STEP
    os.makedirs(DST, exist_ok=True)
    if os.path.isdir(os.path.join(SRC, "_images")) and not os.path.isdir(os.path.join(DST, "_images")):
        shutil.copytree(os.path.join(SRC, "_images"), os.path.join(DST, "_images"))
    tot = moved = conflicts = 0
    for p, (t, off, faces) in data.items():
        need = defaultdict(set)  # vert -> set of (dx,dy,dz)
        for i, (mat, vs) in enumerate(faces):
            n = info.get((p, i)); k = lift.get((p, i), 0.0)
            vec = (round(n[0]*k, 4), round(n[1]*k, 4), round(n[2]*k, 4)) if n and k else (0.0, 0.0, 0.0)
            for v in vs: need[v].add(vec)
        new = {}
        for v, s in need.items():
            # a vert shared by faces needing different lifts takes the largest (keeps the mesh watertight)
            if len(s) > 1: conflicts += 1
            dx, dy, dz = max(s, key=lambda d: d[0]*d[0]+d[1]*d[1]+d[2]*d[2])
            if dx or dy or dz: new[v] = (off[v][0]+dx, off[v][1]+dy, off[v][2]+dz)
        tot += len(faces); moved += sum(1 for i in range(len(faces)) if (p, i) in lift)
        def repl(m):
            v = int(m.group(1))
            if v not in new: return m.group(0)
            x, y, z = new[v]
            return f"VERT {v}\nOFFSET {x:.6f}, {y:.6f}, {z:.6f}"
        open(os.path.join(DST, os.path.basename(p)), "w", encoding="utf-8").write(VERT_RE.sub(repl, t))
        print(f"{os.path.basename(p)}: verts moved {len(new)}")
    print(f"TOTAL faces {tot}, lifted {moved} ({100*moved/max(tot,1):.1f}%), shared verts given max lift {conflicts}")

if __name__ == "__main__":
    sys.exit(main())
