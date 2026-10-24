"""World-space collision tris from the LOD0 render meshes of SOLID placed props (BoD's collision static models), as clip.json.
Usage (64-bit Python): prop_collision_tris.py props.json out.json [--prefix p8_zm_esc_bridge_] [--min-nz 0.5]"""
import argparse
import json
import re
from pathlib import Path

import numpy as np

RIP = Path(r"E:\ClaudeWork\bo3\greyhound\app\exported_files\black_ops_4\xmodels")
OFFSET = re.compile(r"^OFFSET (\S+), (\S+), (\S+)", re.M)
TRI_VERTS = re.compile(r"^TRI [^\n]*\nVERT (\d+)[\s\S]*?\nVERT (\d+)[\s\S]*?\nVERT (\d+)", re.M)


def mesh(model):
    xme = next((RIP / model).glob("*_LOD0.XMODEL_EXPORT"), None)
    if xme is None:
        return None
    text = xme.read_text(errors="replace")
    faces = text[text.index("\nNUMFACES "):]
    verts = np.array(OFFSET.findall(text, 0, text.index("\nNUMFACES ")), float)
    tris = np.array(TRI_VERTS.findall(faces), int)
    return verts[tris] if len(tris) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("props", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--prefix", default="", help="only models whose name starts with this")
    ap.add_argument("--min-nz", type=float, help="keep only tris whose |normal.z| is at least this (walkable surfaces)")
    args = ap.parse_args()
    props = [p for p in json.loads(args.props.read_text()) if p["model"].startswith(args.prefix) and p.get("contents", 1) & 0x1]
    cache, out = {}, []
    for p in props:
        if p["model"] not in cache:
            cache[p["model"]] = mesh(p["model"])
        local = cache[p["model"]]
        if local is None:
            continue
        axis = np.array(p["axis"], float).reshape(3, 3)  # rows forward/left/up
        world = np.asarray(p["origin"], float) + p.get("scale", 1) * local @ axis
        if args.min_nz is not None:
            n = np.cross(world[:, 1] - world[:, 0], world[:, 2] - world[:, 0])
            length = np.linalg.norm(n, axis=1)
            world = world[(length > 1e-6) & (np.abs(n[:, 2]) >= args.min_nz * np.maximum(length, 1e-9))]
        out.extend(world.round(3).tolist())
    args.out.write_text(json.dumps({"brushes": [], "tris": out, "tri_contents": [1] * len(out)}))
    print(f"{len(props)} SOLID placements, {len(cache)} models -> {len(out)} tris -> {args.out}")


if __name__ == "__main__":
    main()
