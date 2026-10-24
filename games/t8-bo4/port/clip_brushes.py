"""T6 clipmap (brush planes + collision triangles, as JSON) -> iwmap clip brushes for the worldspawn, so cod2map
builds player collision and the navmesh from them. Face points follow the template: (p2-p0) x (p1-p0) = outward normal."""
import json
import math

SUFFIX = " 128 128 0 0 0 0 lightmap_gray 16384 16384 0 0 0 0"
SOLID, PLAYERCLIP, MONSTERCLIP, CLIPSHOT, MISSILECLIP = 0x1, 0x10000, 0x20000, 0x2000, 0x80
PRISM_DEPTH = 4.0


def norm(v):
    length = math.sqrt(sum(c * c for c in v))
    return [c / length for c in v] if length > 1e-9 else None


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def face(n, d, centre, texture):
    """Plane n.x = d (n outward) as three points around the projection of the brush centre."""
    p0 = [c - (sum(a * b for a, b in zip(n, centre)) - d) * k for c, k in zip(centre, n)]
    helper = [0, 0, 1] if abs(n[2]) < 0.9 else [1, 0, 0]
    u = norm(cross(helper, n))
    v = cross(n, u)  # u x v = n, so p1 = p0 + v, p2 = p0 + u gives (p2-p0) x (p1-p0) = n
    p1 = [a + 64 * b for a, b in zip(p0, v)]
    p2 = [a + 64 * b for a, b in zip(p0, u)]
    return " " + " ".join("( " + " ".join(f"{c:.4f}" for c in p) + " )" for p in (p0, p1, p2)) + f" {texture}{SUFFIX}"


def axial_centre(planes):
    """Middle of the brush's axial bounds (the +/- axis planes every T6 brush carries)."""
    lo, hi = [None] * 3, [None] * 3
    for n, d in planes:
        for axis in range(3):
            if abs(n[axis]) > 0.9999:
                if n[axis] > 0:
                    hi[axis] = d
                else:
                    lo[axis] = -d
    return None if None in lo or None in hi else [(a + b) / 2 for a, b in zip(lo, hi)]


def texture_for(contents):
    if contents & SOLID or contents & PLAYERCLIP and contents & MONSTERCLIP:
        return "clip"
    if contents & PLAYERCLIP:
        return "clip_player"
    if contents & MONSTERCLIP:
        return "clip_ai"
    if contents & (CLIPSHOT | MISSILECLIP):
        return "clip_weapon"  # bullets only; the shell xmodels carry no collision of their own
    return None


def brush_text(planes, centre, texture):
    faces = [face(n, d, centre, texture) for n, d in planes]
    return "{\n" + "\n".join(faces) + "\n}\n"


def prism(tri, texture):
    a, b, c = tri
    n = norm(cross(sub(b, a), sub(c, a)))
    if n is None:
        return None
    centre = [(x + y + z) / 3 - PRISM_DEPTH / 2 * k for x, y, z, k in zip(a, b, c, n)]
    d = sum(x * y for x, y in zip(n, a))
    planes = [(n, d), ([-k for k in n], -(d - PRISM_DEPTH))]
    for p, q in ((a, b), (b, c), (c, a)):
        side = norm(cross(sub(q, p), n))
        if side is None:
            return None
        if sum(s * (m - x) for s, m, x in zip(side, centre, p)) > 0:
            side = [-s for s in side]
        planes.append((side, sum(s * x for s, x in zip(side, p))))
    return brush_text(planes, centre, texture)


def patch(tri, texture):
    """One collision tri as a 2x2 patch mesh with a collapsed corner (stock maps collapse patch verts the same way)."""
    a, b, c = tri
    if norm(cross(sub(b, a), sub(c, a))) is None:
        return None
    row = lambda p, q: "   (\n" + "".join(f"\tv {x:g} {y:g} {z:g} t 0 0 0 0\n" for x, y, z in (p, q)) + "   )\n"
    return f"{{\n  mesh\n  {{\n  toolFlags;\n   {texture}\n   lightmap_gray\n   2 2 0 8\n{row(a, b)}{row(c, c)}  }}\n}}\n"


def patches(path):
    """Clip patch meshes for every tri of a clip.json (no brush planes, so they don't count against MAX_MAP_PLANES)."""
    data = json.loads(open(path).read())
    tri_contents = data.get("tri_contents") or []
    out, skipped = [], 0
    for i, tri in enumerate(data.get("tris", [])):
        texture = texture_for(tri_contents[i] if i < len(tri_contents) else SOLID)
        text = texture and patch(tri[:3], texture)
        if text:
            out.append(text)
        else:
            skipped += 1
    return out, skipped


def brushes(path):
    """All clip brushes from the worker's clip.json, as iwmap "// brush" blocks (guids added by the caller)."""
    data = json.loads(open(path).read())
    out, skipped = [], 0
    for brush in data.get("brushes", []):
        texture = texture_for(brush.get("contents", SOLID))
        planes = [(norm(p[:3]), p[3]) for p in brush["planes"]]
        if texture is None or len(planes) < 4 or any(n is None for n, _ in planes):
            skipped += 1
            continue
        centre = brush.get("centre") or ([sum(v[i] for v in brush["verts"]) / len(brush["verts"]) for i in range(3)]
                                          if brush.get("verts") else axial_centre(planes))
        extent = min(planes[i][1] + planes[i + 1][1] for i in (0, 2, 4))  # axial pairs come first: -X +X -Y +Y -Z +Z
        if centre is None or extent > 4096:
            skipped += 1  # 4096+ on every axis is no real wall (zm_prison has one 22k cube at the origin that buries every node)
            continue
        out.append(brush_text(planes, centre, texture))
    tri_contents = data.get("tri_contents") or []
    for i, tri in enumerate(data.get("tris", [])):
        verts, contents = (tri["verts"], tri.get("contents", SOLID)) if isinstance(tri, dict) else \
            (tri[:3], tri_contents[i] if i < len(tri_contents) else SOLID)
        texture = texture_for(contents)
        text = texture and prism(verts, texture)
        if text:
            out.append(text)
        else:
            skipped += 1
    return out, skipped
