# Seeds (string matches over ALL functions) + call-sequence propagation, server -> t6zm.
# usage: propagate.py server.exe server.map t6zm.exe out.tsv
import re, struct, sys, bisect, collections
src = open(__file__.replace('propagate.py', 'strmatch.py')).read()
exec(src.split('by_func = collections')[0].replace("__file__.replace('strmatch.py', 'sigmatch.py')", "__file__.replace('propagate.py', 'sigmatch.py')"))

names = {}
for l in open(sys.argv[2], errors='replace'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', p[0]) and re.match(r'^[0-9a-f]{8}$', p[2]) and p[3] == 'f':
        m = re.match(r'^[?_]?([A-Za-z_][A-Za-z0-9_]*)', p[1])
        names[int(p[2], 16)] = (m.group(1) if m else p[1], p[-1])

by_func = collections.defaultdict(set)
for s, fs in srefs.items():
    for f in fs: by_func[f].add(s)
pairs = {}
for a in addrs:
    votes = collections.Counter()
    for s in by_func.get(a, ()):
        c = trefs.get(s, set())
        if 0 < len(c) <= 2 and len(srefs[s]) <= 2:
            for x in c: votes[x] += 1.0 / len(c)
    b = votes.most_common(2)
    if b and (len(b) == 1 or b[0][1] > b[1][1]): pairs[a] = b[0][0]
# drop many-to-one seeds
cnt = collections.Counter(pairs.values())
pairs = {a: t for a, t in pairs.items() if cnt[t] == 1}
print('seeds', len(pairs))

_, sva, _, stext = sec(ssecs, '.text')
def s_end(a):
    k = bisect.bisect_right(addrs, a); return addrs[k] if k < len(addrs) else a + 0x100
def t_end(a):
    o = a - ttva + 16
    while o < len(ttext):
        if o % 16 == 0 and ttext[o - 1] == 0xCC: return ttva + o
        o += 1
    return a + 0x100
def calls(text, base, a, e):
    out = []; o = a - base
    while o < e - base - 4:
        if text[o] == 0xE8:
            t = base + o + 5 + struct.unpack_from('<i', text, o + 1)[0]
            if base <= t < base + len(text): out.append(t); o += 5; continue
        o += 1
    return out
NOISE = re.compile(r'Assert|MyAssertHandler|Com_PrintWarning|Com_PrintError|Com_Printf|Sys_IsMainThread|_RTC_|__security|_chkstk|Profile|PIXBegin|PIXEnd|R_PixBegin|R_PixEnd|Sys_Assert', re.I)
votes = collections.defaultdict(collections.Counter)
for rnd in range(12):
    new = 0
    for a, t in list(pairs.items()):
        sc = [c for c in calls(stext, sva, a, s_end(a)) if c in names and not NOISE.search(names[c][0])]
        tc = calls(ttext, ttva, t, t_end(t))
        if not sc or not tc: continue
        if len(sc) == len(tc):
            for x, y in zip(sc, tc): votes[x][y] += 1
            continue
        import difflib
        sm = difflib.SequenceMatcher(None, [pairs.get(c, -c) for c in sc], tc, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for x, y in zip(sc[i1:i2], tc[j1:j2]): votes[x][y] += 1
    for x, v in votes.items():
        if x in pairs: continue
        b = v.most_common(2)
        if b[0][1] >= 1 and (len(b) == 1 or b[0][1] >= 2 * b[1][1]) and b[0][0] not in set(pairs.values()):
            pairs[x] = b[0][0]; new += 1
    print('round', rnd, 'added', new, 'total', len(pairs))
    if not new: break
with open(sys.argv[4], 'w') as f:
    for a in sorted(pairs):
        n, o = names.get(a, ('?', '?'))
        f.write('%08X\t%08X\t%s\t%s\n' % (a, pairs[a], n, o))
