"""Find the GfxWorld static-model PLACEMENT array by its strongest signature: a dense run of
orthonormal 3x3 float32 rotation matrices (BO3 GfxStaticModel = origin f3 + matrix f9 + scale f1 + ... + XModel*).
Orthonormal matrices are essentially absent from random bytes, so clustering localises the array
regardless of GfxWorld struct-offset drift. Reports hit clusters + inferred record stride.
numpy, read-only."""
import mmap
import numpy as np
import struct
import sys

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
NTOL, DTOL = 0.02, 0.02   # row-norm and orthogonality tolerance


def scan():
    f = open(DEC, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    n = len(mm)
    nfloats = n // 4
    a = np.frombuffer(mm, dtype="<f4", count=nfloats)
    M = nfloats - 9
    C = 8_000_000
    hits = []
    for s in range(0, M, C):
        e = min(s + C, M)
        L = e - s
        reg = a[s:e + 8]  # need indices up to +8
        cols = [reg[k:k + L] for k in range(9)]
        finite = np.ones(L, dtype=bool)
        for c in cols:
            finite &= np.isfinite(c)
        n0 = cols[0] * cols[0] + cols[1] * cols[1] + cols[2] * cols[2]
        n1 = cols[3] * cols[3] + cols[4] * cols[4] + cols[5] * cols[5]
        n2 = cols[6] * cols[6] + cols[7] * cols[7] + cols[8] * cols[8]
        d01 = cols[0] * cols[3] + cols[1] * cols[4] + cols[2] * cols[5]
        d02 = cols[0] * cols[6] + cols[1] * cols[7] + cols[2] * cols[8]
        d12 = cols[3] * cols[6] + cols[4] * cols[7] + cols[5] * cols[8]
        ok = finite
        ok &= np.abs(n0 - 1) < NTOL
        ok &= np.abs(n1 - 1) < NTOL
        ok &= np.abs(n2 - 1) < NTOL
        ok &= np.abs(d01) < DTOL
        ok &= np.abs(d02) < DTOL
        ok &= np.abs(d12) < DTOL
        # exclude trivial all-zero (won't pass norm) already; also drop exact identity spam? keep.
        idx = np.nonzero(ok)[0]
        for j in idx:
            hits.append((s + j) * 4)  # byte offset of matrix start
    print(f"zone {n:,} bytes, {nfloats:,} floats; orthonormal-matrix hits: {len(hits):,}")
    hits = np.array(hits, dtype=np.int64)
    if len(hits) == 0:
        mm.close(); f.close(); return
    # Cluster: group hits whose gaps are small/consistent
    gaps = np.diff(hits)
    # Find dense regions: where gap <= 256 bytes
    print("\n== dense clusters (consecutive matrices within 256 bytes) ==")
    starts = np.nonzero(np.concatenate(([True], gaps > 256)))[0]
    ends = np.concatenate((starts[1:], [len(hits)]))
    clusters = []
    for si, ei in zip(starts, ends):
        cnt = ei - si
        if cnt >= 20:
            lo, hi = hits[si], hits[ei - 1]
            seg = gaps[si:ei - 1]
            vals, counts = np.unique(seg, return_counts=True)
            mode = vals[np.argmax(counts)]
            clusters.append((lo, hi, cnt, int(mode)))
    clusters.sort(key=lambda c: -c[2])
    for lo, hi, cnt, mode in clusters[:30]:
        span = hi - lo
        print(f"  @0x{lo:x}..0x{hi:x}  count={cnt}  modal_stride={mode}B  span={span}  (~{span//max(mode,1)+1} records)")
    mm.close(); f.close()
    return clusters


if __name__ == "__main__":
    scan()
