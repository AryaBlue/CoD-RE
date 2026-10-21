"""Check an extractor's gfx.bin (W2BSP001) + clip.json against what the BO3 shell pipeline consumes
(build_textured.py via world.read_gfx_world, clip_brushes.py). Usage: validate_emit.py gfx.bin clip.json [x y z]"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

# external dependency: B2W / BO1MapConverter (not included) — https://github.com/Ticass/B2W
sys.path.insert(0, r"PATH/TO/BO1MapConverter/b2w_bo1/src")  # set this to your own path
from waw2bo2.world import read_gfx_world  # noqa: E402

SOLID, PLAYERCLIP, MONSTERCLIP = 0x1, 0x10000, 0x20000


def check_gfx(path, landmark):
    w = read_gfx_world(path)  # raises on any layout mismatch or trailing bytes
    V, front, back, degenerate = w.vertices, 0, 0, 0
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for s in w.surfaces:
        local = w.indices[s.base_index: s.base_index + s.triangle_count * 3]
        for t in range(s.triangle_count):
            a, b, c = (V[local[3 * t + k] + s.first_vertex] for k in range(3))
            u = [b.xyz[i] - a.xyz[i] for i in range(3)]
            v = [c.xyz[i] - a.xyz[i] for i in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            d = sum(n[i] * (a.normal[i] + b.normal[i] + c.normal[i]) for i in range(3))
            degenerate += d == 0
            back += d > 0  # T6 native order: (p1-p0)x(p2-p0) points AGAINST the vertex normal
            front += d < 0
            for p in (a, b, c):
                lo = [min(lo[i], p.xyz[i]) for i in range(3)]
                hi = [max(hi[i], p.xyz[i]) for i in range(3)]
    tris = front + back + degenerate
    report = {"vertices": len(V), "indices": len(w.indices), "surfaces": len(w.surfaces), "triangles": tris,
              "materials": len({s.material for s in w.surfaces}), "bounds": [lo, hi],
              "winding_ok_pct": round(100 * front / max(tris, 1), 2), "winding_reversed_pct": round(100 * back / max(tris, 1), 2)}
    if landmark:
        report["landmark_inside_bounds"] = all(lo[i] <= landmark[i] <= hi[i] for i in range(3))
    return report


def check_clip(path, landmark):
    d = json.loads(Path(path).read_text())
    problems, contents, outside = [], Counter(), 0
    for i, b in enumerate(d["brushes"]):
        p = b["planes"]
        if len(p) < 6 or any(abs(abs(p[k][k // 2]) - 1) > 1e-4 for k in range(6)):
            problems.append(f"brush {i}: first six planes are not the axial -X +X -Y +Y -Z +Z")
        elif any(p[k][k // 2] != (-1 if k % 2 == 0 else 1) for k in range(6)):
            problems.append(f"brush {i}: axial planes out of order or not outward")
        for v in b.get("verts", []):
            if any(q[0] * v[0] + q[1] * v[1] + q[2] * v[2] > q[3] + 0.05 for q in p):
                outside += 1  # inside a brush is n.x <= d for every plane
                break
        contents[hex(b["contents"])] += 1
        if len(problems) > 20:
            break
    tris = d.get("tris", [])
    for key in ("tri_contents", "tri_materials"):
        if key in d and len(d[key]) != len(tris):
            problems.append(f"{key} has {len(d[key])} entries for {len(tris)} tris")
    blocking = sum(1 for b in d["brushes"] if b["contents"] & (SOLID | PLAYERCLIP | MONSTERCLIP))
    report = {"brushes": len(d["brushes"]), "player_or_ai_blocking": blocking, "tris": len(tris),
              "brushes_with_verts_outside_planes": outside, "top_contents": contents.most_common(6), "problems": problems[:20]}
    if landmark:
        report["landmark_in_brush_bounds"] = sum(
            1 for b in d["brushes"] if all(-b["planes"][2 * k][3] - 64 <= landmark[k] <= b["planes"][2 * k + 1][3] + 64 for k in range(3)))
    return report


if __name__ == "__main__":
    landmark = [float(x) for x in sys.argv[3:6]] if len(sys.argv) >= 6 else None
    print(json.dumps({"gfx": check_gfx(Path(sys.argv[1]), landmark), "clip": check_clip(sys.argv[2], landmark)}, indent=1))
