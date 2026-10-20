"""Minimal PDB (MSF 7.0) TPI reader: dumps struct/union/enum layouts by name.
usage: pdbtypes.py <pdb> <regex-of-type-names>"""
import struct, sys, re

def read_msf(path):
    f = open(path, 'rb'); d = f.read()
    assert d.startswith(b'Microsoft C/C++ MSF 7.00'), 'not MSF7'
    bs, _, nblocks, dirbytes, _, bmaddr = struct.unpack_from('<6I', d, 32)
    ndirblocks = (dirbytes + bs - 1) // bs
    dirblocks = struct.unpack_from(f'<{ndirblocks}I', d, bmaddr * bs)
    dirdata = b''.join(d[b*bs:(b+1)*bs] for b in dirblocks)[:dirbytes]
    nstreams = struct.unpack_from('<I', dirdata, 0)[0]
    sizes = struct.unpack_from(f'<{nstreams}I', dirdata, 4)
    o = 4 + 4*nstreams; streams = []
    for sz in sizes:
        if sz == 0xffffffff: streams.append(b''); continue
        n = (sz + bs - 1) // bs
        blocks = struct.unpack_from(f'<{n}I', dirdata, o); o += 4*n
        streams.append(b''.join(d[b*bs:(b+1)*bs] for b in blocks)[:sz])
    return streams

def numeric(b, o):
    v = struct.unpack_from('<H', b, o)[0]
    if v < 0x8000: return v, o+2
    fmt = {0x8000:'<b',0x8001:'<h',0x8002:'<H',0x8003:'<i',0x8004:'<I',0x8009:'<q',0x800a:'<Q'}[v]
    return struct.unpack_from(fmt, b, o+2)[0], o+2+struct.calcsize(fmt)

def cstr(b, o):
    e = b.index(b'\0', o); return b[o:e].decode('latin1'), e+1

BASIC = {0x03:'void',0x10:'char',0x20:'uchar',0x11:'short',0x21:'ushort',0x12:'long',0x22:'ulong',
         0x13:'int64',0x23:'uint64',0x30:'bool',0x40:'float',0x41:'double',0x68:'int8',0x69:'uint8',
         0x70:'char',0x71:'wchar_t',0x72:'int16',0x73:'uint16',0x74:'int',0x75:'uint',0x76:'int64',0x77:'uint64'}

class TPI:
    def __init__(self, s):
        hdrsz, self.begin, self.end, nbytes = struct.unpack_from('<4I', s, 4)
        self.recs = {}; o = hdrsz; ti = self.begin
        while o < hdrsz + nbytes:
            ln, kind = struct.unpack_from('<HH', s, o)
            self.recs[ti] = (kind, s[o+4:o+2+ln]); o += 2+ln; ti += 1
        self.byname = {}
        for ti, (k, b) in self.recs.items():
            if k in (0x1504, 0x1505, 0x1506, 0x1507):
                n, fwd, sz = self.agg(ti)
                if not fwd: self.byname.setdefault(n, ti)

    def agg(self, ti):
        k, b = self.recs[ti]
        if k in (0x1504, 0x1505):
            cnt, prop, fl, der, vsh = struct.unpack_from('<HHIII', b, 0)
            sz, o = numeric(b, 16)
        elif k == 0x1506:
            cnt, prop, fl = struct.unpack_from('<HHI', b, 0); sz, o = numeric(b, 8)
        else:  # enum
            cnt, prop, ut, fl = struct.unpack_from('<HHII', b, 0); sz, o = 0, 12
        name, _ = cstr(b, o)
        return name, bool(prop & 0x80), sz

    def name(self, ti):
        if ti < 0x1000:
            base = BASIC.get(ti & 0xff, f'basic_{ti:#x}')
            return base + ('*' if ti & 0x700 else '')
        k, b = self.recs[ti]
        if k in (0x1504, 0x1505, 0x1506, 0x1507):
            return ('enum ' if k == 0x1507 else '') + self.agg(ti)[0]
        if k == 0x1002: return self.name(struct.unpack_from('<I', b, 0)[0]) + '*'
        if k == 0x1001:
            t, m = struct.unpack_from('<IH', b, 0)
            return ('const ' if m & 1 else '') + ('volatile ' if m & 2 else '') + self.name(t)
        if k == 0x1503:
            et, it = struct.unpack_from('<II', b, 0); sz, _ = numeric(b, 8)
            return f'{self.name(et)}[{sz}B]'
        if k == 0x1205:
            t, ln, pos = struct.unpack_from('<IBB', b, 0)
            return f'{self.name(t)} :{ln} @bit{pos}'
        if k == 0x1008: return 'func'
        return f'type_{k:#x}'

    def fields(self, fl):
        k, b = self.recs[fl]; o = 0; out = []
        while o < len(b):
            sk = struct.unpack_from('<H', b, o)[0]
            if sk == 0x150d:   # member
                attr, t = struct.unpack_from('<HI', b, o+2); off, o2 = numeric(b, o+8)
                n, o = cstr(b, o2); out.append(('member', off, self.name(t), n, t))
            elif sk == 0x1502: # enumerate
                attr = struct.unpack_from('<H', b, o+2)[0]; v, o2 = numeric(b, o+4)
                n, o = cstr(b, o2); out.append(('enum', v, '', n, 0))
            elif sk == 0x150e: # static member
                attr, t = struct.unpack_from('<HI', b, o+2); n, o = cstr(b, o+8)
                out.append(('static', 0, self.name(t), n, t))
            elif sk == 0x1510: # nested type
                t = struct.unpack_from('<I', b, o+4)[0]; n, o = cstr(b, o+8)
            elif sk == 0x1400: # base class
                attr, t = struct.unpack_from('<HI', b, o+2); off, o = numeric(b, o+8)
                out.append(('base', off, self.name(t), '<base>', t))
            elif sk == 0x150f: # overloaded method
                n, o = cstr(b, o+8); out.append(('method', 0, '', n, 0))
            elif sk == 0x1511: # one method
                attr, t = struct.unpack_from('<HI', b, o+2); mprop = (attr >> 2) & 7
                o += 8 + (4 if mprop in (4, 6) else 0); n, o = cstr(b, o)
                out.append(('method', 0, '', n, 0))
            elif sk == 0x1409: o += 8
            elif sk == 0x1404:
                out += self.fields(struct.unpack_from('<I', b, o+4)[0]); o += 8
            else:
                out.append(('?', 0, '', f'unknown leaf {sk:#x}', 0)); break
            while o < len(b) and b[o] >= 0xf0: o += b[o] & 0x0f
        return out

    def dump(self, ti):
        k, b = self.recs[ti]; name, _, sz = self.agg(ti)
        fl = struct.unpack_from('<I', b, 4 if k != 0x1507 else 8)[0]
        kw = {0x1504:'class',0x1505:'struct',0x1506:'union',0x1507:'enum'}[k]
        print(f'{kw} {name}  // sizeof={sz:#x}')
        for kind, off, tn, n, _ in self.fields(fl):
            if kind == 'enum': print(f'    {n} = {off},')
            elif kind == 'method': print(f'    {n}();')
            elif kind == 'static': print(f'    static {tn} {n};')
            else: print(f'    /*{off:#06x}*/ {tn} {n};')
        print()

if __name__ == '__main__':
    tpi = TPI(read_msf(sys.argv[1])[2])
    pat = re.compile(sys.argv[2])
    for n in sorted(tpi.byname):
        if pat.fullmatch(n): tpi.dump(tpi.byname[n])
