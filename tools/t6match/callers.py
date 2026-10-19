# Extra pass: an unmatched server function whose matched callees are all called by exactly one t6zm function -> pair.
# Alternates with call-sequence propagation. usage: callers.py server.exe server.map t6zm.exe pairs_in.tsv pairs_out.tsv
import re, struct, sys, bisect, collections, difflib
exec(open(__file__.replace('callers.py', 'sigmatch.py')).read().split('sbase, ssecs')[0])
sbase, ssecs = pe(sys.argv[1]); tbase, tsecs = pe(sys.argv[3])
def sec(secs, n): return [s for s in secs if s[0] == n][0]
_, sva, _, stext = sec(ssecs, '.text'); _, tva, _, ttext = sec(tsecs, '.text')
names = {}
for l in open(sys.argv[2], errors='replace'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', p[0]) and re.match(r'^[0-9a-f]{8}$', p[2]) and p[3] == 'f':
        m = re.match(r'^[?_]?([A-Za-z_][A-Za-z0-9_]*)', p[1]); names[int(p[2], 16)] = (m.group(1) if m else p[1], p[-1])
addrs = sorted(names)
NOISE = re.compile(r'Assert|MyAssertHandler|Com_PrintWarning|Com_PrintError|Com_Printf|Sys_IsMainThread|_RTC_|__security|_chkstk|Profile|PIXBegin|PIXEnd|R_PixBegin|R_PixEnd|Sys_Assert', re.I)

# t6 function starts: 16-aligned after int3 padding
tstarts = [tva + o for o in range(16, len(ttext), 16) if ttext[o - 1] == 0xCC and ttext[o] != 0xCC]
def t_func(va):
    k = bisect.bisect_right(tstarts, va); return tstarts[k - 1] if k else None
def s_func(va):
    k = bisect.bisect_right(addrs, va); return addrs[k - 1] if k else None
def callgraph(text, base, func_of, valid):
    out = collections.defaultdict(list); o = 0; n = len(text) - 5
    pat = re.compile(b'\xe8', re.S)
    for m in pat.finditer(text):
        o = m.start()
        if o > n: break
        t = base + o + 5 + struct.unpack_from('<i', text, o + 1)[0]
        if valid(t):
            f = func_of(base + o)
            if f: out[f].append(t)
    return out
tset = set(tstarts)
tcalls = callgraph(ttext, tva, t_func, lambda t: t in tset)
scalls = callgraph(stext, sva, s_func, lambda t: t in names)
tcallers = collections.defaultdict(set)
for f, cs in tcalls.items():
    for c in cs: tcallers[c].add(f)

pairs = {}
for l in open(sys.argv[4]):
    s, t = l.split('\t')[:2]; pairs[int(s, 16)] = int(t, 16)
for rnd in range(8):
    used = set(pairs.values()); new = {}
    # A) callers of matched callees
    for f, cs in scalls.items():
        if f in pairs: continue
        mc = {pairs[c] for c in cs if c in pairs and not NOISE.search(names[c][0])}
        if len(mc) < 2: continue
        cand = None
        for c in mc:
            cand = set(tcallers.get(c, ())) if cand is None else cand & tcallers.get(c, set())
            if not cand: break
        cand = {c for c in (cand or ()) if c not in used}
        if len(cand) == 1: new[f] = cand.pop()
    # B) call-sequence gaps inside matched pairs
    votes = collections.defaultdict(collections.Counter)
    for s, t in pairs.items():
        sc = [c for c in scalls.get(s, ()) if not NOISE.search(names[c][0])]
        tc = tcalls.get(t, [])
        if not sc or not tc: continue
        sm = difflib.SequenceMatcher(None, [pairs.get(c, -c) for c in sc], tc, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for x, y in zip(sc[i1:i2], tc[j1:j2]): votes[x][y] += 1
    for x, v in votes.items():
        if x in pairs or x in new: continue
        b = v.most_common(2)
        if len(b) == 1 or b[0][1] >= 2 * b[1][1]: new[x] = b[0][0]
    cnt = collections.Counter(new.values())
    added = 0
    for x, y in new.items():
        if cnt[y] == 1 and y not in used: pairs[x] = y; added += 1
    print('round', rnd, 'added', added, 'total', len(pairs))
    if not added: break
with open(sys.argv[5], 'w', newline='\n') as f:
    for a in sorted(pairs):
        n, o = names.get(a, ('?', '?')); f.write('%08X\t%08X\t%s\t%s\n' % (a, pairs[a], n, o))
