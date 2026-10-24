"""Reduce the unique collision planes in a clip.json so a ported BO4 map fits under cod2map's MAX_MAP_PLANES.

Operates ONLY on world brushes (tris pass through untouched -> they become patches, which do not count). Output is a
clip.json consumed unchanged by clip_brushes.py, so every brush keeps the emitter contract: first six planes axial in
the order -X +X -Y +Y -Z +Z, verts inside, contents preserved, <=45 sides.

Passes (each lossless unless noted):
  0 redundant  : drop brush planes no vertex supports (pure import noise); re-cap any brush >45 sides to its AABB.
  1 contain    : drop a brush whose AABB sits wholly inside another same-class brush (overlapping per-surface import).
  2 boxify      : replace a brush with its AABB when the box pokes <= --tol past it AND (not a ramp, or rise <= --floor-tol).
                  Floor-safe: a walkable sloped top is only flattened when its vertical rise is within step noise.
  3 merge       : union axis-aligned boxes of equal cross-section, contents and adjacency into one box (exact, no loss).
  4 cluster     : [--cluster] replace each dense grid cell of leftover oblique brushes with one AABB. LOSES concavity.

Passes 2-3 iterate with --tol escalating (x2 each round) until the plane table is <= --target-planes or nothing moves.
--target-planes is the cod2map TABLE size (unique planes x2 for flips); default 120000 leaves headroom under 131072.

Usage: python decimate_clip.py <in.json> <out.json> [--target-planes 120000] [--tol 8] [--floor-tol 8]
                                [--max-tol 64] [--cluster] [--cluster-cell 128] [--report r.json]
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plane_count as pc  # canonical(), emitted_brush_planes(), clip_planes()

EPS = 0.25          # adjacency / coplanar tolerance for box merging (units)
VERT_EPS = 0.1      # a plane is "supported" if a vertex lies this close to it
MAX_SIDES = 45      # Radiant assert: a brush with > 45 sides gives no .led / fullbright
RAMP_NZ = 0.7       # |n.z| above this on a non-axial face = a walkable slope (floor/ceiling), not a wall


def nplanes(planes):
    """Unit-normalised (nx,ny,nz,d) for a brush's raw planes."""
    out = []
    for a, b, c, d in planes:
        L = math.sqrt(a * a + b * b + c * c)
        if L < 1e-9:
            continue
        out.append((a / L, b / L, c / L, d / L))
    return out


def aabb(verts):
    return [min(v[i] for v in verts) for i in range(3)], [max(v[i] for v in verts) for i in range(3)]


def box_corners(lo, hi):
    return [[lo[0] if x == 0 else hi[0], lo[1] if y == 0 else hi[1], lo[2] if z == 0 else hi[2]]
            for x in (0, 1) for y in (0, 1) for z in (0, 1)]


def box_planes(lo, hi):
    """Six axial planes in the emitter's required order -X +X -Y +Y -Z +Z (outward, n.x <= d inside)."""
    return [[-1, 0, 0, -lo[0]], [1, 0, 0, hi[0]], [0, -1, 0, -lo[1]],
            [0, 1, 0, hi[1]], [0, 0, -1, -lo[2]], [0, 0, 1, hi[2]]]


def is_box(pls):
    """True if every normalised plane is axial (the brush is already an AABB)."""
    return all(max(abs(n[0]), abs(n[1]), abs(n[2])) > 0.9999 for n in pls)


def protrusion(lo, hi, pls):
    """Max distance a corner of the AABB poking outside the brush polytope (= max solid an AABB swap would add)."""
    worst = 0.0
    for c in box_corners(lo, hi):
        worst = max(worst, max(a * c[0] + b * c[1] + cc * c[2] - d for a, b, cc, d in pls))
    return worst


def ramp_top(pls):
    """A non-axial face whose normal points up like a floor/ceiling (a slope the player stands on)."""
    return any(RAMP_NZ < abs(n[2]) < 0.9999 for n in pls)


class Brush:
    __slots__ = ("contents", "planes", "verts", "lo", "hi", "boxed")

    def __init__(self, contents, planes, verts):
        self.contents = contents
        self.verts = verts
        self.lo, self.hi = aabb(verts)
        self.planes = planes
        self.boxed = is_box(nplanes(planes))

    def klass(self):
        """Texture class the emitter maps this brush to; brushes only merge within the same class."""
        import clip_brushes as cb
        return cb.texture_for(self.contents)


def drop_redundant(b):
    """Pass 0: keep the 6 axial AABB planes + every oblique plane a vertex supports; AABB-cap if still > 45 sides."""
    lo, hi = b.lo, b.hi
    axial = box_planes(lo, hi)
    pls = nplanes(b.planes)
    obliques = []
    for n in pls:
        if max(abs(n[0]), abs(n[1]), abs(n[2])) > 0.9999:
            continue  # axial handled by the canonical AABB six
        if any(abs(n[0] * v[0] + n[1] * v[1] + n[2] * v[2] - n[3]) <= VERT_EPS for v in b.verts):
            obliques.append([n[0], n[1], n[2], n[3]])
    if len(axial) + len(obliques) > MAX_SIDES:
        b.planes, b.boxed = axial, True  # pathological fan -> AABB (rare; logged by caller)
        b.verts = box_corners(lo, hi)
        return True
    b.planes = axial + obliques
    b.boxed = not obliques
    return False


def inside(b, corners):
    """Every given point satisfies all of b's planes (within a small slack)?"""
    pls = nplanes(b.planes)
    return all(all(a * p[0] + q * p[1] + r * p[2] <= d + 0.05 for a, q, r, d in pls) for p in corners)


def bucketise(brushes, cell):
    grid = defaultdict(list)
    for i, b in enumerate(brushes):
        for cx in range(int(b.lo[0] // cell), int(b.hi[0] // cell) + 1):
            for cy in range(int(b.lo[1] // cell), int(b.hi[1] // cell) + 1):
                grid[(cx, cy)].append(i)
    return grid


def contain_drop(brushes):
    """Pass 1: drop a brush whose AABB lies wholly inside another same-class brush's solid."""
    vol = lambda b: max(0.0, b.hi[0] - b.lo[0]) * max(0.0, b.hi[1] - b.lo[1]) * max(0.0, b.hi[2] - b.lo[2])
    grid = bucketise(brushes, 256)
    dead = set()
    for idxs in grid.values():
        for i in idxs:
            if i in dead:
                continue
            ci = box_corners(brushes[i].lo, brushes[i].hi)
            for j in idxs:
                if i == j or j in dead or brushes[j].klass() != brushes[i].klass():
                    continue
                if vol(brushes[j]) >= vol(brushes[i]) and inside(brushes[j], ci):
                    dead.add(i)
                    break
    return [b for k, b in enumerate(brushes) if k not in dead], len(dead)


def boxify(brushes, tol, floor_tol):
    """Pass 2: swap near-box brushes for their AABB; keep ramps whose rise exceeds step noise."""
    done = 0
    for b in brushes:
        if b.boxed:
            continue
        pls = nplanes(b.planes)
        if protrusion(b.lo, b.hi, pls) > tol:
            continue
        if ramp_top(pls) and (b.hi[2] - b.lo[2]) > floor_tol:
            continue  # a real slope the player walks up; flattening would move stand height
        b.planes = box_planes(b.lo, b.hi)
        b.verts = box_corners(b.lo, b.hi)
        b.boxed = True
        done += 1
    return done


def box_merge(brushes):
    """Pass 3: fuse axis-aligned boxes with equal cross-section, class and face adjacency (exact volume)."""
    boxes = [i for i, b in enumerate(brushes) if b.boxed]
    live = {i: [list(brushes[i].lo), list(brushes[i].hi)] for i in boxes}
    changed = True
    while changed:
        changed = False
        for axis in range(3):
            o1, o2 = [a for a in range(3) if a != axis]
            buckets = defaultdict(list)
            for i, (lo, hi) in live.items():
                key = (brushes[i].klass(), round(lo[o1] / EPS), round(hi[o1] / EPS), round(lo[o2] / EPS), round(hi[o2] / EPS))
                buckets[key].append(i)
            for idxs in buckets.values():
                idxs.sort(key=lambda i: live[i][0][axis])
                prev = None
                for i in idxs:
                    if prev is not None and abs(live[prev][1][axis] - live[i][0][axis]) <= EPS:
                        live[prev][1][axis] = live[i][1][axis]
                        del live[i]
                        changed = True
                    else:
                        prev = i
    kept = [b for i, b in enumerate(brushes) if not b.boxed]
    for i, (lo, hi) in live.items():
        nb = Brush(brushes[i].contents, box_planes(lo, hi), box_corners(lo, hi))
        kept.append(nb)
    return kept, len(boxes) - len(live)


def cluster_aabb(brushes, cell):
    """Pass 4 (--cluster): replace each dense cell of leftover oblique brushes with one class AABB. LOSES concavity."""
    obl = [i for i, b in enumerate(brushes) if not b.boxed]
    grid = defaultdict(list)
    for i in obl:
        b = brushes[i]
        cx, cy, cz = int((b.lo[0] + b.hi[0]) / 2 // cell), int((b.lo[1] + b.hi[1]) / 2 // cell), int((b.lo[2] + b.hi[2]) / 2 // cell)
        grid[(brushes[i].klass(), cx, cy, cz)].append(i)
    drop, add, fused = set(), [], 0
    for key, idxs in grid.items():
        if len(idxs) < 3:
            continue  # only collapse genuine clusters
        lo = [min(brushes[i].lo[a] for i in idxs) for a in range(3)]
        hi = [max(brushes[i].hi[a] for i in idxs) for a in range(3)]
        if max(hi[a] - lo[a] for a in range(3)) > cell * 1.5:
            continue  # spread too far -> would fill open space
        drop.update(idxs)
        add.append(Brush(brushes[idxs[0]].contents, box_planes(lo, hi), box_corners(lo, hi)))
        fused += len(idxs)
    return [b for k, b in enumerate(brushes) if k not in drop] + add, fused


def table_of(brushes, passthrough, tris, tri_contents, tri_materials):
    """Current cod2map plane-table size (unique undirected x2) for the whole clip set."""
    out = emit(brushes, passthrough, tris, tri_contents, tri_materials)
    tmp = Path(pc.__file__).with_name("_decimate_tmp.json")
    tmp.write_text(json.dumps(out))
    try:
        bpl, ppl, _, _ = pc.clip_planes(str(tmp))
        uniq = {k for k in (pc.canonical(p, 0.001, 0.01) for p in bpl + ppl) if k}
    finally:
        tmp.unlink(missing_ok=True)
    return len(uniq) * 2, len(uniq)


def emit(brushes, passthrough, tris, tri_contents, tri_materials):
    out = {"brushes": []}
    for b in brushes:
        d = {"contents": b.contents, "planes": [[round(x, 6) for x in p] for p in b.planes], "verts": [list(v) for v in b.verts]}
        out["brushes"].append(d)
    out["brushes"].extend(passthrough)
    if tris:
        out["tris"] = tris
    if tri_contents:
        out["tri_contents"] = tri_contents
    if tri_materials:
        out["tri_materials"] = tri_materials
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("outp")
    ap.add_argument("--target-planes", type=int, default=120000, help="cod2map plane TABLE size target (unique x2)")
    ap.add_argument("--tol", type=float, default=8.0, help="starting AABB protrusion tolerance (units)")
    ap.add_argument("--max-tol", type=float, default=64.0)
    ap.add_argument("--floor-tol", type=float, default=8.0, help="max rise of a ramp we are willing to flatten")
    ap.add_argument("--cluster", action="store_true", help="aggressive: collapse dense oblique clusters to AABBs (loses concavity)")
    ap.add_argument("--cluster-cell", type=float, default=128.0)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    data = json.loads(Path(args.inp).read_text())
    emitted, passthrough = [], []
    for b in data.get("brushes", []):
        if pc.emitted_brush_planes(b) is None:
            passthrough.append(b)  # the emitter skips it anyway; keep bytes intact
        else:
            emitted.append(Brush(b.get("contents", 1), b["planes"], [list(v) for v in b["verts"]]))
    tris = data.get("tris") or []
    tri_contents = data.get("tri_contents") or []
    tri_materials = data.get("tri_materials") or []

    before_table, before_uniq = table_of(emitted, passthrough, tris, tri_contents, tri_materials)
    log = {"input": args.inp, "before": {"brushes_emitted": len(emitted), "passthrough": len(passthrough),
           "unique_planes": before_uniq, "plane_table": before_table, "cap": 131072}, "passes": []}

    capped = sum(drop_redundant(b) for b in emitted)
    emitted, dropped = contain_drop(emitted)
    log["passes"].append({"pass": "redundant+contain", "aabb_capped_over45": capped, "contained_dropped": dropped,
                          "brushes": len(emitted)})

    tol = min(args.tol, args.max_tol)
    while True:
        boxed = boxify(emitted, tol, args.floor_tol)
        emitted, merged = box_merge(emitted)
        tbl, uq = table_of(emitted, passthrough, tris, tri_contents, tri_materials)
        log["passes"].append({"pass": f"boxify(tol={tol})+merge", "boxified": boxed, "merged": merged,
                              "brushes": len(emitted), "unique_planes": uq, "plane_table": tbl})
        if tbl <= args.target_planes or tol >= args.max_tol:
            break  # done, or reached the aggressiveness ceiling (raise --max-tol to push further)
        tol = min(tol * 2, args.max_tol)

    if args.cluster and tbl > args.target_planes:
        emitted, fused = cluster_aabb(emitted, args.cluster_cell)
        emitted, merged = box_merge(emitted)
        tbl, uq = table_of(emitted, passthrough, tris, tri_contents, tri_materials)
        log["passes"].append({"pass": "cluster", "fused_brushes": fused, "merged": merged,
                              "brushes": len(emitted), "unique_planes": uq, "plane_table": tbl})

    out = emit(emitted, passthrough, tris, tri_contents, tri_materials)
    Path(args.outp).write_text(json.dumps(out))
    after_table, after_uniq = tbl, uq
    log["after"] = {"brushes_emitted": len(emitted), "unique_planes": after_uniq, "plane_table": after_table,
                    "under_cap": after_table <= 131072, "under_target": after_table <= args.target_planes}
    log["reduction_pct"] = round(100 * (before_uniq - after_uniq) / max(before_uniq, 1), 1)
    if args.report:
        args.report.write_text(json.dumps(log, indent=1))
    print(f"{args.inp} -> {args.outp}")
    print(f"  brushes {len(data.get('brushes', []))} -> emitted {len(emitted)} (+{len(passthrough)} passthrough, {len(tris)} tris)")
    print(f"  unique planes {before_uniq} -> {after_uniq}  (table {before_table} -> {after_table}; cap 131072; target {args.target_planes})")
    print(f"  reduction {log['reduction_pct']}%  under_cap={log['after']['under_cap']} under_target={log['after']['under_target']}")


if __name__ == "__main__":
    main()
