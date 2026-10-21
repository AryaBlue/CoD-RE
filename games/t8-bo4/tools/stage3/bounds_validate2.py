"""Vectorised bounds oracle + base scorer. Fields extracted via strided numpy views; name-hash
gathered by fancy indexing; bounds transform looped only over hash hits. Fast (<10s)."""
import json
import os
import re
import sys
import numpy as np
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # smodel_lib in ../
from smodel_lib import axis_to_angles  # noqa: E402

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
RIP = r"PATH/TO/exported_xmodels"  # set this to your own path
ARRAY, COUNT, STRIDE = 0x1D3898E4, 42559, 0x60
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
    d = open(p, "rb").read()
    nv = d.find(b"NUMVERTS")
    v = OFFSET_RE.findall(d, nv if nv >= 0 else 0)
    if not v:
        return None
    a = np.array([[float(x) for x in t] for t in v])
    return a.min(0), a.max(0)


def gather_u64(data, offs):
    """u64 little-endian at arbitrary byte offsets (numpy)."""
    offs = offs.astype(np.int64)
    out = np.zeros(len(offs), dtype=np.uint64)
    for j in range(8):
        out |= data[offs + j].astype(np.uint64) << np.uint64(8 * j)
    return out


def main(base_a=0x13A3D948, sweep=False):
    import mmap
    _f = open(DEC, "rb"); _mm = mmap.mmap(_f.fileno(), 0, access=mmap.ACCESS_READ)
    data = np.frombuffer(_mm, dtype=np.uint8); n = data.size
    print(f"mapped {n:,} bytes", flush=True)
    f4 = data[:(n // 4) * 4].view("<f4")
    u32 = data[:(n // 4) * 4].view("<u4")
    b = ARRAY // 4
    k = np.arange(COUNT)
    idx = b + k * 24
    origin = np.stack([f4[idx], f4[idx + 1], f4[idx + 2]], 1).astype(np.float64)
    isa = np.stack([f4[idx + 3 + j] for j in range(9)], 1).astype(np.float64).reshape(COUNT, 3, 3)
    amn = np.stack([f4[idx + 12], f4[idx + 13], f4[idx + 14]], 1).astype(np.float64)
    amx = np.stack([f4[idx + 15], f4[idx + 16], f4[idx + 17]], 1).astype(np.float64)
    low = u32[b + k * 24 + 21].astype(np.int64)
    high = u32[b + k * 24 + 22]
    valid = high == 0x40000000

    names = [d for d in os.listdir(RIP) if os.path.isdir(os.path.join(RIP, d))]
    M60 = np.uint64(0x0FFFFFFFFFFFFFFF)
    hmap = {}
    for nm in names:
        hmap.setdefault(hash64(nm) & 0x0FFFFFFFFFFFFFFF, nm)  # 60-bit FNV-1a (confirmed T8 xmodel name hash)
    hset = np.array(sorted(hmap.keys()), dtype=np.uint64)

    def score(base, emit=False):
        tgt = base + (low - 1)
        ok = valid & (tgt >= 0) & (tgt + 8 <= n)
        nh = np.zeros(COUNT, dtype=np.uint64)
        nh[ok] = gather_u64(data, tgt[ok]) & M60
        named_mask = ok & np.isin(nh, hset)
        hits = np.nonzero(named_mask)[0]
        passed = 0
        out = []
        for i in hits:
            name = hmap.get(int(nh[i]))
            lb = local_aabb(name)
            if lb is None:
                continue
            try:
                sA = np.linalg.inv(isa[i])
            except np.linalg.LinAlgError:
                continue
            lo, hi = lb
            corners = np.array([[lo[0] if c & 1 else hi[0], lo[1] if c & 2 else hi[1], lo[2] if c & 4 else hi[2]] for c in range(8)])
            world = origin[i] + corners @ sA.T
            err = float(max(np.abs(world.min(0) - amn[i]).max(), np.abs(world.max(0) - amx[i]).max()))
            if err < 6.0:
                passed += 1
                if emit:
                    rn = [np.linalg.norm(isa[i][r]) for r in range(3)]
                    s = 1.0 / (sum(rn) / 3.0)
                    axis = [float(x) for x in (s * isa[i].T).flatten()]
                    out.append({"model": name, "origin": [round(float(x), 4) for x in origin[i]],
                                "angles": [round(x, 4) for x in axis_to_angles(axis)], "scale": round(s, 6),
                                "axis": [round(x, 6) for x in axis], "bounds_err": round(err, 3), "rec": int(i)})
        return len(hits), passed, out

    if sweep:
        print("base sweep (named, passed):")
        best = (0, -1)
        for d in range(-0x4000, 0x4001, 0x4):
            base = base_a + d
            nhits, pz, _ = score(base)
            if pz > best[1]:
                best = (base, pz)
            if pz > 5:
                print(f"  base 0x{base:x} (A{d:+#x}): named={nhits} passed={pz}")
        print(f"BEST base 0x{best[0]:x} passed={best[1]}")
        return
    nhits, pz, out = score(base_a, emit=True)
    print(f"base 0x{base_a:x}: named={nhits} bounds-PASS(<6u)={pz} distinct_models={len({r['model'] for r in out})}")
    from collections import Counter
    print("top passing:", Counter(r['model'] for r in out).most_common(8))
    for r in out[:6]:
        print(f"  {r['model']} origin={r['origin']} angles={r['angles']} scale={r['scale']} err={r['bounds_err']}")
    json.dump(out, open(r"PATH/TO/validated_baseA.json", "w"))


if __name__ == "__main__":
    main(sweep="--sweep" in sys.argv)
