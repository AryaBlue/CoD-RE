# Print a server function's direct calls (named) aligned with its t6zm twin's calls.
# usage: align.py server.exe server.map t6zm.exe pairs.tsv <name>=<t6addr> ...
import re, struct, sys, bisect, collections, difflib
exec(open(__file__.replace('align.py', 'sigmatch.py')).read().split('sbase, ssecs')[0])
s = pe(sys.argv[1])[1]; t = pe(sys.argv[3])[1]
def sec(secs, n): return [x for x in secs if x[0] == n][0]
_, sva, _, stext = sec(s, '.text'); _, tva, _, ttext = sec(t, '.text')
names, byname = {}, {}
for l in open(sys.argv[2], errors='replace'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', p[0]) and re.match(r'^[0-9a-f]{8}$', p[2]) and p[3] == 'f':
        m = re.match(r'^[?_]?([A-Za-z_][A-Za-z0-9_]*)', p[1]); n = m.group(1) if m else p[1]
        a = int(p[2], 16); names.setdefault(a, n); byname.setdefault(n, a)
addrs = sorted(names)
pairs = {}; rev = {}
for l in open(sys.argv[4]):
    a, b = l.split('\t')[:2]; pairs[int(a, 16)] = int(b, 16); rev[int(b, 16)] = int(a, 16)
NOISE = re.compile(r'Assert|MyAssertHandler|Com_PrintWarning|Com_PrintError|Com_Printf|_RTC_|__security|_chkstk|Profile|PIX|R_Pix|Sys_Assert', re.I)
def s_calls(a):
    k = bisect.bisect_right(addrs, a); e = addrs[k] if k < len(addrs) else a + 0x400
    out = []
    for o in range(a - sva, e - sva - 4):
        if stext[o] in (0xE8, 0xE9):
            x = sva + o + 5 + struct.unpack_from('<i', stext, o + 1)[0]
            if x in names and not NOISE.search(names[x]): out.append(x)
    return out
def t_calls(a):
    o = a - tva; out = []
    while o < len(ttext) - 5:
        if o > a - tva + 16 and o % 16 == 0 and ttext[o - 1] == 0xCC: break
        if ttext[o] in (0xE8, 0xE9):
            x = tva + o + 5 + struct.unpack_from('<i', ttext, o + 1)[0]
            if tva <= x < tva + len(ttext): out.append(x)
        o += 1
    return out
for arg in sys.argv[5:]:
    n, ta = arg.split('='); ta = int(ta, 16); sa = byname[n]
    sc, tc = s_calls(sa), t_calls(ta)
    print('==== %s  server 0x%08X  t6zm 0x%08X  (%d / %d calls)' % (n, sa, ta, len(sc), len(tc)))
    sm = difflib.SequenceMatcher(None, [pairs.get(c, -c) for c in sc], tc, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        L = max(i2 - i1, j2 - j1)
        for k in range(L):
            x = sc[i1 + k] if i1 + k < i2 else None; y = tc[j1 + k] if j1 + k < j2 else None
            mark = {'equal': '=', 'replace': '~' if i2 - i1 == j2 - j1 else '?', 'delete': '-', 'insert': '+'}[tag]
            print('  %s %-40s %s%s' % (mark, names[x] if x else '', '0x%08X' % y if y else '', ('  (' + names[rev[y]] + ')') if y in rev and mark != '=' else ''))
