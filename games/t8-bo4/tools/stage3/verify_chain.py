"""Verify the collision static-model array -> xmodel ptr -> XModel name-hash chain.
Array @0x1D3898E4, 42559 recs x 0x60 (BoD-session layout):
 +0x00 float3 origin; +0x0c float3x3 invScaledAxis; +0x30 float3 absmin; +0x3c float3 absmax;
 +0x48 u32 0; +0x4c u32 flags(0x3039/0x13039); +0x50 u32 0; +0x54 u64 xmodel ptr; +0x5c u32 contents.
Pointer decode: 0x40000000_XXXXXXXX -> .dec off = (XXXXXXXX-1)+0x101DF9EC."""
import mmap
import struct

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
ARRAY = 0x1D3898E4
COUNT = 42559
STRIDE = 0x60
PBASE = 0x101DF9EC


def decode_ptr(p):
    if (p >> 32) != 0x40000000:
        return None
    return ((p & 0xFFFFFFFF) - 1) + PBASE


def main():
    f = open(DEC, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    n = len(mm)
    print(f"zone {n:,}; array end 0x{ARRAY+COUNT*STRIDE:x} (<= zone? {ARRAY+COUNT*STRIDE<=n})")
    namehashes = {}
    bad_ptr = 0
    for i in list(range(8)) + [100, 1000, 10000, 42558]:
        R = ARRAY + i * STRIDE
        origin = struct.unpack_from("<3f", mm, R)
        mat = struct.unpack_from("<9f", mm, R + 0x0C)
        amn = struct.unpack_from("<3f", mm, R + 0x30)
        amx = struct.unpack_from("<3f", mm, R + 0x3C)
        flags = struct.unpack_from("<I", mm, R + 0x4C)[0]
        xptr = struct.unpack_from("<Q", mm, R + 0x54)[0]
        contents = struct.unpack_from("<I", mm, R + 0x5C)[0]
        tgt = decode_ptr(xptr)
        nh = ns = None
        if tgt and tgt + 16 <= n:
            nh = struct.unpack_from("<Q", mm, tgt)[0]
            ns = struct.unpack_from("<Q", mm, tgt + 8)[0]
        print(f"\nrec {i} @0x{R:x}: origin={tuple(round(v,1) for v in origin)} flags=0x{flags:x} contents=0x{contents:x}")
        print(f"   xptr=0x{xptr:016x} -> dec off {hex(tgt) if tgt else None}  XModel.name hash=0x{nh:016x} str=0x{ns:016x}" if nh is not None else f"   xptr=0x{xptr:016x} DECODE FAIL")
        print(f"   invScaledAxis={tuple(round(v,4) for v in mat)}")

    # quick pass over all: how many ptrs decode, how many distinct name hashes
    distinct = {}
    for i in range(COUNT):
        R = ARRAY + i * STRIDE
        xptr = struct.unpack_from("<Q", mm, R + 0x54)[0]
        tgt = decode_ptr(xptr)
        if tgt is None or tgt + 8 > n:
            bad_ptr += 1
            continue
        nh = struct.unpack_from("<Q", mm, tgt)[0]
        distinct[nh] = distinct.get(nh, 0) + 1
    print(f"\n== over {COUNT} records: {bad_ptr} ptr-decode failures, {len(distinct)} distinct name hashes ==")
    top = sorted(distinct.items(), key=lambda kv: -kv[1])[:12]
    for h, c in top:
        print(f"   0x{h:016x} x{c}")
    mm.close(); f.close()


if __name__ == "__main__":
    main()
