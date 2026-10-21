"""Dump context around every 'maps/zm/zm_escape.d3dbsp' name-hash hit to identify which
is the GfxWorld asset-struct start and whether field offsets drifted from ACTS's layout."""
import mmap
import struct

DEC = r"PATH/TO/zm_escape.ff.dec"  # set this to your own path
LANDMARK = (-1815.0, 8033.0, 1432.0)
H_D3DBSP = 0x6BA7703DC1C9D8DA  # maps/zm/zm_escape.d3dbsp &0x7FFF...
H_ESC = 0x551FD293040F234E     # zm_escape &0x7FFF...


def finite(v):
    return v == v and abs(v) < 1e30


def looks_bounds(mn, mx):
    return all(finite(x) for x in mn + mx) and all(mn[i] < mx[i] for i in range(3)) \
        and all(1 < (mx[i] - mn[i]) < 4e5 for i in range(3))


def main():
    f = open(DEC, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    for H, tag in [(H_D3DBSP, "d3dbsp"), (H_ESC, "zm_escape")]:
        packed = struct.pack("<Q", H)
        pos = mm.find(packed)
        idx = 0
        print(f"\n########## hits for {tag} (0x{H:016x}) ##########")
        while pos != -1:
            idx += 1
            nxt = struct.unpack_from("<Q", mm, pos + 8)[0]
            # context: 32 bytes before, to see if this is a struct start or an inline ref
            before = mm[max(0, pos - 16):pos].hex()
            # try reading GfxWorld fields assuming pos == struct start
            surf = struct.unpack_from("<i", mm, pos + 0x18)[0] if pos + 0x1AB0 < len(mm) else None
            print(f"\n[{tag} #{idx}] @0x{pos:x}  XHash.str=0x{nxt:016x}  prev16={before}")
            if pos + 0x1AB0 < len(mm):
                model = struct.unpack_from("<i", mm, pos + 0x180)[0]
                mn = struct.unpack_from("<3f", mm, pos + 0x190)
                mx = struct.unpack_from("<3f", mm, pos + 0x19C)
                chk = struct.unpack_from("<I", mm, pos + 0x1A8)[0]
                smc = struct.unpack_from("<I", mm, pos + 0x1BC)[0]
                print(f"    [+0x18 surfCnt]={surf}  [+0x180 modelCnt]={model}  "
                      f"[+0x1a8 chksum]=0x{chk:x}  [+0x1bc smodelCnt]={smc}")
                print(f"    [+0x190 mins]={tuple(round(v,2) for v in mn)}  "
                      f"[+0x19c maxs]={tuple(round(v,2) for v in mx)}  bounds_ok={looks_bounds(mn,mx)}")
                # Also scan a window +0x100..+0x280 for any clean bounds sextuplet bracketing landmark
                for off in range(0x80, 0x400, 4):
                    b = struct.unpack_from("<6f", mm, pos + off)
                    m0, m1 = b[:3], b[3:]
                    if looks_bounds(m0, m1) and all(m0[i] - 512 <= LANDMARK[i] <= m1[i] + 512 for i in range(3)):
                        print(f"      >> bounds-bracket-landmark @+0x{off:x}: mins={tuple(round(v,1) for v in m0)} maxs={tuple(round(v,1) for v in m1)}")
            pos = mm.find(packed, pos + 1)
    mm.close()
    f.close()


if __name__ == "__main__":
    main()
