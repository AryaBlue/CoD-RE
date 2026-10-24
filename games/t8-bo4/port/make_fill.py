"""Fill skin: invis_floors.json (walkable clip patches) + gap_skin.json (clip inside unripped models) + brush_skin.json (clip brush faces), all
places with collision but no shell surface -> double-sided chunks shell_chunks_v3\\bodgfx_016.. (<=60k verts each), textured like the nearest
shell face of the same orientation. Then import bodisland; --place adds the misc_models + zone lines."""
import glob, json, os, re, sys, uuid
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(__file__))
from shell_texfix import load

GEO = r"F:\ClaudeWork\bo3\bod_port\geo"
SHELL = GEO + r"\shell_chunks_v3"
R = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130"
BASE = R + r"\map_source\zm\zm_alcatraz_bodfull.map.base_bodprops"
ZONE = R + r"\usermaps\zm_alcatraz_bodfull\zone_source\zm_alcatraz_bodfull.zone"
FIRST, PER_CHUNK = 16, 19999
MAX_AREA, UVS = 1e4, 1 / 128.0

def chunk_name(i): return f"bodgfx_{FIRST + i:03d}"

def write_chunk(path, T, pick, blocks):
    used = sorted(set(pick)); mi = {m: i for i, m in enumerate(used)}
    V = [tuple(v) for t in T for v in t]
    L = ["// bod_port fill skin (make_fill.py)", "MODEL", "VERSION 6", "", "NUMBONES 1", 'BONE 0 -1 "tag_origin"', "", "BONE 0",
         "OFFSET 0.000000, 0.000000, 0.000000", "SCALE 1.000000, 1.000000, 1.000000", "X 1.000000, 0.000000, 0.000000",
         "Y 0.000000, 1.000000, 0.000000", "Z 0.000000, 0.000000, 1.000000", "", f"NUMVERTS {len(V)}"]
    for i, v in enumerate(V):
        L += [f"VERT {i}", f"OFFSET {v[0]:.6f}, {v[1]:.6f}, {v[2]:.6f}", "BONES 1", "BONE 0 1.000000", ""]
    L.append(f"NUMFACES {2 * len(T)}")
    for k, m in enumerate(pick):
        b = 3 * k; P = np.array(V[b:b + 3]); fn = np.abs(np.cross(P[1] - P[0], P[2] - P[0]))
        ax = {2: (0, 1), 1: (0, 2), 0: (1, 2)}[int(fn.argmax())]  # planar projection on the dominant axis
        for vs in ((b, b + 1, b + 2), (b, b + 2, b + 1)):  # both windings: double-sided
            L.append(f"TRI 0 {mi[m]} 0 0")
            for v in vs:
                p = V[v]
                L += [f"VERT {v}", "NORMAL 0.000000 0.000000 1.000000", "COLOR 1.000000 1.000000 1.000000 1.000000", f"UV 1 {p[ax[0]] * UVS:.6f} {-p[ax[1]] * UVS:.6f}"]
    L += ["", "NUMOBJECTS 1", 'OBJECT 0 "world_mesh"', "", f"NUMMATERIALS {len(used)}"]
    out = "\n".join(L) + "\n" + "".join(f'MATERIAL {i} "{m}"' + blocks[m].rstrip("\n") + "\n" for i, m in enumerate(used))
    open(path, "w", encoding="utf-8", newline="\n").write(out)

def build():
    T = np.array(json.load(open(GEO + r"\invis_floors.json"))["tris"]).reshape(-1, 3, 3)
    a = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    parts = [T[a < MAX_AREA]]
    for f in ("gap_skin", "brush_skin"):
        if os.path.exists(GEO + rf"\{f}.json"): parts.append(np.array(json.load(open(GEO + rf"\{f}.json"))["tris"]).reshape(-1, 3, 3))
    T = np.unique(np.concatenate(parts).round(1), axis=0)
    faces, blocks = [], {}
    for p in sorted(glob.glob(SHELL + r"\bodgfx_0*_LOD0.XMODEL_EXPORT")):
        if int(re.search(r"bodgfx_(\d+)", p).group(1)) >= FIRST: continue
        faces += load(p)
        t = open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'^MATERIAL \d+ "([^"]+)"(.*?)(?=^MATERIAL |\Z)', t, re.M | re.S):
            blocks.setdefault(m.group(1), m.group(2))
    S = np.array([f[1] for f in faces]); mats = np.array([f[0] for f in faces])
    n = np.cross(S[:, 1] - S[:, 0], S[:, 2] - S[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    alpha = set(json.load(open(GEO + r"\shell_alpha_mats.json")))
    bad = np.array(["decal" in m or "caulk" in m or "blackness" in m or m in alpha for m in mats])
    flat = np.abs(n[:, 2]) > 0.7
    W = np.array([1, 1, 3.0])
    trees = {f: (cKDTree(S[(flat == f) & ~bad].mean(1) * W), mats[(flat == f) & ~bad]) for f in (True, False)}
    tn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); tf = np.abs(tn[:, 2]) > 0.7 * np.linalg.norm(tn, axis=1)
    pick = np.empty(len(T), dtype=object)
    for f in (True, False):
        tree, mm = trees[f]
        _, idx = tree.query(T[tf == f].mean(1) * W)
        pick[tf == f] = mm[idx]
    for old in glob.glob(SHELL + r"\bodgfx_0*_LOD0.XMODEL_EXPORT"):  # retire fill chunks from a previous run
        if int(re.search(r"bodgfx_(\d+)", old).group(1)) >= FIRST: os.replace(old, old + ".old")
    n = 0
    for i in range(0, len(T), PER_CHUNK):
        write_chunk(SHELL + rf"\{chunk_name(n)}_LOD0.XMODEL_EXPORT", T[i:i + PER_CHUNK], list(pick[i:i + PER_CHUNK]), blocks); n += 1
    json.dump(n, open(GEO + r"\fill_chunks.json", "w"))
    from collections import Counter
    print(f"fill tris {len(T)} in {n} chunks; materials {Counter(pick).most_common(6)}")

def place():
    n = json.load(open(GEO + r"\fill_chunks.json"))
    b = open(BASE, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in b[:2000] else "\n"
    b = re.sub(r"// entity bodfill \d+\r?\n\{.*?\r?\n\}\r?\n", "", b, flags=re.S)
    ents = [nl.join([f"// entity bodfill {i}", "{", 'guid "{' + str(uuid.uuid4()).upper() + '}"', '"classname" "misc_model"', f'"model" "{chunk_name(i)}"',
                     '"origin" "0 0 0"', '"angles" "0 0 0"', '"modelscale" "1"', '"static" "1"'] + [f'"lightingstate{k}" "1"' for k in range(1, 5)] + ["}"]) for i in range(n)]
    open(BASE, "w", encoding="utf-8", errors="surrogateescape", newline="").write(b.rstrip("\r\n") + nl + nl.join(ents) + nl)
    z = [l for l in open(ZONE, encoding="utf-8").read().splitlines() if not (re.match(r"xmodel,bodgfx_(\d+)$", l) and int(l[14:]) >= FIRST)]
    z += [f"xmodel,{chunk_name(i)}" for i in range(n)]
    open(ZONE, "w", encoding="utf-8").write("\n".join(z) + "\n")
    print(f"placed {n} fill chunks")

if __name__ == "__main__":
    place() if "--place" in sys.argv else build()
