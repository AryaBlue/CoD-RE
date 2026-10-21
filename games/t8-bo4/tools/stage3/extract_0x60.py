"""Extract the full 0x60 per-instance transform/cull array around the matrix cluster.
Record frame (anchored on matrix start M; marker sits at M-0x20+... let's anchor on marker):
 marker frame R:
  +0x00 u32 marker(==0x3039?)  +0x04 u32  +0x08 u32 packed  +0x0c f32  +0x10 u32 flag
  +0x14 vec3 center  +0x20 matrix[9]  +0x44 vec3 min  +0x50 vec3 max  +0x5c f32
Walk by 0x60 from a seed while the record stays valid; collect transforms + stats."""
import json
import mmap
import math
import struct
import numpy as np

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
LANDMARK = (-1815.0, 8033.0, 1432.0)
SEED_MATRIX = 0x1D484E10   # known identity matrix; marker = SEED_MATRIX - 0x20
STRIDE = 0x60


def orthonormal(m, tol=0.03):
    r = [np.array(m[0:3]), np.array(m[3:6]), np.array(m[6:9])]
    if not all(np.isfinite(x).all() for x in r):
        return False
    for x in r:
        if abs(np.dot(x, x) - 1) > tol:
            return False
    return abs(np.dot(r[0], r[1])) < tol and abs(np.dot(r[0], r[2])) < tol and abs(np.dot(r[1], r[2])) < tol


def parse(mm, R):
    marker = struct.unpack_from("<I", mm, R)[0]
    packed = struct.unpack_from("<I", mm, R + 8)[0]
    f0c = struct.unpack_from("<f", mm, R + 0x0C)[0]
    flag = struct.unpack_from("<I", mm, R + 0x10)[0]
    center = struct.unpack_from("<3f", mm, R + 0x14)
    mat = struct.unpack_from("<9f", mm, R + 0x20)
    mn = struct.unpack_from("<3f", mm, R + 0x44)
    mx = struct.unpack_from("<3f", mm, R + 0x50)
    return marker, packed, f0c, flag, center, mat, mn, mx


def valid(rec):
    marker, packed, f0c, flag, center, mat, mn, mx = rec
    if not orthonormal(mat):
        return False
    if not all(math.isfinite(v) for v in center + mn + mx):
        return False
    if not all(mn[i] <= mx[i] + 1e-3 for i in range(3)):
        return False
    # center == midpoint(min,max)?
    return all(abs(center[i] - 0.5 * (mn[i] + mx[i])) < 1.0 for i in range(3))


def main():
    f = open(DEC, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    n = len(mm)
    R0 = SEED_MATRIX - 0x20
    # confirm seed
    print("seed marker u32 =", hex(struct.unpack_from("<I", mm, R0)[0]), "(expect 0x3039?)")
    # walk back
    lo = R0
    while lo - STRIDE >= 0 and valid(parse(mm, lo - STRIDE)):
        lo -= STRIDE
    # walk forward
    hi = R0
    while hi + STRIDE + 0x60 <= n and valid(parse(mm, hi + STRIDE)):
        hi += STRIDE
    count = (hi - lo) // STRIDE + 1
    print(f"contiguous array: 0x{lo:x}..0x{hi+0x60:x}  records={count}  stride=0x{STRIDE:x}")

    recs = []
    markers, f0cs, flags = set(), set(), set()
    cen = []
    for R in range(lo, hi + 1, STRIDE):
        marker, packed, f0c, flag, center, mat, mn, mx = parse(mm, R)
        markers.add(marker); f0cs.add(round(f0c, 4)); flags.add(flag)
        cen.append(center)
        recs.append({"off": R, "marker": marker, "packed": packed, "f0c": f0c, "flag": flag,
                     "center": center, "matrix": mat, "min": mn, "max": mx})
    cen = np.array(cen)
    gmin = cen.min(0).tolist()
    gmax = cen.max(0).tolist()
    inside = all(gmin[i] - 1 <= LANDMARK[i] <= gmax[i] + 1 for i in range(3))
    print(f"\nmarkers seen: {sorted(markers)[:8]}  flags: {sorted(flags)[:8]}  f0c vals: {sorted(f0cs)[:8]}")
    print(f"center bounds: min={[round(v,1) for v in gmin]}  max={[round(v,1) for v in gmax]}")
    print(f"landmark {LANDMARK} inside center-bounds? {inside}")
    print(f"center mean = {[round(v,1) for v in cen.mean(0)]}")
    # scale: derive from matrix row norm if scale baked, else packed/f0c
    # sample first 5 with euler
    print("\nfirst 5 records:")
    for r in recs[:5]:
        print(f"  @0x{r['off']:x} marker={hex(r['marker'])} packed={hex(r['packed'])} f0c={r['f0c']} flag={r['flag']}")
        print(f"     center={tuple(round(v,2) for v in r['center'])} min={tuple(round(v,2) for v in r['min'])} max={tuple(round(v,2) for v in r['max'])}")
        print(f"     matrix={tuple(round(v,4) for v in r['matrix'])}")
    out = r"PATH/TO/array_0x60.json"
    json.dump({"start": lo, "count": count, "stride": STRIDE,
               "center_bounds": [gmin, gmax], "landmark_inside": inside,
               "records": recs}, open(out, "w"))
    print(f"\nwrote {out}")
    mm.close(); f.close()


if __name__ == "__main__":
    main()
