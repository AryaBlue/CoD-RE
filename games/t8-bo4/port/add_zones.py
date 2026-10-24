"""Give zm_alcatraz_bodfull real zones: one info_volume per BoD spawner anchor + walkable spawn points, start zone at the spawn room, adjacency into the map GSC.
Replaces the template giant start_zone and its spawners. Writes <map>.bak_prezones once."""
import json, math, os, re, shutil, sys, uuid

TOOLS = r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130"
MAP = TOOLS + r"\map_source\zm\zm_alcatraz_bodfull.map"
GSC = TOOLS + r"\usermaps\zm_alcatraz_bodfull\scripts\zm\zm_alcatraz_bodfull.gsc"
ENTS = r"F:\ClaudeWork\bo4_recon\entities.json"
SEEDS = r"F:\ClaudeWork\bo3\bod_port\t8_world\nav\bod_nav_seeds.json"
START = (9727.0, 11136.0, 264.0)
PER_ZONE, MIN_GAP = 4, 140.0
BOX, CELL, CELLZ, ZW = ((-3584, 4352, -512), (11776, 12928, 2688)), 512.0, 128.0, 3.0

def guid(): return "{" + str(uuid.uuid4()).upper() + "}"

def box_brush(x0, y0, z0, x1, y1, z1):
    t = "volume 64 64 0 0 0 0 lightmap_gray 16384 16384 0 0 0 0"
    P = lambda *a: "( " + " ".join(f"{v:g}" for v in a) + " )"
    faces = [(P(x1, y1, z0), P(x1, y0, z0), P(x1, y0, z1)), (P(x1, y1, z0), P(x0, y1, z0), P(x0, y0, z0)),
             (P(x1, y0, z1), P(x0, y0, z1), P(x0, y1, z1)), (P(x1, y0, z1), P(x1, y0, z0), P(x0, y0, z0)),
             (P(x0, y1, z1), P(x0, y0, z1), P(x0, y0, z0)), (P(x0, y1, z1), P(x0, y1, z0), P(x1, y1, z0))]
    return "// brush 0\n{\n guid \"" + guid() + "\"\n" + "".join(f" {a} {b} {c} {t}\n" for a, b, c in faces) + "}\n"

def ent(kv, brushes=""):
    return "{" + chr(10) + 'guid "' + guid() + '"' + chr(10) + "".join(f'"{k}" "{v}"' + chr(10) for k, v in kv.items()) + brushes + "}" + chr(10)

def zone_name(t):
    n = re.sub(r"_?spawners?$", "", t); n = re.sub(r"^spawner_", "", n)
    return n if n.startswith("zone_") else "zone_" + n

def anchors():
    out = {}
    for e in json.load(open(ENTS)):
        t = e.get("targetname")
        if isinstance(t, str) and re.search(r"spawner", t) and e.get("classname") == "script_struct":
            out.setdefault(zone_name(t), e["origin"])
    out["start_zone"] = list(START)
    return out

def pick_spawns(c, seeds, n=PER_ZONE):
    near = sorted((s for s in seeds if 100 < math.dist(s[:2], c[:2]) < 700 and abs(s[2] - c[2]) < 120), key=lambda s: math.dist(s, c))
    got = []
    for s in near:
        if all(math.dist(s, g) >= MIN_GAP for g in got): got.append(s)
        if len(got) == n: break
    return got

def main():
    if not os.path.exists(MAP + ".bak_prezones"): shutil.copy(MAP, MAP + ".bak_prezones")
    if not os.path.exists(GSC + ".bak_prezones"): shutil.copy(GSC, GSC + ".bak_prezones")
    seeds = [tuple(s["origin"]) for s in json.load(open(SEEDS))]
    A = anchors()
    names = sorted(A)
    base = MAP + ".base_bodprops" if os.path.exists(MAP + ".base_bodprops") else MAP + ".bak_prezones"
    t = open(base, encoding="utf-8", errors="surrogateescape", newline="").read()
    nl = "\r\n" if "\r\n" in t[:2000] else "\n"
    t = t.replace("\r\n", "\n")
    # drop the template zone volume and its spawners
    ents = re.split(r"(?=^// entity \d+\n)", t, flags=re.M)
    keep = [e for e in ents if not re.search(r'"targetname" "start_zone(_spawners)?"', e)]
    dropped = len(ents) - len(keep)
    out, zones, adj = [], {}, set()
    for z in names:
        sp = pick_spawns(A[z], seeds)
        if not sp: print("no walkable seeds near", z); continue
        zones[z] = sp
    # tile the playable box: each cell goes to the nearest zone anchor (height weighted so floors stay apart)
    cells, owner = {}, {}
    zs = list(zones)
    for ix in range(int((BOX[1][0] - BOX[0][0]) // CELL)):
        for iy in range(int((BOX[1][1] - BOX[0][1]) // CELL)):
            for iz in range(int((BOX[1][2] - BOX[0][2]) // CELLZ)):
                c = (BOX[0][0] + (ix + .5) * CELL, BOX[0][1] + (iy + .5) * CELL, BOX[0][2] + (iz + .5) * CELLZ)
                owner[(ix, iy, iz)] = min(zs, key=lambda z: (A[z][0] - c[0]) ** 2 + (A[z][1] - c[1]) ** 2 + (ZW * (A[z][2] - c[2])) ** 2)
    for (ix, iy, iz), z in owner.items():
        for n in ((ix + 1, iy, iz), (ix, iy + 1, iz), (ix, iy, iz + 1)):
            if n in owner and owner[n] != z: adj.add(tuple(sorted((z, owner[n]))))
    # merge vertical runs per column into one brush
    brushes = {z: [] for z in zs}
    for (ix, iy, iz), z in sorted(owner.items()):
        if iz and owner.get((ix, iy, iz - 1)) == z: continue
        top = iz
        while owner.get((ix, iy, top + 1)) == z: top += 1
        x0, y0 = BOX[0][0] + ix * CELL, BOX[0][1] + iy * CELL
        brushes[z].append(box_brush(x0, y0, BOX[0][2] + iz * CELLZ, x0 + CELL, y0 + CELL, BOX[0][2] + (top + 1) * CELLZ))
    for z in zs:
        out.append(ent({"classname": "info_volume", "script_noteworthy": "player_volume", "target": z + "_spawners", "targetname": z}, "".join(brushes[z])))
        for s in zones[z]:
            out.append(ent({"classname": "script_struct", "origin": f"{s[0]:.0f} {s[1]:.0f} {s[2] + 4:.0f}", "angles": "0 0 0",
                            "script_noteworthy": "spawn_location", "script_string": "find_flesh", "targetname": z + "_spawners"}))
    print("brushes", sum(len(b) for b in brushes.values()))
    body = "".join(keep).rstrip("\n") + "\n" + "".join(f"// entity bodzone {i}\n{e}" for i, e in enumerate(out))
    open(MAP, "w", encoding="utf-8", errors="surrogateescape", newline="").write(body.replace("\n", nl))
    g = open(GSC + ".bak_prezones", encoding="utf-8").read()
    lines = "".join(f'\tzm_zonemgr::add_adjacent_zone( "{a}", "{b}", "always_on" );\n' for a, b in sorted(adj))
    g = g.replace('\tlevel flag::set( "always_on" );\n', '\tlevel flag::set( "always_on" );\n\n\t// BoD zones (add_zones.py)\n' + lines)
    open(GSC, "w", encoding="utf-8").write(g)
    print(f"dropped {dropped} template ents; zones {len(zones)}; spawn points {sum(len(v) for v in zones.values())}; adjacencies {len(adj)}")
    lonely = [z for z in zones if not any(z in p for p in adj)]
    print("zones with no neighbour:", lonely)

if __name__ == "__main__":
    sys.exit(main())
