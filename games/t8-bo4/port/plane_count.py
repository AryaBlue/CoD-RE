"""Budget gauge: count the DISTINCT collision planes a clip.json contributes to cod2map's global plane table.

cod2map keeps one MAX_MAP_PLANES table (131,072) of every unique plane referenced by brush sides. It dedupes
a plane against the whole table, and (idTech lineage, confirmed by this project's count_map_planes.py note) stores
each geometric plane together with its flip, so the table grows by TWO per new undirected plane. We therefore
canonicalise with a CONSISTENT SIGN (a plane and its opposite collapse to one key) and report:
  - unique       : distinct undirected planes (the dedup count)
  - table (x2)   : unique*2, the slots those planes occupy -> compare THIS against 131,072
We also print directed-unique (no sign merge) so nothing is hidden.

Counts exactly what cod2map receives: brushes that clip_brushes.py would emit (same skip rules) plus the prism
planes it makes from tris. Run on a decimated clip.json to read the new budget.

Usage: python plane_count.py <clip.json> [...] [--neps 0.001] [--deps 0.01] [--cap 131072]
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"F:\ClaudeWork\bo3\bo3_modtools_test")))
import clip_brushes as cb  # emit filter + prism plane math, the single source of truth


def canonical(plane, neps, deps):
    """Undirected canonical key: unit normal, first significant component forced positive, quantised."""
    a, b, c, d = plane
    L = math.sqrt(a * a + b * b + c * c)
    if L < 1e-9:
        return None
    a, b, c, d = a / L, b / L, c / L, d / L
    if a < -1e-6 or (abs(a) <= 1e-6 and (b < -1e-6 or (abs(b) <= 1e-6 and c < 0))):
        a, b, c, d = -a, -b, -c, -d
    return (round(a / neps), round(b / neps), round(c / neps), round(d / deps))


def canonical_dir(plane, neps, deps):
    """Directed key: no sign merge (for reference only)."""
    a, b, c, d = plane
    L = math.sqrt(a * a + b * b + c * c)
    if L < 1e-9:
        return None
    return (round(a / L / neps), round(b / L / neps), round(c / L / neps), round(d / L / deps))


def emitted_brush_planes(brush):
    """The planes clip_brushes.brushes() would emit for this brush, or None if it skips the brush."""
    texture = cb.texture_for(brush.get("contents", cb.SOLID))
    planes = [(cb.norm(p[:3]), p[3]) for p in brush["planes"]]
    if texture is None or len(planes) < 4 or any(n is None for n, _ in planes):
        return None
    if brush.get("centre"):
        centre = brush["centre"]
    elif brush.get("verts"):
        centre = [sum(v[i] for v in brush["verts"]) / len(brush["verts"]) for i in range(3)]
    else:
        centre = cb.axial_centre(planes)
    extent = min(planes[i][1] + planes[i + 1][1] for i in (0, 2, 4))
    if centre is None or extent > 4096:
        return None
    return [[n[0], n[1], n[2], d] for n, d in planes]


def prism_planes(verts):
    """The 5 planes clip_brushes.prism() makes from a collision tri (front, back, 3 sides)."""
    a, b, c = verts
    n = cb.norm(cb.cross(cb.sub(b, a), cb.sub(c, a)))
    if n is None:
        return None
    centre = [(x + y + z) / 3 - cb.PRISM_DEPTH / 2 * k for x, y, z, k in zip(a, b, c, n)]
    d = sum(x * y for x, y in zip(n, a))
    out = [[n[0], n[1], n[2], d], [-n[0], -n[1], -n[2], -(d - cb.PRISM_DEPTH)]]
    for p, q in ((a, b), (b, c), (c, a)):
        side = cb.norm(cb.cross(cb.sub(q, p), n))
        if side is None:
            return None
        if sum(s * (m - x) for s, m, x in zip(side, centre, p)) > 0:
            side = [-s for s in side]
        out.append([side[0], side[1], side[2], sum(s * x for s, x in zip(side, p))])
    return out


def clip_planes(path):
    """Every plane the emitter would put in the .map from this clip.json: (brush_planes, prism_planes)."""
    data = json.loads(Path(path).read_text())
    bplanes, nbrush = [], 0
    for brush in data.get("brushes", []):
        pl = emitted_brush_planes(brush)
        if pl is not None:
            nbrush += 1
            bplanes.extend(pl)
    pplanes, nprism = [], 0
    tri_contents = data.get("tri_contents") or []
    for i, tri in enumerate(data.get("tris", [])):
        verts, contents = (tri["verts"], tri.get("contents", cb.SOLID)) if isinstance(tri, dict) else \
            (tri[:3], tri_contents[i] if i < len(tri_contents) else cb.SOLID)
        if cb.texture_for(contents) is None:
            continue
        pl = prism_planes(verts)
        if pl is not None:
            nprism += 1
            pplanes.extend(pl)
    return bplanes, pplanes, nbrush, nprism


def count(path, neps, deps, cap):
    bplanes, pplanes, nbrush, nprism = clip_planes(path)
    allp = bplanes + pplanes
    uniq = {k for k in (canonical(p, neps, deps) for p in allp) if k}
    uniq_b = {k for k in (canonical(p, neps, deps) for p in bplanes) if k}
    uniq_dir = {k for k in (canonical_dir(p, neps, deps) for p in allp) if k}
    table = len(uniq) * 2
    print(f"{path}")
    print(f"  emitted: {nbrush} brushes ({len(bplanes)} face slots) + {nprism} prisms ({len(pplanes)} slots)")
    print(f"  unique undirected planes : {len(uniq)}   (brush-only {len(uniq_b)})")
    print(f"  unique directed planes   : {len(uniq_dir)}")
    print(f"  plane TABLE (x2 flips)   : {table}  vs MAX_MAP_PLANES {cap}  -> {'OVER' if table > cap else 'under'} "
          f"({table * 100 // cap}% of cap)")
    return len(uniq), table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--neps", type=float, default=0.001)
    ap.add_argument("--deps", type=float, default=0.01)
    ap.add_argument("--cap", type=int, default=131072)
    args = ap.parse_args()
    for f in args.files:
        count(f, args.neps, args.deps, args.cap)


if __name__ == "__main__":
    main()
