"""Visible render mesh from the BoD terrain tri-soup: clip.json tris -> OBJ + materials.json for obj_to_xme.py.
Floors (|nz| >= 0.5) face up with one material; steeper tris are emitted two-sided (the soup's winding is mixed).
XME front face = counter-clockwise (cross(b-a, c-a) along the normal), checked against Greyhound rip models.
Usage: soup_to_obj.py clip.json out.obj materials.json [--floor zm_al_concrete_bare] [--wall dirt_rocky04]"""
import argparse
import json
from pathlib import Path

import numpy as np

IMAGES = Path(r"E:\ClaudeWork\bo3\bod_port\geo\chunks_textured\_images")  # MotD base textures (real names)
UV_SCALE = 256.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip", type=Path)
    ap.add_argument("obj", type=Path)
    ap.add_argument("materials", type=Path)
    ap.add_argument("--floor", default="zm_al_concrete_bare")
    ap.add_argument("--wall", default="dirt_rocky04")
    args = ap.parse_args()
    t = np.array(json.loads(args.clip.read_text())["tris"], float)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    length = np.linalg.norm(n, axis=1)
    t, n = t[length > 1e-6], n[length > 1e-6] / length[length > 1e-6, None]
    floor = np.abs(n[:, 2]) >= 0.5
    down = floor & (n[:, 2] < 0)
    t[down] = t[down][:, ::-1]  # reverse winding so every floor faces up
    n[down] = -n[down]
    walls = t[~floor]
    tris = [(args.floor, t[floor], n[floor]), (args.wall, walls, n[~floor]), (args.wall, walls[:, ::-1], -n[~floor])]
    keys, verts = {}, []
    with args.obj.open("w", newline="\n") as f:
        body, normals, vt = [], [], 0
        for mat, tt, nn in tris:
            body.append(f"usemtl {mat}\n")
            for tri, nrm in zip(tt, nn):
                normals.append(nrm)
                ni = len(normals)
                idx = []
                for p in tri:
                    k = tuple(np.round(p, 3))
                    if k not in keys:
                        keys[k] = len(verts) + 1
                        verts.append(p)
                    # planar UVs: floors on xy, walls on the dominant horizontal axis and z
                    if mat == args.floor:
                        u, v = p[0] / UV_SCALE, p[1] / UV_SCALE
                    else:
                        u, v = (p[1] if abs(nrm[0]) > abs(nrm[1]) else p[0]) / UV_SCALE, p[2] / UV_SCALE
                    body.append(f"vt {u:.4f} {v:.4f}\n")
                    idx.append(keys[k])
                    vt += 1
                body.append(f"f {idx[0]}/{vt - 2}/{ni} {idx[1]}/{vt - 1}/{ni} {idx[2]}/{vt}/{ni}\n")
        f.writelines(f"v {x:.3f} {y:.3f} {z:.3f}\n" for x, y, z in verts)
        f.writelines(f"vn {x:.5f} {y:.5f} {z:.5f}\n" for x, y, z in normals)
        f.writelines(body)
    mats = {m: {"colorMap": str(IMAGES / m / f"{m}_c.png")} for m in (args.floor, args.wall)}
    args.materials.write_text(json.dumps(mats, indent=1))
    print(f"{int(floor.sum())} floor + {2 * len(walls)} two-sided wall tris, {len(verts)} verts -> {args.obj}")


if __name__ == "__main__":
    main()
