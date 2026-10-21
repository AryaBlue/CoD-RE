"""Diagnose why ~84% of placements don't resolve: classify each record's model-ptr target
under base A, histogram the low ranges, and search for a second base that recovers the
tiny-int / pointer-form targets."""
import os
import struct
import numpy as np
from collections import Counter

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
RIP_XMODELS = r"PATH/TO/exported_xmodels"  # set this to your own path
ARRAY, COUNT, STRIDE = 0x1D3898E4, 42559, 0x60
BASE_A = 0x13A3D948


def hash64(s):
    s = s.lower().replace("\\", "/"); h = 0xCBF29CE484222325
    for b in s.encode():
        h = (0x100000001B3 * (b ^ h)) & 0xFFFFFFFFFFFFFFFF
    return h


def main():
    names = sorted(d for d in os.listdir(RIP_XMODELS) if os.path.isdir(os.path.join(RIP_XMODELS, d)))
    hmap = {}
    for nm in names:
        h = hash64(nm)
        for v in (h, h & 0x7FFFFFFFFFFFFFFF, h & 0x0FFFFFFFFFFFFFFF):
            hmap.setdefault(v, nm)
    data = np.fromfile(DEC, dtype=np.uint8); n = data.size; buf = memoryview(data)
    def u64(o): return int.from_bytes(buf[o:o + 8], "little")

    lows = []
    for i in range(COUNT):
        p = u64(ARRAY + i * STRIDE + 0x54)
        lows.append(p & 0xFFFFFFFF if (p >> 32) == 0x40000000 else None)
    valid = [l for l in lows if l is not None]
    print(f"low range: min=0x{min(valid):x} max=0x{max(valid):x}  distinct={len(set(valid))}")

    # classify target under base A
    def classify(nh):
        if nh in hmap or (nh & 0x7FFFFFFFFFFFFFFF) in hmap or (nh & 0x0FFFFFFFFFFFFFFF) in hmap:
            return "rip"
        if nh < 0x1000:
            return "tinyint"
        if (nh >> 32) in (0x40000000, 0x41000000, 0x42000000, 0x43000000):
            return "ptrform"
        hi = nh >> 56
        return "realhash" if 0x08 <= nh.bit_length() and nh > 0xFFFFFFFF else "other"
    cls = Counter()
    low_by_cls = {}
    for i, l in enumerate(lows):
        if l is None:
            cls["noptr"] += 1; continue
        tgt = BASE_A + (l - 1)
        nh = u64(tgt) if 0 <= tgt + 8 <= n else 0
        c = classify(nh)
        cls[c] += 1
        low_by_cls.setdefault(c, []).append(l)
    print("target classes under base A:", dict(cls))
    for c in ("tinyint", "ptrform", "realhash"):
        if c in low_by_cls:
            ls = low_by_cls[c]
            print(f"  {c}: low min=0x{min(ls):x} max=0x{max(ls):x} distinct={len(set(ls))} top_low={Counter(ls).most_common(3)}")

    # do tiny-int records share few lows? (placeholder model)
    # second-base search: build hash-hits again, pair with UNRESOLVED lows
    v32 = data[: (n // 4) * 4].view("<u4")
    targets = np.array(sorted(hmap.keys()), dtype=np.uint64)
    hit_off = set()
    C = 16_000_000
    for s in range(0, len(v32) - 1, C):
        e = min(s + C, len(v32) - 1)
        val = v32[s:e].astype(np.uint64) | (v32[s + 1:e + 1].astype(np.uint64) << np.uint64(32))
        for j in np.nonzero(np.isin(val, targets))[0]:
            hit_off.add((s + j) * 4)
    unresolved_lows = set()
    for i, l in enumerate(lows):
        if l is None:
            continue
        tgt = BASE_A + (l - 1); nh = u64(tgt) if 0 <= tgt + 8 <= n else 0
        if classify(nh) != "rip":
            unresolved_lows.add(l)
    cand = Counter()
    for l in unresolved_lows:
        for O in hit_off:
            b = O - (l - 1)
            if 0 <= b < n:
                cand[b] += 1
    print("\ntop bases for UNRESOLVED lows:")
    for b, v in cand.most_common(6):
        print(f"  base 0x{b:x}: {v} votes  (==A? {b==BASE_A})")


if __name__ == "__main__":
    main()
