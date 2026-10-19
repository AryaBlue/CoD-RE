# Map server data symbols to t6zm via matched function pairs: data addresses referenced in the same order.
# usage: globals.py server.exe server.map t6zm.exe all_pairs.tsv out.tsv
import re, struct, sys, bisect, collections
exec(open(__file__.replace('globals.py', 'sigmatch.py')).read().split('sbase, ssecs')[0])
sbase, ssecs = pe(sys.argv[1]); tbase, tsecs = pe(sys.argv[3])
def sec(secs, n): return [s for s in secs if s[0] == n][0]
_, sva, _, stext = sec(ssecs, '.text'); _, tva, _, ttext = sec(tsecs, '.text')
_, sdva, sdvs, _ = sec(ssecs, '.data'); _, tdva, tdvs, _ = sec(tsecs, '.data')

data = []; faddrs = []
for l in open(sys.argv[2], errors='replace'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', p[0]) and re.match(r'^[0-9a-f]{8}$', p[2]):
        a = int(p[2], 16)
        if p[3] == 'f': faddrs.append(a)
        elif sdva <= a < sdva + sdvs:
            m = re.match(r'^[?_]?([A-Za-z_][A-Za-z0-9_]*)', p[1]); data.append((a, m.group(1) if m else p[1], p[-1]))
data.sort(); daddr = [d[0] for d in data]; faddrs = sorted(set(faddrs))

def s_end(a):
    k = bisect.bisect_right(faddrs, a); return faddrs[k] if k < len(faddrs) else a + 0x100
def t_end(a):
    o = a - tva + 16
    while o < len(ttext):
        if o % 16 == 0 and ttext[o - 1] == 0xCC: return tva + o
        o += 1
    return a + 0x100
def drefs(text, base, a, e, lo, hi):
    out = []; o = a - base
    while o < e - base - 3:
        v = struct.unpack_from('<I', text, o)[0]
        if lo <= v < hi: out.append((v, text[o - 2:o])); o += 4
        else: o += 1
    return out

votes = collections.defaultdict(collections.Counter)
for l in open(sys.argv[4]):
    s, t = [int(x, 16) for x in l.split('\t')[:2]]
    a = drefs(stext, sva, s, s_end(s), sdva, sdva + sdvs)
    b = drefs(ttext, tva, t, t_end(t), tdva, tdva + tdvs)
    import difflib
    sm = difflib.SequenceMatcher(None, [k for _, k in a], [k for _, k in b], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal': continue
        for (x, _), (y, _) in zip(a[i1:i2], b[j1:j2]):
                k = bisect.bisect_right(daddr, x) - 1
                if k < 0: continue
                sym, off = data[k], x - data[k][0]
                votes[sym][y - off] += 1           # symbol base in t6zm
with open(sys.argv[5], 'w') as f:
    for sym, v in sorted(votes.items()):
        (best, n), = v.most_common(1)
        tot = sum(v.values())
        if n >= 2 and n * 2 > tot:
            f.write('%08X\t%08X\t%s\t%s\t%d/%d\n' % (sym[0], best, sym[1], sym[2], n, tot))
print(len(votes), 'symbols seen')
