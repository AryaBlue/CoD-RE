import struct
class PE:
    def __init__(s, path):
        d = s.d = open(path, 'rb').read()
        o = struct.unpack_from('<I', d, 0x3c)[0]
        n = struct.unpack_from('<H', d, o + 6)[0]; so = struct.unpack_from('<H', d, o + 20)[0]
        s.base = struct.unpack_from('<I', d, o + 52)[0]; s.secs = []
        for i in range(n):
            h = o + 24 + so + 40 * i
            name = d[h:h+8].rstrip(b'\0').decode(); vs, va, rs, ro = struct.unpack_from('<4I', d, h + 8)
            s.secs.append((name, s.base + va, vs, ro, rs))
    def off(s, va):
        for n, v, vs, ro, rs in s.secs:
            if v <= va < v + max(vs, rs): return ro + va - v if va - v < rs else None
    def va(s, off):
        for n, v, vs, ro, rs in s.secs:
            if ro <= off < ro + rs: return v + off - ro
    def u32(s, va): return struct.unpack_from('<I', s.d, s.off(va))[0]
    def cstr(s, va):
        o = s.off(va); e = s.d.index(b'\0', o); return s.d[o:e].decode('latin1')
    def sec(s, name): return [x for x in s.secs if x[0] == name][0]
