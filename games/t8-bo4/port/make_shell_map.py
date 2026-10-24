"""Make a BO3 usermap that places imported world-coordinate chunk xmodels as misc_models (the E1 shell):
clones the zm_cltest usermap, keeps its gameplay entities but moves spawns to the given start and fits
the zone/Umbra/sun/fps volumes to the chunks' bounds."""
import argparse
import json
import re
import shutil
import uuid
from pathlib import Path

import clip_brushes

TOOLS = Path(r"F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130")
TEMPLATE = "zm_cltest"
TEMPLATE_START = (0.0, -448.0, 40.0)
ATMOS_SKY = "skybox_default_night"  # matches make_atmos.py's BOD_SUN
ATMOS_LUT = "luts_t7_zm_alcatraz_bod"  # bod_port\grade\gen_bod_lut.py --install
VOLUMES = ("info_volume", "umbra_volume", "volume_sun", "volume_fpstool")
DROP = ("misc_prefab",)  # perk/box/barricade prefabs would land inside walls; the shell is walk-only
ENTITY = re.compile(r"// entity \d+\n\{\n(.*?)\n\}\n(?=// entity|\Z)", re.S)  # brush entities nest "}" lines
POINT = re.compile(r"\( (\S+) (\S+) (\S+) \)")


def guid():
    return "{" + str(uuid.uuid4()).upper() + "}"


def chunk_bounds(exports, margin):
    """Robust bounds (0.5/99.5 percentile per axis) so stray skybox/far verts don't blow the volumes up."""
    axes = [[], [], []]
    for export in exports:
        for x, y, z in re.findall(r"^OFFSET ([^,\s]+),? ([^,\s]+),? ([^,\s]+)\s*$",export.read_text(errors="replace"), re.M):
            for a, v in zip(axes, (x, y, z)):
                a.append(float(v))
    if not axes[0]:
        raise SystemExit("no vertices found in the chunks")
    lo, hi = [], []
    for a in axes:
        a.sort()
        lo.append(round(a[int(len(a) * 0.005)] - margin))
        hi.append(round(a[int(len(a) * 0.995)] + margin))
    return lo, hi


def fit_bounds(body):
    """Bounds of an axis-aligned brush, from the constant axis of each face's plane points."""
    old_lo, old_hi = [1e9] * 3, [-1e9] * 3
    for face in (l for l in body.splitlines() if l.lstrip().startswith("(")):
        pts = [tuple(map(float, p)) for p in POINT.findall(face)[:3]]
        for axis in range(3):
            if pts[0][axis] == pts[1][axis] == pts[2][axis]:
                old_lo[axis] = min(old_lo[axis], pts[0][axis])
                old_hi[axis] = max(old_hi[axis], pts[0][axis])
    return old_lo, old_hi


def fit_brush(body, lo, hi):
    """Affine-map an axis-aligned template brush onto [lo, hi]; positive scale keeps the face winding."""
    faces = [l for l in body.splitlines() if l.lstrip().startswith("(")]
    old_lo, old_hi = fit_bounds(body)

    def move(m):
        return "( " + " ".join(f"{round(lo[i] + (float(m.group(i + 1)) - old_lo[i]) * (hi[i] - lo[i]) / (old_hi[i] - old_lo[i]))}"
                               for i in range(3)) + " )"
    for face in faces:
        head, rest = face[:face.rindex(")") + 1], face[face.rindex(")") + 1:]
        body = body.replace(face, POINT.sub(move, head) + rest, 1)
    return body


def set_key(body, key, value):
    line = f'"{key}" "{value}"'
    return re.sub(rf'^"{key}" "[^"]*"$', line, body, flags=re.M) if f'"{key}" "' in body else \
        re.sub(r'^("classname" "[^"]*")$', rf"\1\n{line}", body, count=1, flags=re.M)


def source_nodes(ents_path):
    """(origin, angles) of every node_pathnode in a dumped .ents file."""
    text = Path(ents_path).read_text(errors="replace")
    ents = [dict(re.findall(r'"([^"]+)" "([^"]*)"', b)) for b in re.findall(r"\{([^{}]*)\}", text)]
    return [(e["origin"], e.get("angles", "0 0 0")) for e in ents if e.get("classname") == "node_pathnode" and "origin" in e]


def source_spawns(ents_path):
    """The source map's own player start structs (the template's land half-inside props)."""
    text = Path(ents_path).read_text(errors="replace")
    ents = [dict(re.findall(r'"([^"]+)" "([^"]*)"', b)) for b in re.findall(r"\{([^{}]*)\}", text)]
    return [e for e in ents if e.get("targetname") == "initial_spawn_points" and "script_string" not in e]


def build_map(models, lo, hi, start, angle, clip=(), nodes=(), spawns=(), props=(), atmos=None):
    text = (TOOLS / "map_source" / "zm" / f"{TEMPLATE}.map").read_text(errors="replace")
    header = text[:text.index("// entity 0")]
    delta = [s - t for s, t in zip(start, TEMPLATE_START)]
    out = []
    for m in ENTITY.finditer(text):
        body = m.group(1)
        cls = re.search(r'"classname" "([^"]+)"', body).group(1)
        if cls in DROP or spawns and '"targetname" "initial_spawn_points"' in body:
            continue
        if cls == "worldspawn":
            # cod2map asserts with no structural brush (no cells), so the template's one brush moves under the map
            size = [h - l for l, h in zip(*fit_bounds(body))]
            body = fit_brush(body, [lo[0], lo[1], lo[2] - size[2]], [lo[0] + size[0], lo[1] + size[1], lo[2]])
            if atmos:  # make_atmos.py names the ssi and fog alike; wsi follows the ssi as in stock maps
                for key, value in (("ssi", atmos), ("wsi", atmos), ("fsi", atmos), ("skyboxmodel", ATMOS_SKY), ("lutmaterial", ATMOS_LUT)):
                    body = set_key(body, key, value)
            body += "".join(f"\n// brush {i}\n{{\n guid \"{guid()}\"\n" + b[2:].rstrip() for i, b in enumerate(clip, 1))
        elif cls in VOLUMES:
            body = fit_brush(body, lo, hi)
        elif cls == "info_player_start":
            body = set_key(set_key(body, "origin", "{:g} {:g} {:g}".format(*start)), "angles", f"0 {angle:g} 0")
        else:  # structs, spawners, probe: keep the template layout around the new start
            origin = re.search(r'^"origin" "(\S+) (\S+) (\S+)"$', body, re.M)
            if origin:
                body = set_key(body, "origin", " ".join(f"{float(v) + d:g}" for v, d in zip(origin.groups(), delta)))
        out.append(body)
    for model in models:
        out.append(f'guid "{guid()}"\n"classname" "misc_model"\n"model" "{model}"\n"origin" "0 0 0"\n"angles" "0 0 0"\n'
                   '"modelscale" "1"\n"static" "1"\n"use_collmap" "1"\n' +  # bakes the GDT CollisionMap into the bsp (player clip + navmesh)
"\n".join(f'"lightingstate{i}" "1"' for i in range(1, 5)))
    for p in props:  # placed instances: {model, origin [x,y,z], angles [p,y,r], scale}
        out.append(f'guid "{guid()}"\n"classname" "misc_model"\n"model" "{p["model"]}"\n'
                   f'"origin" "{" ".join(f"{v:g}" for v in p["origin"])}"\n"angles" "{" ".join(f"{v:g}" for v in p.get("angles", (0, 0, 0)))}"\n'
                   f'"modelscale" "{p.get("scale", 1):g}"\n"static" "1"\n' + "\n".join(f'"lightingstate{i}" "1"' for i in range(1, 5)))
    for s in spawns:  # BO3 picks initial_spawn structs whose script_string holds <gametype>_<location>
        out.append(f'guid "{guid()}"\n"classname" "script_struct"\n"origin" "{s["origin"]}"\n"angles" "{s.get("angles", "0 0 0")}"\n'
                   f'"targetname" "initial_spawn_points"\n"script_noteworthy" "initial_spawn"\n"script_int" "{s.get("script_int", "1")}"\n'
                   '"radius" "32"\n"script_string" "zclassic_start_room zcleansed_start_room zgrief_start_room"')
    for origin, angles in nodes:  # the source map's path nodes, as navmesh seeds across the whole map
        out.append(f'guid "{guid()}"\n"classname" "node_pathnode"\n"origin" "{origin}"\n"angles" "{angles}"')
    out = [re.sub(r"guid \"\{[^}]+\}\"", lambda _: f'guid "{guid()}"', b) for b in out]
    return header + "".join(f"// entity {i}\n{{\n{b}\n}}\n" for i, b in enumerate(out))


def clone_usermap(name, models, sky="skybox_default_day", lut="luts_t7_default"):
    src, dst = TOOLS / "usermaps" / TEMPLATE, TOOLS / "usermaps" / name
    files = [src / "scripts" / "zm" / f"{TEMPLATE}.gsc", src / "scripts" / "zm" / f"{TEMPLATE}.csc",
             src / "sound" / "zoneconfig" / f"{TEMPLATE}.szc", src / "zone_source" / "loc" / f"{TEMPLATE}.zone"]
    for f in files:
        target = dst / str(f.relative_to(src)).replace(TEMPLATE, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f.read_text(errors="replace").replace(TEMPLATE, name))
    zone = (src / "zone_source" / f"{TEMPLATE}.zone").read_text(errors="replace").replace(TEMPLATE, name)
    zone = zone.replace("xmodel,skybox_default_day", f"xmodel,{sky}").replace("material,luts_t7_default", f"material,{lut}")
    zone = zone[:zone.index("// stand-in import test")].rstrip() + "\n\n// shell chunks\n" + "".join(f"xmodel,{m}\n" for m in models)
    (dst / "zone_source" / f"{name}.zone").write_text(zone)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="usermap name, e.g. zm_alcatraz")
    ap.add_argument("chunks", type=Path, help="folder of <model>.XMODEL_EXPORT chunks (already imported)")
    ap.add_argument("--start", type=float, nargs=3, required=True, help="player start x y z")
    ap.add_argument("--angle", type=float, default=90)
    ap.add_argument("--margin", type=float, default=512)
    ap.add_argument("--clip", type=Path, help="clip.json (T6 clipmap brushes + tris) -> worldspawn clip brushes")
    ap.add_argument("--terrain", type=Path, help="clip.json whose tris become clip patch meshes (large tri-soups)")
    ap.add_argument("--extend", type=float, nargs=6, metavar=("X0", "Y0", "Z0", "X1", "Y1", "Z1"), help="also cover this box with the volumes")
    ap.add_argument("--safety", type=float, nargs=5, metavar=("X0", "Y0", "X1", "Y1", "TOP"), help="caulk pad under the start area")
    ap.add_argument("--props", type=Path, help="JSON list of {model, origin, angles, scale} placed as static misc_models")
    ap.add_argument("--atmos", help="ssi/fog name from make_atmos.py, set on the worldspawn")
    ap.add_argument("--ents", type=Path, help="source .ents dump; its node_pathnodes become navmesh seeds")
    args = ap.parse_args()
    exports = sorted(args.chunks.glob("*.XMODEL_EXPORT"))
    models = [re.sub(r"_lod0$", "", p.stem.lower()) for p in exports]  # as import_rip names them
    lo, hi = chunk_bounds(exports, args.margin) if exports else (list(args.extend[:3]), list(args.extend[3:]))
    if args.extend:  # grow the volumes over terrain/props outside the chunks (e.g. the BoD bridge)
        lo = [min(l, round(e - args.margin)) for l, e in zip(lo, args.extend[:3])]
        hi = [max(h, round(e + args.margin)) for h, e in zip(hi, args.extend[3:])]
    clip, skipped = clip_brushes.brushes(args.clip) if args.clip else ([], 0)
    if args.terrain:
        terrain, terrain_skipped = clip_brushes.patches(args.terrain)
        clip, skipped = clip + terrain, skipped + terrain_skipped
    if args.safety:  # structural caulk pad: catches the player even if the clip brushes don't collide
        x0, y0, x1, y1, top = args.safety
        planes = [([-1, 0, 0], -x0), ([1, 0, 0], x1), ([0, -1, 0], -y0), ([0, 1, 0], y1), ([0, 0, -1], -(top - 64)), ([0, 0, 1], top)]
        clip.append(clip_brushes.brush_text(planes, [(x0 + x1) / 2, (y0 + y1) / 2, top - 32], "caulk"))
    nodes = source_nodes(args.ents) if args.ents else []
    spawns = source_spawns(args.ents) if args.ents else []
    props = json.loads(args.props.read_text()) if args.props else []
    (TOOLS / "map_source" / "zm" / f"{args.name}.map").write_text(
        build_map(models, lo, hi, args.start, args.angle, clip, nodes, spawns, props, args.atmos))
    clone_usermap(args.name, models + sorted({p["model"] for p in props}), *((ATMOS_SKY, ATMOS_LUT) if args.atmos else ()))
    print(f"{args.name}: {len(models)} misc_models, {len(clip)} clip brushes ({skipped} skipped), {len(nodes)} path nodes; "
          f"volumes {[round(v) for v in lo]} .. {[round(v) for v in hi]}")


if __name__ == "__main__":
    main()
