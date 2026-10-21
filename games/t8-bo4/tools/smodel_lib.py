"""Shared helpers for the MotD static-model (smodel) pass.

Three jobs reuse this: placement-list angle recovery, the glb->XME mesh conversion, and the offline gate.
Facts verified against the dump's own xmodel JSON bounds oracle (see build_smodel_xmodels verification):
  - OAT waw2bo2 glbs are 1:1 COD INCHES (NO x100 scale).
  - glTF is Y-up RH; COD is Z-up. Axis map cod=(gx,-gz,gy), determinant +1 (winding/normals preserved).
  - placement axis stored by gfxworld is a COD AnglesToAxis matrix; angles recovered by its inverse."""
from __future__ import annotations

import json
import math
import re
import struct
from pathlib import Path

DUMP = Path(r"PATH/TO/zm_prison_dump")  # set this to your own path
REDUMP = Path(r"PATH/TO/redump")  # set this to your own path
MODEL_EXPORT = DUMP / "model_export"
XMODEL = DUMP / "xmodel"

# --- placement angle recovery (COD convention) ---------------------------------------------------


def axis_to_angles(a):
    """9-float COD axis (row0=forward, row1=left, row2=up) -> [pitch, yaw, roll] degrees."""
    fx, fy, fz = a[0], a[1], a[2]
    horiz = math.hypot(fx, fy)
    pitch = math.degrees(math.atan2(-fz, horiz))
    if horiz > 1e-6:
        yaw = math.degrees(math.atan2(fy, fx))
        roll = math.degrees(math.atan2(a[5], a[8]))  # left.z=sr*cp, up.z=cr*cp
    else:  # gimbal: pitch=+-90, fold roll into yaw, roll=0
        yaw = math.degrees(math.atan2(-a[3], a[4]))
        roll = 0.0
    return [pitch, yaw, roll]


def angles_to_axis(pitch, yaw, roll):
    """COD AnglesToAxis: [pitch,yaw,roll] deg -> 9 floats (row0=forward, row1=left, row2=up)."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return (
        cp * cy, cp * sy, -sp,
        sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, sr * cp,
        cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp,
    )


def axis_roundtrip_error(a):
    """Max abs element error of angles_to_axis(axis_to_angles(a)) vs a."""
    b = angles_to_axis(*axis_to_angles(a))
    return max(abs(b[i] - a[i]) for i in range(9))


# --- glb (OAT glTF 2.0 binary) reader ------------------------------------------------------------

_CT_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_CT_FMT = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
_TYPE_N = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class GlbError(Exception):
    pass


def _read_accessor(js, bin_blob, idx):
    acc = js["accessors"][idx]
    n = _TYPE_N[acc["type"]]
    ct = acc["componentType"]
    comp = _CT_SIZE[ct]
    bv = js["bufferViews"][acc["bufferView"]]
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or (comp * n)
    fmt = "<" + _CT_FMT[ct] * n
    out = []
    for i in range(acc["count"]):
        out.append(struct.unpack_from(fmt, bin_blob, base + i * stride))
    return out, acc


def read_glb(path: Path):
    """Return dict: prims=[{positions,normals,uvs,indices,material}], plus any non-identity node warn."""
    d = path.read_bytes()
    magic, ver, length = struct.unpack_from("<III", d, 0)
    if magic != 0x46546C67:
        raise GlbError("not a glb")
    off, js_blob, bin_blob = 12, None, b""
    while off < length:
        clen, ctype = struct.unpack_from("<II", d, off)
        off += 8
        cdata = d[off:off + clen]
        off += clen
        if ctype == 0x4E4F534A:
            js_blob = cdata
        elif ctype == 0x004E4942:
            bin_blob = cdata
    js = json.loads(js_blob)
    for b in js.get("buffers", []):
        if b.get("uri"):
            raise GlbError("external buffer uri not supported")
    warn = []
    for n in js.get("nodes", []):
        if any(k in n for k in ("matrix", "rotation", "translation")) or n.get("scale", [1, 1, 1]) != [1, 1, 1]:
            warn.append(n.get("name", "?"))
    mats = [m.get("name", f"mat{i}") for i, m in enumerate(js.get("materials", []))]
    prims = []
    for mesh in js.get("meshes", []):
        for pr in mesh["primitives"]:
            if pr.get("mode", 4) != 4:
                raise GlbError(f"primitive mode {pr.get('mode')} not triangles")
            att = pr["attributes"]
            pos, _ = _read_accessor(js, bin_blob, att["POSITION"])
            nrm = _read_accessor(js, bin_blob, att["NORMAL"])[0] if "NORMAL" in att else None
            uv = _read_accessor(js, bin_blob, att["TEXCOORD_0"])[0] if "TEXCOORD_0" in att else None
            idx = [t[0] for t in _read_accessor(js, bin_blob, pr["indices"])[0]] if "indices" in pr else list(range(len(pos)))
            mi = pr.get("material")
            prims.append({"positions": pos, "normals": nrm, "uvs": uv, "indices": idx,
                          "material": mats[mi] if mi is not None else "default"})
    return {"prims": prims, "node_warn": warn}


def glb_to_cod(v):
    """glTF Y-up (x,y,z) -> COD Z-up (x,-z,y)."""
    return (v[0], -v[2], v[1])


# --- material colour resolve (prop materials) ----------------------------------------------------

_MAT_DIRS = [REDUMP / "materials", DUMP / "materials"]
_IMG_DIRS = [REDUMP / "images", DUMP / "images"]


def _find_file(dirs, rel):
    for base in dirs:
        p = base / rel
        if p.is_file():
            return p
    return None


def resolve_material_colour(mat_name: str):
    """prop material name ('mc/mtl_x' or 'x') -> colour .iwi Path or None (via material JSON colorMap)."""
    mj = _find_file(_MAT_DIRS, mat_name + ".json")
    if mj is None:
        return None
    texs = json.loads(mj.read_text(encoding="utf-8")).get("textures", [])
    cm = next((t for t in texs if t.get("semantic") == "colorMap"), None) \
        or next((t for t in texs if t.get("name") == "colorMap"), None)
    if not cm or not cm.get("image"):
        return None
    return _find_file(_IMG_DIRS, cm["image"] + ".iwi")


def sanitise(raw: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9_]", "_", raw.lower())).strip("_") or "mtl"


def mat_id(mat_name: str) -> str:
    """Lowercase base id for a prop material (leaf after technique subdir)."""
    return sanitise(mat_name.split("/")[-1])


def asset_id(name: str) -> str:
    """Flat, legal, lowercase asset/dir name (gdt rejects '/'); slash-prefixed names are kept distinct."""
    return sanitise(name.lower().replace("/", "_"))


# --- classification --------------------------------------------------------------------------------

# scripted/economy/interactive systems handled elsewhere -> do NOT convert as scenery.
# whole-underscore-token match (avoids corruGATEd / _PAPer / _POWERpole false positives).
INTERACTIVE_TOKENS = {
    "vending", "perk", "afterlife", "teleporter", "buildable", "workbench", "craftable",
    "powerbreaker", "powerswitch", "breaker", "pap", "packapunch", "wallbuy", "mystery",
    "treasure", "toybox", "trap", "gate", "juggernog", "revive", "fanblade",
}
# multi-token sequences
INTERACTIVE_SEQ = ("cell_door", "magic_box", "acid_trap", "pack_a_punch", "quick_revive",
                   "power_switch", "electric_switch", "fan_blade")
# true FX/UI card materials to drop at primitive level (NOT solid geometry that merely has 'decal'
# in a trim name, e.g. zm_al_decal_trim_wire_orange_twist on the gg bridge cable).
FX_MAT = re.compile(r"^gfx|^fxt_|^hud_|^menu_|flare|distortion|reticle|_particle(_|$)", re.I)


# decorative background clumps that name-match an interactive rule but are pure scenery (coordinator-approved)
SCENERY_OVERRIDE = {"p6_zm_al_cell_door_clump"}


def classify(name: str) -> str:
    low = name.lower()
    wrap = "_" + low + "_"
    if low in SCENERY_OVERRIDE:
        return "scenery"
    if low.startswith(("c_zom", "c_zombie")) or low.endswith(("_anim", "_skel")):
        return "skinned_anim"  # character/animated -> not rigid scenery, handled elsewhere
    if low.startswith("fxanim") or "_fxanim" in wrap:
        return "fx_anim"
    tokens = set(low.split("_"))
    if tokens & INTERACTIVE_TOKENS or any(s in wrap for s in INTERACTIVE_SEQ):
        return "interactive"
    if "door" in tokens and "frame" not in tokens:  # door frame = scenery; door leaf = scripted
        return "door_review"
    return "scenery"


def lod0_glb(name: str) -> Path | None:
    p = MODEL_EXPORT / f"{name.lower()}_lod0.glb"
    return p if p.is_file() else None


def xmodel_bounds(name: str):
    """(mins, maxs) from the dump's xmodel JSON boneInfo[0], COD inches Z-up, or None."""
    p = XMODEL / f"{name.lower()}.json"
    if not p.is_file():
        return None
    bi = json.loads(p.read_text(encoding="utf-8")).get("boneInfo", [])
    if not bi:
        return None
    return tuple(bi[0]["mins"]), tuple(bi[0]["maxs"])
