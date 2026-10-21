"""BoD (T8) clipMap brushes -> clip.json (EMITTER_SPEC.md schema), from the decompressed zm_escape zone.
Usage: clip_t8.py <zm_escape.ff.dec> <out clip.json>"""
import json
import struct
import sys
from collections import Counter

import numpy as np

CLIPINFO = 0x1D2FF450      # inline ClipInfo: (u32 count, u32 pad, u64 ptr) pairs
PLANES = 0x1E26F52C        # cplane_s[37346], 20 B: normal, dist, type, signbits
BRUSHES = 0x1E64BD74       # cbrush_t[12892], 64 B (layout below)
PTR_DELTA = 0x101DF9EC     # zone pointer 0x40000000_XXXXXXXX -> file offset (XXXXXXXX - 1) + delta (this block)
BRUSH = np.dtype([("sides", "<u8"), ("verts", "<u8"), ("mins", "<3f4"), ("contents", "<u4"), ("maxs", "<3f4"),
                  ("axial_mat", "<6u2"), ("numverts", "<u2"), ("numsides", "<u2"), ("pad", "<u4")])


def ptr(p):
    assert p >> 56 == 0x40, hex(p)
    return (p & 0xFFFFFFFF) - 1 + PTR_DELTA


def main():
    zone, out = sys.argv[1], sys.argv[2]
    with open(zone, "rb") as f:
        f.seek(CLIPINFO)
        counts = [struct.unpack("<I4xQ", f.read(16))[0] for _ in range(9)]
        n_planes, n_brushes = counts[0], counts[5]
        f.seek(PLANES)
        planes = np.frombuffer(f.read(n_planes * 20), np.dtype([("n", "<3f4"), ("d", "<f4"), ("type", "u1"), ("sign", "u1"), ("pad", "<2u1")]))
        f.seek(BRUSHES)
        brushes = np.frombuffer(f.read(n_brushes * 64), BRUSH)
        verts_of = []
        for b in brushes:
            if b["numverts"]:
                f.seek(ptr(int(b["verts"])))
                verts_of.append(np.frombuffer(f.read(12 * int(b["numverts"])), "<3f4").astype(float))
            else:
                verts_of.append(np.zeros((0, 3)))
    plane_base = ptr(int(brushes[0]["sides"]))
    assert plane_base == PLANES, hex(plane_base)
    out_brushes, outside, flipped = [], 0, 0
    for b, verts in zip(brushes, verts_of):
        lo, hi = b["mins"].astype(float), b["maxs"].astype(float)
        planes_b = [[-1, 0, 0, -lo[0]], [1, 0, 0, hi[0]], [0, -1, 0, -lo[1]], [0, 1, 0, hi[1]], [0, 0, -1, -lo[2]], [0, 0, 1, hi[2]]]
        first = (ptr(int(b["sides"])) - PLANES) // 20 if b["numsides"] else 0
        for p in planes[first:first + int(b["numsides"])]:
            planes_b.append([*p["n"].astype(float).tolist(), float(p["d"])])
        if len(verts) and any(max(np.dot(verts, q[:3]) - q[3]) > 0.5 for q in planes_b[6:]):
            outside += 1
        out_brushes.append({"contents": int(b["contents"]), "planes": planes_b, "verts": verts.round(3).tolist()})
    json.dump({"brushes": out_brushes, "tris": [], "tri_contents": []}, open(out, "w"))
    allv = np.vstack([v for v in verts_of if len(v)])
    print(f"ClipInfo counts {counts}")
    print(f"{len(out_brushes)} brushes, {sum(len(b['planes']) - 6 for b in out_brushes)} side planes, "
          f"{outside} brushes with corners outside their side planes; corner bounds {allv.min(0).round()} .. {allv.max(0).round()}")
    print("contents", Counter(hex(b["contents"]) for b in out_brushes).most_common(12))


if __name__ == "__main__":
    main()
