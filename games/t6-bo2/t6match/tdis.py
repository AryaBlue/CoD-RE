"""Disassemble functions of the server exe with names from its .map (capstone).
usage: tdis.py CoDMPServer_PC.exe <hexaddr>..."""
import sys, re, bisect
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
MAP = sys.argv[1].rsplit('.', 1)[0] + '.map'  # the .map next to the server exe
p = PE(sys.argv[1]); names = {}
for l in open(MAP, errors='replace'):
    q = l.split()
    if len(q) >= 3 and re.match(r'^[0-9a-f]{4}:[0-9a-f]{8}$', q[0]) and re.match(r'^[0-9a-f]{8}$', q[2]):
        m = re.match(r'^[?_]?([A-Za-z_][A-Za-z0-9_]*)', q[1]); names.setdefault(int(q[2], 16), m.group(1) if m else q[1])
addrs = sorted(names)
md = Cs(CS_ARCH_X86, CS_MODE_32)
def nm(v):
    if v in names: return names[v]
    k = bisect.bisect_right(addrs, v)
    if k and v - addrs[k-1] < 0x400: return '%s+%x' % (names[addrs[k-1]], v - addrs[k-1])
for a in sys.argv[2:]:
    a = int(a, 16); k = bisect.bisect_right(addrs, a); end = addrs[k] if k < len(addrs) else a + 0x200
    print('==== %s 0x%x' % (names.get(a, '?'), a))
    code = p.d[p.off(a):p.off(a) + (end - a)]
    for i in md.disasm(code, a):
        ann = []
        for h in re.findall(r'0x[0-9a-f]{5,8}', i.op_str):
            n = nm(int(h, 16))
            if n: ann.append(n)
        print('  %08x  %-6s %-40s %s' % (i.address, i.mnemonic, i.op_str, ('; ' + ', '.join(ann)) if ann else ''))
