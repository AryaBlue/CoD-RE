"""BoD hkaiNavMesh (Havok 2017.2 tagfile in zm_escape.ff.dec) -> cod2map navmesh seeds + optional floor clip brushes.
Usage (64-bit Python): navmesh_extract.py <zone.dec> <TAG0 offset> <outdir> [--check clip_world.json]"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import havok_tag0 as h  # noqa: E402

SCALE = 39.37  # Havok metres -> COD inches; lines BoD up on MotD's own coordinates
FLOOR_DEPTH = 4.0


def navmesh(tf):
    nm = tf.by_name("hkaiNavMesh")[0]
    _, vo, vn = tf.array(nm, "vertices")
    _, eo, en = tf.array(nm, "edges")
    _, fo, fn = tf.array(nm, "faces")
    verts = np.frombuffer(tf.buf, np.float32, vn * 4, vo).reshape(-1, 4)[:, :3].astype(float) * SCALE
    edges = np.frombuffer(tf.buf, np.int32, en * 5, eo).reshape(-1, 5)  # a, b, oppositeEdge, oppositeFace, flags|cost
    faces = np.frombuffer(tf.buf, np.int32, fn * 4, fo).reshape(-1, 4)  # startEdge, startUserEdge, numEdges|numUser<<16, cluster
    polys = [edges[s:s + (n & 0xFFFF), 0] for s, n in zip(faces[:, 0], faces[:, 2])]
    return verts, polys


def floor_brush(points):
    """Convex face extruded FLOOR_DEPTH down, as clip.json planes (axial -X +X -Y +Y -Z +Z first, then sides)."""
    lo, hi = points.min(0), points.max(0)
    planes = [[-1, 0, 0, -lo[0]], [1, 0, 0, hi[0]], [0, -1, 0, -lo[1]], [0, 1, 0, hi[1]],
              [0, 0, -1, -(lo[2] - FLOOR_DEPTH)], [0, 0, 1, hi[2]]]
    n = np.cross(points[1] - points[0], points[2] - points[0])
    if np.linalg.norm(n) > 1e-6:
        n = n / np.linalg.norm(n) * (1 if n[2] > 0 else -1)
        planes.append([*n.round(6), float(n @ points[0])])  # sloped top
    centre = points.mean(0)
    for a, b in zip(points, np.roll(points, -1, 0)):
        side = np.cross(b - a, [0, 0, 1.0])
        if np.linalg.norm(side) < 1e-6:
            continue
        side /= np.linalg.norm(side)
        if side @ (centre - a) > 0:
            side = -side
        planes.append([*side.round(6), float(side @ a)])
    verts = np.vstack([points, points - [0, 0, FLOOR_DEPTH]])
    return {"contents": 0x1, "planes": [[float(x) for x in p] for p in planes], "verts": verts.round(3).tolist()}


def main():
    zone, offset, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    verts, polys = navmesh(h.Tagfile(h.load(zone, offset), 4))
    out.mkdir(parents=True, exist_ok=True)
    centroids = np.array([verts[p].mean(0) for p in polys])
    seeds = [{"origin": [round(float(x), 1) for x in c + [0, 0, 8]]} for c in centroids]
    (out / "bod_nav_seeds.json").write_text(json.dumps(seeds))
    brushes = [floor_brush(verts[p]) for p in polys]
    (out / "bod_nav_floor_clip.json").write_text(json.dumps({"brushes": brushes, "tris": [], "tri_contents": []}))
    print(f"{len(polys)} faces, {len(verts)} verts; bounds {verts.min(0).round()} .. {verts.max(0).round()}")
    if "--check" in sys.argv:
        d = json.loads(Path(sys.argv[sys.argv.index("--check") + 1]).read_text())
        b = np.array([[-p[0][3], -p[2][3], -p[4][3], p[1][3], p[3][3], p[5][3]] for p in (x["planes"] for x in d["brushes"])])
        inside = [c for c in centroids if (b[:, 0] <= c[0]).any() and c[0] <= b[:, 3].max() and b[:, 1].min() <= c[1] <= b[:, 4].max()]
        on = sum(((b[:, 0] <= c[0]) & (c[0] <= b[:, 3]) & (b[:, 1] <= c[1]) & (c[1] <= b[:, 4]) & (abs(b[:, 5] - c[2]) < 24)).any()
                 for c in inside)
        print(f"alignment: {on}/{len(inside)} centroids inside the shell's footprint sit within 24u of a shell brush top")


if __name__ == "__main__":
    main()
