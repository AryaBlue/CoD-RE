"""Face-aware spawn finder: a wall is a few verts spanning metres, so vert-counting misses it.
Test a standing column at each candidate floor point against render TRIANGLES: a triangle blocks
if the point (x,y) is inside its 2D projection AND its interpolated Z sits in the body column.
Candidates = nav seeds (guaranteed-walkable floor) near the original spawn. Pick the nearest clear one."""
import json, math

OBJ  = r"F:\ClaudeWork\c2m\app2\exported_maps\black_ops_4\zm_escape\zm_escape.obj"
SEEDS = r"F:\ClaudeWork\bo3\bod_port\t8_world\nav\bod_nav_seeds.json"
ORIG = (886.0, 10570.0, 1376.0)
NEAR = 1e9              # consider all seeds; sort by distance to orig, pick nearest clear
BODY = (12.0, 76.0)     # standing column: floor+12 .. floor+76 (player ~70u tall)
RAD  = 18.0             # player half-width; a triangle within this of the column also blocks
TRI_NEAR = 300.0        # only consider triangles whose verts are within this of a candidate XY

def load_verts(path):
    vs = [None]
    with open(path, errors="replace") as f:
        for ln in f:
            if ln[:2] == "v ":
                p = ln.split()
                vs.append((float(p[1]), float(p[2]), float(p[3])))
    return vs

def load_tris(path):
    tris = []
    with open(path, errors="replace") as f:
        for ln in f:
            if ln[:2] == "f ":
                idx = [int(c.split("/")[0]) for c in ln.split()[1:]]
                for i in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[i], idx[i + 1]))
    return tris

def pt_in_tri2d(px, py, a, b, c):
    d1 = (px - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (py - b[1])
    d2 = (px - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (py - c[1])
    d3 = (px - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (py - a[1])
    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (neg and pos)

def z_at(px, py, a, b, c):
    v0x, v0y = b[0]-a[0], b[1]-a[1]
    v1x, v1y = c[0]-a[0], c[1]-a[1]
    v2x, v2y = px-a[0], py-a[1]
    den = v0x*v1y - v1x*v0y
    if abs(den) < 1e-6: return None
    v = (v2x*v1y - v1x*v2y)/den
    w = (v0x*v2y - v2x*v0y)/den
    u = 1-v-w
    return u*a[2] + v*b[2] + w*c[2]

print("loading verts...")
V = load_verts(OBJ)
print(f"  {len(V)-1} verts")
print("loading tris...")
T = load_tris(OBJ)
print(f"  {len(T)} tris")

# spatial hash of triangles by XY cell for O(1) column lookup
ox, oy = ORIG[0], ORIG[1]
CELL = 64.0
grid = {}
def cells_for(x0, y0, x1, y1):
    for gx in range(int(x0//CELL), int(x1//CELL)+1):
        for gy in range(int(y0//CELL), int(y1//CELL)+1):
            yield (gx, gy)
print("building triangle grid...")
for (ia, ib, ic) in T:
    a, b, c = V[ia], V[ib], V[ic]
    x0, x1 = min(a[0],b[0],c[0]), max(a[0],b[0],c[0])
    y0, y1 = min(a[1],b[1],c[1]), max(a[1],b[1],c[1])
    tri = (a, b, c)
    for cell in cells_for(x0, y0, x1, y1):
        grid.setdefault(cell, []).append(tri)
print(f"  {len(grid)} cells")

seeds = json.load(open(SEEDS))
if isinstance(seeds, dict): seeds = seeds.get("points") or seeds.get("seeds") or []
cands = []
for s in seeds:
    o = s["origin"] if isinstance(s, dict) and "origin" in s else s
    x, y, z = (o[0], o[1], o[2]) if isinstance(o, (list, tuple)) else (o["x"], o["y"], o["z"])
    if abs(x-ox) <= NEAR and abs(y-oy) <= NEAR:
        cands.append((x, y, z))
cands.sort(key=lambda p: (p[0]-ox)**2 + (p[1]-oy)**2)
print(f"  {len(cands)} seed candidates in radius")

def blocked(x, y, floor):
    lo, hi = floor+BODY[0], floor+BODY[1]
    seen = set()
    for cell in cells_for(x-RAD, y-RAD, x+RAD, y+RAD):
        for tri in grid.get(cell, ()):
            if id(tri) in seen: continue
            seen.add(id(tri))
            a, b, c = tri
            if max(a[2],b[2],c[2]) < lo or min(a[2],b[2],c[2]) > hi: continue
            for (sx, sy) in ((x,y),(x+RAD,y),(x-RAD,y),(x,y+RAD),(x,y-RAD)):
                if pt_in_tri2d(sx, sy, a, b, c):
                    z = z_at(sx, sy, a, b, c)
                    if z is not None and lo <= z <= hi:
                        return True
    return False

print("scanning candidates for a clear standing column...")
found = None
checked = 0
for (x, y, z) in cands:
    checked += 1
    if not blocked(x, y, z):
        found = (x, y, z)
        break
    if checked % 50 == 0:
        print(f"  checked {checked}, nearest-clear not yet found")

if found:
    d = math.dist(found, ORIG)
    print(f"\nCLEAR SPAWN: {found[0]:.0f} {found[1]:.0f} {found[2]:.0f}  ({d:.0f}u from orig, checked {checked})")
else:
    print(f"\nno clear seed in radius (checked {checked}) - widen NEAR or lift Z")
