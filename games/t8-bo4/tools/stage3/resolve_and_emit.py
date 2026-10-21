"""Resolve each clip static-model placement's XModel name and emit the MotD smodel JSON.

Array @0x1D3898E4, 42559 x 0x60. Fields: +0x00 origin f3, +0x0c invScaledAxis f3x3,
+0x30 absmin f3, +0x3c absmax f3, +0x4c flags u32, +0x54 xmodel ptr u64, +0x5c contents u32.
Ptr form 0x40000000_XXXXXXXX; target = base + (XXXXXXXX-1). base is SOLVED here (not the
clip-internal 0x101DF9EC) by matching XModel.name hashes of the 6092 Greyhound rip names.
Transform: invScaledAxis = (1/s) axis^T  ->  axis = s*invScaledAxis^T, s = 1/row_norm. angles via smodel_lib.
Output schema per record: {model, source, origin[3], angles[3], scale, axis[9], flags, contents}."""
import json
import math
import os
import sys
import struct
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # smodel_lib in ../
from smodel_lib import axis_to_angles  # noqa: E402

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
RIP_XMODELS = r"PATH/TO/exported_xmodels"  # set this to your own path
OUT = r"PATH/TO/bod_props.json"  # set this to your own path
ARRAY, COUNT, STRIDE = 0x1D3898E4, 42559, 0x60


def hash64(s):
    s = s.lower().replace("\\", "/")
    h = 0xCBF29CE484222325
    for b in s.encode():
        h = (0x100000001B3 * (b ^ h)) & 0xFFFFFFFFFFFFFFFF
    return h


def main():
    names = sorted(d for d in os.listdir(RIP_XMODELS) if os.path.isdir(os.path.join(RIP_XMODELS, d)))
    print(f"rip model names: {len(names)}")
    # hash -> name, across masks
    hmap = {}
    for nm in names:
        h = hash64(nm)
        for v in (h, h & 0x7FFFFFFFFFFFFFFF, h & 0x0FFFFFFFFFFFFFFF):
            hmap.setdefault(v, nm)
    targets = np.array(sorted(hmap.keys()), dtype=np.uint64)
    print(f"distinct target hashes: {len(targets)}")

    data = np.fromfile(DEC, dtype=np.uint8)
    n = data.size
    v32 = data[: (n // 4) * 4].view("<u4")
    # scan u64 at every 4-byte offset for membership in targets
    hit_off = {}  # byte offset -> hash value
    C = 16_000_000
    for s in range(0, len(v32) - 1, C):
        e = min(s + C, len(v32) - 1)
        lo = v32[s:e].astype(np.uint64)
        hi = v32[s + 1:e + 1].astype(np.uint64)
        val = lo | (hi << np.uint64(32))
        m = np.isin(val, targets)
        for j in np.nonzero(m)[0]:
            hit_off[(s + j) * 4] = int(val[j])
    print(f"XModel.name hash hits in zone: {len(hit_off)} (distinct names {len({hmap[h] for h in hit_off.values()})})")

    # distinct model ptr lows from records
    buf = memoryview(data)  # zero-copy view over the uint8 array for struct reads
    def u64(o): return int.from_bytes(buf[o:o + 8], "little")
    def u32(o): return int.from_bytes(buf[o:o + 4], "little")
    def f3(o): return struct.unpack_from("<3f", buf, o)
    def f9(o): return struct.unpack_from("<9f", buf, o)

    lows = set()
    for i in range(COUNT):
        p = u64(ARRAY + i * STRIDE + 0x54)
        if (p >> 32) == 0x40000000:
            lows.add(p & 0xFFFFFFFF)
    print(f"records {COUNT}, distinct 0x40000000 model-ptr lows: {len(lows)}")

    # SOLVE base: candidate = O - (low-1) must be a hash-hit offset for a referenced model
    cand = Counter()
    hit_set = set(hit_off.keys())
    for low in lows:
        for O in hit_set:
            b = O - (low - 1)
            if 0 <= b < n:
                cand[b] += 1
    if not cand:
        print("NO base candidates — XModel structs not located by name hashes.")
        return
    base, votes = cand.most_common(1)[0]
    second = cand.most_common(2)[1][1] if len(cand) > 1 else 0
    print(f"SOLVED base = 0x{base:x} with {votes} votes (next best {second})")

    # Resolve + emit
    out, resolved, missing_hash, bad_ptr = [], 0, 0, 0
    miss_names = Counter()
    for i in range(COUNT):
        R = ARRAY + i * STRIDE
        origin = list(f3(R))
        isa = f9(R + 0x0C)
        flags = u32(R + 0x4C)
        p = u64(R + 0x54)
        contents = u32(R + 0x5C)
        if (p >> 32) != 0x40000000:
            bad_ptr += 1
            continue
        tgt = base + ((p & 0xFFFFFFFF) - 1)
        nh = u64(tgt) if 0 <= tgt + 8 <= n else 0
        name = hmap.get(nh) or hmap.get(nh & 0x7FFFFFFFFFFFFFFF) or hmap.get(nh & 0x0FFFFFFFFFFFFFFF)
        # transform: axis = s * invScaledAxis^T
        M = np.array(isa, dtype=np.float64).reshape(3, 3)
        rn = [np.linalg.norm(M[r]) for r in range(3)]
        if min(rn) < 1e-6 or not all(math.isfinite(x) for x in origin + list(isa)):
            # degenerate (null/box record) - skip quietly
            continue
        s = 1.0 / (sum(rn) / 3.0)
        axisM = s * M.T
        axis = [float(x) for x in axisM.flatten()]
        det = float(np.linalg.det(axisM))
        angles = axis_to_angles(axis)
        rec = {"model": name, "source": name, "origin": [round(x, 4) for x in origin],
               "angles": [round(x, 4) for x in angles], "scale": round(s, 6),
               "axis": [round(x, 6) for x in axis], "flags": int(flags), "contents": int(contents),
               "name_hash": f"0x{nh:016x}", "det": round(det, 3)}
        if name:
            resolved += 1
        else:
            missing_hash += 1
            miss_names[f"0x{nh:016x}"] += 1
        out.append(rec)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"))
    inrip = len({r["model"] for r in out if r["model"]})
    print(f"\nemitted {len(out)} placements -> {OUT}")
    print(f"  resolved to a name: {resolved}; unresolved hash: {missing_hash}; non-0x40000000 ptr: {bad_ptr}")
    print(f"  distinct resolved models: {inrip}")
    neg = sum(1 for r in out if r.get('det', 1) < 0)
    print(f"  mirrored (det<0): {neg}")
    print("  first 6 resolved:")
    for r in [x for x in out if x["model"]][:6]:
        print(f"    {r['model']}  origin={r['origin']} angles={r['angles']} scale={r['scale']} det={r['det']}")
    if missing_hash:
        print(f"  top unresolved hashes: {miss_names.most_common(6)}")


if __name__ == "__main__":
    main()
