"""Player collision for BoD props: BulletCollisionLOD only stops bullets; players need a CollisionMap. Voxelise each solid-ish prop's LOD0 mesh,
merge voxels into boxes, write share\\raw\\collmaps\\<model>.map (clip brushes), set CollisionMap + scaleCollMap in the prop GDTs, and add
use_collmap to their placements in .map.base_bodprops."""
import glob, os, re, sys, uuid
import numpy as np

R = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130"
CM = R + r"\share\raw\collmaps"
GDTS = [R + r"\source_data\bod_props.gdt", R + r"\source_data\bod_props2.gdt"]
BASE = R + r"\map_source\zm\zm_alcatraz_bodfull.map.base_bodprops"
RIP = r"F:\ClaudeWork\bo3\greyhound\app\exported_files\black_ops_4\xmodels"
SOLID = re.compile(r"cell_door|cell_gate|cell_brick_wall|gate|fence|railing|rail_|bars|stair|barricade|bed_|table|desk|locker|generator|teleporter|apc|truck")
SKIP = re.compile(r"decal|fx|paper|book|bottle|can_|wire|chain|cable|light|lamp|foliage|vine|grass|sign|poster|skylight|ceiling|grate|debris|rubble|trash|food|cup|plate|trim|_top|bottom")
VOX, MAXBOX, MINSIZE = 16.0, 8, 24.0

def mesh(name):
    f = glob.glob(os.path.join(RIP, name, "*LOD0*.XMODEL_EXPORT"))
    if not f: return None
    t = open(f[0], encoding="utf-8", errors="replace").read()
    V = {int(m.group(1)): (float(m.group(2)), float(m.group(3)), float(m.group(4)))
         for m in re.finditer(r'^VERT (\d+)\s*\nOFFSET ([-\d.eE]+),\s*([-\d.eE]+),\s*([-\d.eE]+)', t, re.M)}
    T = [[V[int(x)] for x in re.findall(r'^VERT (\d+)', b, re.M)[:3]] for b in re.split(r'^TRI ', t, flags=re.M)[1:]]
    return np.array([x for x in T if len(x) == 3])

def boxes(T, vox):
    lo = T.reshape(-1, 3).min(0)
    pts = []
    for a, b, c in T:
        n = int(max(np.linalg.norm(b - a), np.linalg.norm(c - a), np.linalg.norm(c - b)) / (vox / 2)) + 1
        u, v = np.meshgrid(np.linspace(0, 1, n + 1), np.linspace(0, 1, n + 1)); k = (u + v) <= 1
        pts.append(a + np.outer(u[k], b - a) + np.outer(v[k], c - a))
    idx = np.unique(((np.concatenate(pts) - lo) // vox).astype(int), axis=0)
    occ = set(map(tuple, idx)); out = []
    for p in sorted(occ):
        if p not in occ: continue
        x0, y0, z0 = p; x1 = x0
        while (x1 + 1, y0, z0) in occ: x1 += 1
        y1 = y0
        while all((x, y1 + 1, z0) in occ for x in range(x0, x1 + 1)): y1 += 1
        z1 = z0
        while all((x, y, z1 + 1) in occ for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)): z1 += 1
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1): occ.discard((x, y, z))
        out.append((lo + np.array([x0, y0, z0]) * vox, lo + (np.array([x1, y1, z1]) + 1) * vox))
    return out

def brush(a, b):  # collmaps reject patches, so boxes are brushes and spend the 131,072 plane budget
    (x0, y0, z0), (x1, y1, z1) = a, b
    P = lambda *v: "( " + " ".join(f"{q:.2f}" for q in v) + " )"
    faces = [(P(x1, y1, z0), P(x1, y0, z0), P(x1, y0, z1)), (P(x1, y1, z0), P(x0, y1, z0), P(x0, y0, z0)),
             (P(x1, y0, z1), P(x0, y0, z1), P(x0, y1, z1)), (P(x1, y0, z1), P(x1, y0, z0), P(x0, y0, z0)),
             (P(x0, y1, z1), P(x0, y0, z1), P(x0, y0, z0)), (P(x0, y1, z1), P(x0, y1, z0), P(x1, y1, z0))]
    t = "clip 64 64 0 0 0 0 lightmap_gray 16384 16384 0 0 0 0"
    return "{\n guid \"{" + str(uuid.uuid4()).upper() + "}\"\n" + "".join(f" {p} {q} {r} {t}\n" for p, q, r in faces) + "}\n"

def main():
    done, total = {}, 0
    for g in GDTS:
        t = open(g, encoding="utf-8", errors="replace").read()
        for name in re.findall(r'^\s*"([^"]+)"\s*\(\s*"xmodel\.gdf"', t, re.M):
            if not SOLID.search(name) or SKIP.search(name) or name in done: continue
            T = mesh(name)
            if T is None or len(T) == 0: continue
            ext = T.reshape(-1, 3).max(0) - T.reshape(-1, 3).min(0)
            if ext.max() < MINSIZE: continue
            vox, B = VOX, None
            while vox <= 64:
                B = boxes(T, vox)
                if len(B) <= MAXBOX: break
                vox *= 2
            body = "".join(f"// brush {i}\n" + brush(a, b) for i, (a, b) in enumerate(B))
            open(os.path.join(CM, name + ".map"), "w", newline="\n").write(
                'iwmap 4\n"000_Global" flags  active\n"The Map" flags expanded \n// entity 0\n{\nguid "{' + str(uuid.uuid4()).upper() + '}"\n"classname" "worldspawn"\n' + body + "}\n")
            done[name] = len(B)
    print(f"collmaps {len(done)}; boxes per model max {max(done.values())}")
    for g in GDTS:
        t = open(g, encoding="utf-8", errors="replace").read()
        def fix(m):
            name, b = m.group(1), m.group(2)
            if name not in done: return m.group(0)
            for k, v in (("CollisionMap", name + ".map"), ("scaleCollMap", "1")):
                b = re.sub(rf'"{k}" "[^"]*"', f'"{k}" "{v}"', b) if f'"{k}"' in b else b.rstrip() + f'\n\t\t"{k}" "{v}"\n\t'
            return f'"{name}" ( "xmodel.gdf" )\n\t{{{b}}}'
        t = re.sub(r'"([^"]+)" \( "xmodel\.gdf" \)\s*\{(.*?)\}', fix, t, flags=re.S)
        open(g, "w", encoding="utf-8").write(t)
    b = open(BASE, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in b[:2000] else "\n"
    n = [0]
    def mark(m):
        if m.group(1) in done and '"use_collmap"' not in m.group(0):
            n[0] += 1; total_boxes[0] += done[m.group(1)]
            return m.group(0) + '"use_collmap" "1"' + nl
        if m.group(1) in done: total_boxes[0] += done[m.group(1)]
        return m.group(0)
    total_boxes = [0]
    b = re.sub(r'"model" "([^"]+)"' + nl + r'(?:"origin" "[^"]*"' + nl + r')?', mark, b)
    open(BASE, "w", encoding="utf-8", errors="surrogateescape", newline="").write(b)
    print(f"use_collmap added to {n[0]} placements; collision boxes in map {total_boxes[0]}")

if __name__ == "__main__":
    main()
