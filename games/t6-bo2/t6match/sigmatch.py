# Match server-exe functions (from the .map) to t6zm.exe by masked byte signatures.
# usage: sigmatch.py server.exe server.map t6zm.exe funcs.tsv out.tsv
import re, struct, sys, bisect

def pe(path):
    d = open(path, 'rb').read()
    o = struct.unpack_from('<I', d, 0x3C)[0]
    n = struct.unpack_from('<H', d, o + 6)[0]
    opt = struct.unpack_from('<H', d, o + 20)[0]
    base = struct.unpack_from('<I', d, o + 24 + 28)[0]
    secs = []
    for i in range(n):
        s = o + 24 + opt + i * 40
        name = d[s:s + 8].rstrip(b'\0').decode()
        vsize, va, rsize, raw = struct.unpack_from('<4I', d, s + 8)
        secs.append((name, base + va, vsize, d[raw:raw + rsize]))
    return base, secs

def read(secs, va, n):
    for name, sva, vs, data in secs:
        if sva <= va < sva + len(data):
            return data[va - sva:va - sva + n]
    return b''

sbase, ssecs = pe(sys.argv[1])
tbase, tsecs = pe(sys.argv[3])
ttext = [s for s in tsecs if s[0] == '.text'] or [max(tsecs, key=lambda s: len(s[3]))]
tname, tva, _, tdata = ttext[0]

# all symbol addresses -> function end estimate
addrs = []
for l in open(sys.argv[2], errors='replace'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', p[0]) and re.match(r'^[0-9a-f]{8}$', p[2]) and p[3] == 'f':
        addrs.append(int(p[2], 16))
addrs = sorted(set(addrs))

def masked(code):
    # regex from bytes: wildcard rel32 after E8/E9, and any imm/disp32 that looks like an image address
    out = []; i = 0
    while i < len(code):
        b = code[i]
        if b in (0xE8, 0xE9) and i + 5 <= len(code):
            out.append(re.escape(bytes([b])) + b'....'); i += 5; continue
        if i + 4 <= len(code):
            v = struct.unpack_from('<I', code, i)[0]
            if 0x400000 <= v < 0x8000000:
                out.append(b'....'); i += 4; continue
        out.append(re.escape(bytes([b]))); i += 1
    return b''.join(out)

res = []
for line in open(sys.argv[4]):
    a, name, obj = line.rstrip('\n').split('\t')
    a = int(a, 16)
    k = bisect.bisect_right(addrs, a)
    end = addrs[k] if k < len(addrs) else a + 64
    size = end - a
    hit = None
    for n in (24, 40, 64, 96):
        n = min(n, size)
        code = read(ssecs, a, n)
        if len(code) < 12: break
        pat = re.compile(masked(code), re.S)
        ms = [m.start() for m in pat.finditer(tdata)][:3]
        if len(ms) == 1: hit = tva + ms[0]; break
        if not ms: break
        if n == size: break
    res.append((a, name, obj, size, hit))
with open(sys.argv[5], 'w') as f:
    for a, name, obj, size, hit in res:
        f.write('%08X\t%s\t%s\t%d\t%s\n' % (a, name, obj, size, '%08X' % hit if hit else '-'))
print(sum(1 for r in res if r[4]), 'of', len(res), 'matched')
