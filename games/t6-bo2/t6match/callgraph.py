# Named call graph of the server exe (direct calls + function-pointer tables), and call trees from given roots.
# usage: callgraph.py server.exe server.map tree <root> [depth] [filter-regex] | table <func> | callers <func>
import re, struct, sys, bisect, collections
exec(open(__file__.replace('callgraph.py', 'sigmatch.py')).read().split('sbase, ssecs')[0])
sbase, ssecs = pe(sys.argv[1])
def sec(n): return [s for s in ssecs if s[0] == n][0]
_, tva, _, text = sec('.text')
names, byname = {}, {}
for l in open(sys.argv[2], errors='replace'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', p[0]) and re.match(r'^[0-9a-f]{8}$', p[2]) and p[3] == 'f':
        m = re.match(r'^[?_]?([A-Za-z_][A-Za-z0-9_]*)', p[1]); n = m.group(1) if m else p[1]
        a = int(p[2], 16); names.setdefault(a, n); byname.setdefault(n, a)
addrs = sorted(names)
def func_of(va):
    k = bisect.bisect_right(addrs, va); return addrs[k - 1] if k else None
calls = collections.defaultdict(list)
for m in re.finditer(b'\xe8', text):
    o = m.start()
    if o + 5 > len(text): break
    t = tva + o + 5 + struct.unpack_from('<i', text, o + 1)[0]
    if t in names:
        f = func_of(tva + o)
        if f is not None: calls[f].append(t)
# function-pointer tables in .rdata/.data: runs of >= 4 dwords that are all function starts
tables = {}
for nm in ('.rdata', '.data'):
    _, va, _, d = sec(nm)
    o = 0; n = len(d) - 4
    while o < n:
        run = []
        while o < n and struct.unpack_from('<I', d, o)[0] in names:
            run.append(struct.unpack_from('<I', d, o)[0]); o += 4
        if len(run) >= 4: tables[va + o - 4 * len(run)] = run
        o += 4 if not run else 0
# which functions reference a table (imm32 of its base, or base-4..+8)
tref = collections.defaultdict(list)
keys = set(tables)
for m in re.finditer(b'(?=(....))', text, re.S):
    v = struct.unpack_from('<I', text, m.start())[0]
    if v in keys:
        f = func_of(tva + m.start())
        if f is not None: tref[f].append(v)
NOISE = re.compile(r'Assert|MyAssertHandler|Com_Print|Com_DPrint|Sys_IsMainThread|_RTC_|__security|_chkstk|Profile_|PIX|R_Pix|Sys_Assert|^memset$|^memcpy$|^strcmp|^_?str|^Q_str|^I_str|va$|^Com_sprintf|^Dvar_|^Sys_Milliseconds|^Sys_EnterCritical|^Sys_LeaveCritical|^R_WarnOncePerFrame|^Hunk_|^__|^_', re.I)

cmd = sys.argv[3]
if cmd == 'tree':
    root = byname[sys.argv[4]]; depth = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    filt = re.compile(sys.argv[6]) if len(sys.argv) > 6 else None
    seen = set()
    def walk(f, d, pre):
        kids = []
        for c in calls.get(f, []):
            if c not in kids and not NOISE.search(names[c]): kids.append(c)
        tabs = tref.get(f, [])
        print('%s%s  0x%08X%s%s' % (pre, names[f], f, '  [table x%d]' % sum(len(tables[t]) for t in tabs) if tabs else '', '  (seen)' if f in seen else ''))
        if f in seen or d >= depth: return
        seen.add(f)
        for c in kids:
            if filt is None or filt.search(names[c]): walk(c, d + 1, pre + '  ')
    walk(root, 0, '')
elif cmd == 'table':
    f = byname[sys.argv[4]]
    for t in tref.get(f, []):
        print('table @0x%08X' % t)
        for i, x in enumerate(tables[t]): print('  [%d] %s 0x%08X' % (i, names[x], x))
elif cmd == 'callers':
    f = byname[sys.argv[4]]
    for g, cs in calls.items():
        if f in cs: print(names[g], '0x%08X' % g)
if cmd == 'findtable':
    f = byname[sys.argv[4]]
    for t, run in tables.items():
        if f in run:
            print('table @0x%08X (%d entries), referenced by: %s' % (t, len(run), [names[g] for g, ts in tref.items() if t in ts]))
            for i, x in enumerate(run): print('  [%d] %s 0x%08X' % (i, names[x], x))
    _, va, _, d = sec('.rdata')
    for nm in ('.rdata', '.data'):
        _, va, _, d = sec(nm)
        for m in re.finditer(re.escape(struct.pack('<I', f)), d): print('raw ref in', nm, '0x%08X' % (va + m.start()))
if cmd == 'up':
    f = byname[sys.argv[4]]; depth = int(sys.argv[5])
    rev = collections.defaultdict(set)
    for g, cs in calls.items():
        for c in cs: rev[c].add(g)
    def up(x, d, pre):
        print(pre + names[x] + '  0x%08X' % x)
        if d < depth:
            for g in sorted(rev.get(x, ())): up(g, d + 1, pre + '  ')
    up(f, 0, '')
if cmd == 'refs':
    f = byname[sys.argv[4]]
    for m in re.finditer(re.escape(struct.pack('<I', f)), text):
        g = func_of(tva + m.start()); print('imm ref in', names.get(g, '?'), '0x%08X' % (tva + m.start()))
    for nm in ('.rdata', '.data'):
        _, va, _, d = sec(nm)
        for m in re.finditer(re.escape(struct.pack('<I', f)), d): print('data ref', nm, '0x%08X' % (va + m.start()))
