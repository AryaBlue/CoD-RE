"""Pin the XModel-pointer base by the DISCRIMINATIVE metric: bounds agreement.
Per record, the base-independent 'recovered local AABB' = (worldCorner - origin) @ invScaledAxis^T
(invScaledAxis maps world->local). For a candidate base, the pointer names a model; that model's
rip local AABB must equal the recovered local AABB. Sweep base, maximise matches. Fully vectorised.
Uses rip_bounds.json {name:[min3,max3,nv]}."""
import json
import sys
import time
import numpy as np

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
RIPB = r"PATH/TO/rip_bounds.json"  # set this to your own path
ARRAY, COUNT, STRIDE = 0x1D3898E4, 42559, 0x60
BASE_A = 0x13A3D948
M60 = np.uint64(0x0FFFFFFFFFFFFFFF)
t0 = time.time()


def hash64(s):
    s = s.lower().replace("\\", "/"); h = 0xCBF29CE484222325
    for b in s.encode():
        h = (0x100000001B3 * (b ^ h)) & 0xFFFFFFFFFFFFFFFF
    return h


def main():
    raw = open(DEC, "rb").read()
    data = np.frombuffer(raw, dtype=np.uint8); n = data.size
    f4 = data[:(n // 4) * 4].view("<f4"); u32 = data[:(n // 4) * 4].view("<u4")
    b = ARRAY // 4; k = np.arange(COUNT); idx = b + k * 24
    origin = np.stack([f4[idx], f4[idx + 1], f4[idx + 2]], 1).astype(np.float64)
    isa = np.stack([f4[idx + 3 + j] for j in range(9)], 1).astype(np.float64).reshape(COUNT, 3, 3)
    amn = np.stack([f4[idx + 12], f4[idx + 13], f4[idx + 14]], 1).astype(np.float64)
    amx = np.stack([f4[idx + 15], f4[idx + 16], f4[idx + 17]], 1).astype(np.float64)
    low = u32[b + k * 24 + 21].astype(np.int64); high = u32[b + k * 24 + 22]
    valid = high == 0x40000000
    print(f"[{time.time()-t0:.1f}s] parsed records", flush=True)

    # recovered local AABB per record (base-independent)
    sel = np.array([[c & 1, (c >> 1) & 1, (c >> 2) & 1] for c in range(8)])  # 0=min,1=max picker
    wc = np.where(sel[None, :, :].astype(bool), amx[:, None, :], amn[:, None, :])  # (COUNT,8,3)
    rel = wc - origin[:, None, :]
    loc = np.einsum("nij,nkj->nik", rel, isa)  # local_row = rel @ invScaledAxis^T  -> (COUNT,8,3)
    rlo = loc.min(1); rhi = loc.max(1)  # recovered local AABB
    print(f"[{time.time()-t0:.1f}s] recovered local AABBs", flush=True)

    rb = json.load(open(RIPB))
    names = list(rb.keys())
    h2name = {}
    rmin = np.zeros((len(names), 3)); rmax = np.zeros((len(names), 3))
    hashes = np.zeros(len(names), dtype=np.uint64)
    for i, nm in enumerate(names):
        hv = hash64(nm) & 0x0FFFFFFFFFFFFFFF
        hashes[i] = hv; rmin[i] = rb[nm][0]; rmax[i] = rb[nm][1]; h2name[hv] = nm
    order = np.argsort(hashes)
    hs = hashes[order]; rmin = rmin[order]; rmax = rmax[order]
    names_sorted = [names[o] for o in order]
    print(f"[{time.time()-t0:.1f}s] rip bounds: {len(names)} models", flush=True)

    def eval_base(base, tol=4.0, emit=False):
        tgt = base + (low - 1)
        ok = valid & (tgt >= 0) & (tgt + 8 <= n)
        t = tgt.copy(); t[~ok] = 0
        acc = np.zeros(COUNT, dtype=np.uint64)
        for j in range(8):
            acc |= data[t + j].astype(np.uint64) << np.uint64(8 * j)
        nh = acc & M60
        pos = np.searchsorted(hs, nh)
        pos = np.clip(pos, 0, len(hs) - 1)
        hit = ok & (hs[pos] == nh)
        # bounds compare for hits
        emin = np.abs(rlo - rmin[pos]).max(1)
        emax = np.abs(rhi - rmax[pos]).max(1)
        err = np.maximum(emin, emax)
        passed = hit & (err < tol)
        if not emit:
            return int(hit.sum()), int(passed.sum())
        return hit, passed, nh, pos, err

    # coarse sweep
    print(f"[{time.time()-t0:.1f}s] sweeping...", flush=True)
    best = (BASE_A, -1, 0)
    for delta in range(-0x8000, 0x8001, 0x4):
        base = BASE_A + delta
        h_, p_ = eval_base(base)
        if p_ > best[1]:
            best = (base, p_, h_)
    base, passn, hitn = best
    print(f"[{time.time()-t0:.1f}s] BEST base 0x{base:x} (A{base-BASE_A:+#x}) bounds-pass={passn} name-hits={hitn}", flush=True)

    hit, passed, nh, pos, err = eval_base(base, emit=True)
    from collections import Counter
    pm = Counter(names_sorted[pos[i]] for i in np.nonzero(passed)[0])
    print(f"distinct passing models: {len(pm)}; top: {pm.most_common(10)}")
    json.dump({"base": hex(base), "bounds_pass": int(passed.sum()), "name_hits": int(hit.sum()),
               "pass_recs": [int(x) for x in np.nonzero(passed)[0]]},
              open(r"PATH/TO/sweep_result.json", "w"))


if __name__ == "__main__":
    main()
