"""Bounds oracle: for each clip static-model record, resolve its XModel name (base_A + T8 hash),
load that rip model's LOD0 local vertex AABB, transform by the record's placement
(world = origin + inverse(invScaledAxis) @ local), and compare the resulting world AABB to the
record's own absmin/absmax (+0x30/+0x3C). Accept only matches within tolerance.
This both ground-truths base_A and filters false hash matches."""
import json
import math
import os
import re
import struct
import sys
import numpy as np
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # smodel_lib in ../
from smodel_lib import axis_to_angles  # noqa: E402

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
RIP = r"PATH/TO/exported_xmodels"  # set this to your own path
ARRAY, COUNT, STRIDE = 0x1D3898E4, 42559, 0x60
BASE_A = 0x13A3D948
OFFSET_RE = re.compile(rb"OFFSET ([-0-9.eE]+), ([-0-9.eE]+), ([-0-9.eE]+)")


def hash64(s):
    s = s.lower().replace("\\", "/"); h = 0xCBF29CE484222325
    for b in s.encode():
        h = (0x100000001B3 * (b ^ h)) & 0xFFFFFFFFFFFFFFFF
    return h


@lru_cache(maxsize=None)
def local_aabb(name):
    p = os.path.join(RIP, name, f"{name}_LOD0.XMODEL_EXPORT")
    if not os.path.isfile(p):
        return None
    data = open(p, "rb").read()
    nv = data.find(b"NUMVERTS")
    if nv < 0:
        return None
    verts = OFFSET_RE.findall(data, nv)  # only after NUMVERTS -> skips bone OFFSET
    if not verts:
        return None
    a = np.array([[float(x) for x in v] for v in verts])
    return a.min(0), a.max(0)


def main():
    data = np.fromfile(DEC, dtype=np.uint8); n = data.size; buf = memoryview(data)
    def u64(o): return int.from_bytes(buf[o:o + 8], "little")
    def f3(o): return np.array(struct.unpack_from("<3f", buf, o))
    def f9(o): return struct.unpack_from("<9f", buf, o)

    names = [d for d in os.listdir(RIP) if os.path.isdir(os.path.join(RIP, d))]
    hmap = {}
    for nm in names:
        h = hash64(nm)
        for v in (h, h & 0x7FFFFFFFFFFFFFFF, h & 0x0FFFFFFFFFFFFFFF):
            hmap.setdefault(v, nm)

    named = passed = nobound = 0
    errs = []
    out = []
    for i in range(COUNT):
        R = ARRAY + i * STRIDE
        p = u64(R + 0x54)
        if (p >> 32) != 0x40000000:
            continue
        tgt = BASE_A + ((p & 0xFFFFFFFF) - 1)
        nh = u64(tgt) if 0 <= tgt + 8 <= n else 0
        name = hmap.get(nh) or hmap.get(nh & 0x7FFFFFFFFFFFFFFF) or hmap.get(nh & 0x0FFFFFFFFFFFFFFF)
        if not name:
            continue
        named += 1
        lb = local_aabb(name)
        if lb is None:
            nobound += 1
            continue
        origin = f3(R)
        isa = np.array(f9(R + 0x0C)).reshape(3, 3)
        try:
            scaledAxis = np.linalg.inv(isa)
        except np.linalg.LinAlgError:
            continue
        amn, amx = f3(R + 0x30), f3(R + 0x3C)
        lo, hi = lb
        corners = np.array([[lo[0] if c & 1 else hi[0], lo[1] if c & 2 else hi[1], lo[2] if c & 4 else hi[2]] for c in range(8)])
        world = origin + corners @ scaledAxis.T
        wmn, wmx = world.min(0), world.max(0)
        err = float(max(np.abs(wmn - amn).max(), np.abs(wmx - amx).max()))
        errs.append(err)
        if err < 6.0:
            passed += 1
            # emit transform: axis = s*invScaledAxis^T, s=1/rownorm
            rn = [np.linalg.norm(isa[r]) for r in range(3)]
            s = 1.0 / (sum(rn) / 3.0)
            axisM = s * isa.T
            axis = [float(x) for x in axisM.flatten()]
            out.append({"model": name, "origin": [round(float(x), 4) for x in origin],
                        "angles": [round(x, 4) for x in axis_to_angles(axis)], "scale": round(s, 6),
                        "axis": [round(x, 6) for x in axis], "bounds_err": round(err, 3), "rec": i})
    errs = np.array(errs) if errs else np.array([0.0])
    print(f"named(base_A+hash): {named}; with rip bounds: {named - nobound}; bounds-PASS(<6u): {passed}")
    print(f"bounds-err over named+bounded: median={np.median(errs):.2f} p10={np.percentile(errs,10):.2f} "
          f"p25={np.percentile(errs,25):.2f} min={errs.min():.2f}  (<6u:{(errs<6).sum()} <20u:{(errs<20).sum()} <100u:{(errs<100).sum()})")
    print(f"distinct passing models: {len({r['model'] for r in out})}")
    from collections import Counter
    cc = Counter(r['model'] for r in out)
    print("top passing models:", cc.most_common(8))
    json.dump(out, open(r"PATH/TO/validated_baseA.json", "w"))


if __name__ == "__main__":
    main()
