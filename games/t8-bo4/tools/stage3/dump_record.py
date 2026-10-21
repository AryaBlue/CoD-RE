"""Dump raw bytes around a matrix-cluster hit to pin the 0x60 placement record layout."""
import mmap
import struct
import sys

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path


def dump(base, before=0x30, total=0x180):
    f = open(DEC, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    start = base - before
    print(f"base matrix hit @0x{base:x}; dumping 0x{start:x}..0x{start+total:x}\n")
    for off in range(start, start + total, 16):
        raw = mm[off:off + 16]
        f4 = struct.unpack("<4f", raw)
        u8 = struct.unpack("<2Q", raw)
        rel = off - base
        print(f"0x{off:x} ({rel:+#06x}): {raw.hex()}  f={tuple(round(x,3) for x in f4)}  u64=({u8[0]:#018x},{u8[1]:#018x})")
    mm.close(); f.close()


if __name__ == "__main__":
    base = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x1d484e10
    dump(base)
