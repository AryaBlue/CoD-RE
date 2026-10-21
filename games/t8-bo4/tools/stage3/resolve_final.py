"""Final placement resolver + bounds gate.
1. sequential full read of the zone into RAM (avoids scattered-mmap disk thrash).
2. ground-truth dict PATH/TO/t8_name_dict.json (60-bit hash->name).
3. pin the XModel-pointer base: sweep bases, score by #records whose NamePtr&0xFFF...(60b) is in dict.
4. at the winning base, resolve names; BOUNDS GATE each against the record's absmin/absmax using the
   rip model LOD0 local AABB (only rip models can be placed). Emit validated placements.
Fields: +0x00 origin f3, +0x0c invScaledAxis f3x3, +0x30 absmin, +0x3c absmax, +0x54 u64 ptr, +0x5c contents.
Ptr 0x40000000_XXXXXXXX -> target = base + XXXXXXXX - 1. Transform world = origin + inv(invScaledAxis)@local."""
import json
import os
import re
import sys
import time
import numpy as np
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # smodel_lib in ../
from smodel_lib import axis_to_angles  # noqa: E402

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
DICT = r"PATH/TO/t8_name_dict.json"  # set this to your own path
RIP = r"PATH/TO/exported_xmodels"  # set this to your own path
OUT = r"PATH/TO/bod_props.json"  # set this to your own path
OUT_FULL = r"PATH/TO/placements_full.json"  # set this to your own path
ARRAY, COUNT, STRIDE = 0x1D3898E4, 42559, 0x60
BASE_A = 0x13A3D948
M60 = 0x0FFFFFFFFFFFFFFF
OFFSET_RE = re.compile(rb"OFFSET ([-0-9.eE]+), ([-0-9.eE]+), ([-0-9.eE]+)")
t0 = time.time()


def log(*a):
    print(f"[{time.time()-t0:5.1f}s]", *a, flush=True)


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


def main():
    raw = open(DEC, "rb").read()                      # one sequential read
    data = np.frombuffer(raw, dtype=np.uint8); n = data.size
    log(f"read {n:,} bytes")
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
    log(f"records parsed; valid 0x40000000 ptrs: {int(valid.sum())}/{COUNT}")

    d = json.load(open(DICT))
    name_by_hash = {int(h, 16) & M60: nm for h, nm in d.items()}
    dict_keys = np.array(sorted(name_by_hash.keys()), dtype=np.uint64)
    log(f"dict loaded: {len(name_by_hash):,} entries")

    def namehash_at(base):
        tgt = base + (low - 1)
        ok = valid & (tgt >= 0) & (tgt + 8 <= n)
        nh = np.zeros(COUNT, dtype=np.uint64)
        t = tgt[ok]
        acc = np.zeros(len(t), dtype=np.uint64)
        for j in range(8):
            acc |= data[t + j].astype(np.uint64) << np.uint64(8 * j)
        nh[ok] = acc & np.uint64(M60)
        return nh, ok

    # base sweep by dict membership
    best = (BASE_A, -1)
    log("sweeping base...")
    for delta in range(-0x2000, 0x2001, 0x4):
        base = BASE_A + delta
        nh, ok = namehash_at(base)
        cnt = int(np.isin(nh, dict_keys).sum())
        if cnt > best[1]:
            best = (base, cnt)
    base, bestcnt = best
    log(f"BEST base 0x{base:x} dict-hits={bestcnt} (base_A delta {base-BASE_A:+#x})")

    nh, ok = namehash_at(base)
    inname = np.isin(nh, dict_keys)
    full = []
    emit = []
    counts = {"resolved_dict": 0, "in_rip": 0, "bounds_pass": 0, "bounds_fail": 0, "no_rip_mesh": 0, "unresolved": 0}
    for i in range(COUNT):
        if not ok[i] or not inname[i]:
            counts["unresolved"] += 1
            full.append({"rec": i, "model": None, "name_hash": f"0x{int(nh[i]):015x}"})
            continue
        name = name_by_hash[int(nh[i])]
        counts["resolved_dict"] += 1
        rec = {"rec": i, "model": name, "origin": [round(float(x), 4) for x in origin[i]]}
        lb = local_aabb(name)
        if lb is None:
            counts["no_rip_mesh"] += 1
            rec["placeable"] = False
            full.append(rec)
            continue
        counts["in_rip"] += 1
        try:
            sA = np.linalg.inv(isa[i])
        except np.linalg.LinAlgError:
            counts["bounds_fail"] += 1; rec["placeable"] = False; full.append(rec); continue
        lo, hi = lb
        corners = np.array([[lo[0] if c & 1 else hi[0], lo[1] if c & 2 else hi[1], lo[2] if c & 4 else hi[2]] for c in range(8)])
        world = origin[i] + corners @ sA.T
        err = float(max(np.abs(world.min(0) - amn[i]).max(), np.abs(world.max(0) - amx[i]).max()))
        rec["bounds_err"] = round(err, 3)
        if err < 6.0:
            counts["bounds_pass"] += 1
            rn = [float(np.linalg.norm(isa[i][r])) for r in range(3)]
            s = 1.0 / (sum(rn) / 3.0)
            axis = [float(x) for x in (s * isa[i].T).flatten()]
            emit.append({"model": name, "origin": rec["origin"],
                         "angles": [round(x, 4) for x in axis_to_angles(axis)],
                         "scale": round(s, 6), "axis": [round(x, 6) for x in axis]})
            rec["placeable"] = True
        else:
            counts["bounds_fail"] += 1
            rec["placeable"] = False
        full.append(rec)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(emit, open(OUT, "w"))
    json.dump({"base": hex(base), "counts": counts, "records": full}, open(OUT_FULL, "w"))
    log(f"counts: {counts}")
    from collections import Counter
    passmodels = Counter(r["model"] for r in emit)
    log(f"emitted {len(emit)} bounds-validated placements -> {OUT}")
    log(f"distinct placeable models: {len(passmodels)}; top: {passmodels.most_common(6)}")
    # dict-resolved but not in rip (what to rip next)
    notrip = Counter(r["model"] for r in full if r.get("model") and r.get("placeable") is False and "bounds_err" not in r)
    log(f"dict-resolved-but-not-ripped distinct: {len(notrip)}; top: {notrip.most_common(6)}")
    for r in emit[:6]:
        log(f"  {r['model']} origin={r['origin']} angles={r['angles']} scale={r['scale']}")


if __name__ == "__main__":
    main()
