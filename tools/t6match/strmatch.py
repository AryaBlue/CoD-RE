# Match server functions to t6zm by the string literals they reference.
# usage: strmatch.py server.exe server.map t6zm.exe funcs.tsv out.tsv
import re, struct, sys, bisect, collections
exec(open(__file__.replace('strmatch.py', 'sigmatch.py')).read().split('sbase, ssecs')[0])

def sec(secs, name): return [s for s in secs if s[0] == name][0]

def strings_refs(secs, starts_of):
    _, tva, _, text = sec(secs, '.text')
    _, rva, rvs, rdata = sec(secs, '.rdata')
    lo, hi = rva, rva + len(rdata)
    pat = re.compile(b'(?=(...[\x00]))'.replace(b'...', b'[\x00-\xff]{2}[' + bytes([lo >> 16 & 0xFF]) + b'-' + bytes([hi >> 16 & 0xFF]) + b']'), re.S)
    refs = collections.defaultdict(set)      # string -> set(function start)
    cache = {}
    for m in pat.finditer(text):
        v = struct.unpack_from('<I', text, m.start())[0]
        if not lo <= v < hi: continue
        s = cache.get(v)
        if s is None:
            o = v - rva; e = rdata.find(b'\0', o, o + 200)
            raw = rdata[o:e] if e > o else b''
            s = raw.decode('latin1') if len(raw) >= 5 and all(32 <= c < 127 for c in raw) else ''
            cache[v] = s
        if not s: continue
        f = starts_of(tva + m.start())
        if f: refs[s].add(f)
    return refs

sbase, ssecs = pe(sys.argv[1]); tbase, tsecs = pe(sys.argv[3])
addrs = []
for l in open(sys.argv[2], errors='replace'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', p[0]) and re.match(r'^[0-9a-f]{8}$', p[2]) and p[3] == 'f':
        addrs.append(int(p[2], 16))
addrs = sorted(set(addrs))
def srv_start(va):
    k = bisect.bisect_right(addrs, va); return addrs[k - 1] if k else None

_, ttva, _, ttext = sec(tsecs, '.text')
def t_start(va):                       # previous 16-aligned address after int3 padding (or a ret)
    o = (va - ttva) & ~15
    while o > 0:
        if ttext[o - 1] == 0xCC or (ttext[o - 1] == 0xC3 and o % 16 == 0 and ttext[o - 2] != 0x8B): return ttva + o
        o -= 16
    return None

srefs = strings_refs(ssecs, srv_start)
trefs = strings_refs(tsecs, t_start)
by_func = collections.defaultdict(set)
for s, fs in srefs.items():
    for f in fs: by_func[f].add(s)

out = []
for line in open(sys.argv[4]):
    a, name, obj = line.rstrip('\n').split('\t'); a = int(a, 16)
    votes = collections.Counter(); used = 0
    for s in by_func.get(a, ()):
        cands = trefs.get(s, set())
        if 0 < len(cands) <= 2 and len(srefs[s]) <= 2:
            used += 1
            for c in cands: votes[c] += 1.0 / len(cands)
    best = votes.most_common(2)
    hit = best[0][0] if best and (len(best) == 1 or best[0][1] > best[1][1]) else None
    out.append((a, name, obj, hit, used))
with open(sys.argv[5], 'w') as f:
    for a, name, obj, hit, used in out:
        f.write('%08X\t%s\t%s\t%s\t%d\n' % (a, name, obj, '%08X' % hit if hit else '-', used))
print(sum(1 for r in out if r[3]), 'of', len(out), 'matched')
