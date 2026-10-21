"""Locate the BO4/T8 GfxWorld asset inside a decompressed zone (zm_escape.ff.dec).

Anchors (ACTS BO4 GfxWorld, natural x64 alignment, sizeof 0x1ab0):
  name   XHash  @0x000   (u64 hash, u64 str)
  baseName char* @0x010
  surfaceCount i32 @0x018
  draw   GfxWorldDraw @0x0d8 .. 0x180
  modelCount i32 @0x180
  models ptr @0x188
  mins   vec3 @0x190
  maxs   vec3 @0x19c
  checksum u32 @0x1a8
  dpvs   GfxWorldDpvsStatic @0x1b8  (smodelCount @0x1bc, smodelDrawInsts ptr @0x400)

Strategy: (1) FNV1a name-hash hits for candidate map names, cross-checked by reading
the bounds at hit+0x190 and testing they bracket the Alcatraz landmark; (2) fallback
full float scan for a mins/maxs sextuplet bracketing the landmark, then back-compute start.
Pure stdlib. 32/64-bit agnostic (only reads little-endian values)."""
import mmap
import struct
import sys

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
LANDMARK = (-1815.0, 8033.0, 1432.0)  # s_warden_box
SENT = 0xFFFFFFFFFFFFFFFF
MINS_OFF, MAXS_OFF = 0x190, 0x19C
NAME_OFF, SURF_OFF, MODEL_OFF, CHK_OFF = 0x00, 0x18, 0x180, 0x1A8
SMCNT_OFF, SMINST_OFF = 0x1BC, 0x400


def hash64(s):
    s = s.lower().replace("\\", "/")
    h = 0xCBF29CE484222325
    for b in s.encode():
        h = (0x100000001B3 * (b ^ h)) & 0xFFFFFFFFFFFFFFFF
    return h


def masks(h):
    return {"full": h, "m63": h & 0x7FFFFFFFFFFFFFFF, "m60": h & 0x0FFFFFFFFFFFFFFF}


def plausible_bounds(mn, mx):
    if not all(abs(v) < 1e6 and v == v for v in mn + mx):
        return False
    if not all(mn[i] < mx[i] for i in range(3)):
        return False
    ext = [mx[i] - mn[i] for i in range(3)]
    if not all(16 < ext[i] < 300000 for i in range(3)):
        return False
    return all(mn[i] - 256 <= LANDMARK[i] <= mx[i] + 256 for i in range(3))


def read_at(mm, start):
    def u64(o): return struct.unpack_from("<Q", mm, start + o)[0]
    def i32(o): return struct.unpack_from("<i", mm, start + o)[0]
    def u32(o): return struct.unpack_from("<I", mm, start + o)[0]
    def vec3(o): return struct.unpack_from("<3f", mm, start + o)
    return {
        "start": start, "name_hash": hex(u64(NAME_OFF)), "name_str": hex(u64(NAME_OFF + 8)),
        "baseName_ptr": hex(u64(0x10)), "surfaceCount": i32(SURF_OFF),
        "modelCount": i32(MODEL_OFF), "mins": vec3(MINS_OFF), "maxs": vec3(MAXS_OFF),
        "checksum": hex(u32(CHK_OFF)), "smodelCount": u32(SMCNT_OFF),
        "smodelDrawInsts_ptr": hex(u64(SMINST_OFF)),
    }


def main():
    names = ["maps/zm/zm_escape", "maps/zm/zm_escape.d3dbsp", "zm_escape",
             "maps/zm/zm_escape.gfxmap", "maps/mp/zm_escape", "zm_escape.d3dbsp",
             "maps/zm/zm_escape.gfx_world", "maps/zm/zm_escape.gfxworld"]
    f = open(DEC, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    n = len(mm)
    print(f"zone size {n:,}")

    print("\n== name-hash hits ==")
    wanted = {}
    for nm in names:
        for tag, h in masks(hash64(nm)).items():
            wanted.setdefault(struct.pack("<Q", h), []).append(f"{nm}|{tag}=0x{h:016x}")
    hits = []
    for packed, labels in wanted.items():
        pos = mm.find(packed)
        cnt = 0
        while pos != -1:
            cnt += 1
            hits.append((pos, labels))
            pos = mm.find(packed, pos + 1)
        if cnt:
            print(f"  {labels[0]} -> {cnt} hit(s)")
    # Cross-check each name-hash hit as a GfxWorld start
    print("\n== name-hash hits validated as GfxWorld start (bounds@+0x190 bracket landmark) ==")
    found = []
    for pos, labels in hits:
        if pos + 0x1AB0 > n:
            continue
        mn = struct.unpack_from("<3f", mm, pos + MINS_OFF)
        mx = struct.unpack_from("<3f", mm, pos + MAXS_OFF)
        if plausible_bounds(mn, mx):
            info = read_at(mm, pos)
            info["labels"] = labels
            found.append(info)
            print(f"  GFXWORLD @0x{pos:x}: {info}")
    if not found:
        print("  none — running fallback float-bounds scan for mins/maxs sextuplet")
        scan_bounds(mm, n)
    mm.close()
    f.close()


def scan_bounds(mm, n):
    import array
    step = 4
    found = 0
    # Walk 4-byte aligned; interpret 6 consecutive floats. Coarse but one-pass.
    lx, ly, lz = LANDMARK
    pos = 0
    end = n - 24
    unpack = struct.Struct("<6f").unpack_from
    while pos < end:
        try:
            a, b, c, d, e, g = unpack(mm, pos)
        except struct.error:
            break
        if (a < lx < d and b < ly < e and c < lz < g
                and -2e5 < a and d < 2e5 and (d - a) < 3e5 and (e - b) < 3e5 and (g - c) < 3e5
                and (d - a) > 256 and (e - b) > 256):
            start = pos - MINS_OFF
            if start >= 0:
                print(f"  bounds-sig @0x{pos:x} (start@0x{start:x}): mins={(a,b,c)} maxs={(d,e,g)}")
                found += 1
                if found > 40:
                    print("  (stopping at 40)")
                    return
        pos += step
    print(f"  bounds scan done, {found} candidate(s)")


if __name__ == "__main__":
    main()
