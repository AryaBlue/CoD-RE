"""Check that a GSC script's calls into stock scripts exist: python check_refs.py <script.gsc> <decompiled dir>"""
import re
import sys
from pathlib import Path

rt = Path(sys.argv[1]).read_text()
defs = {}
for f in Path(sys.argv[2]).glob('*.gsc'):
    for m in re.finditer(r'^([a-z_0-9]+)\s*\(', f.read_text(errors='ignore'), re.M):
        defs.setdefault(m.group(1), set()).add(f.name)
for path, fn in sorted(set(re.findall(r'([a-z_\\]+)::([a-z_0-9]+)', rt))):
    want = path.split('\\')[-1] + '.gsc'
    print(('OK      ' if want in defs.get(fn, ()) else 'MISSING ') + path + '::' + fn)
own = set(re.findall(r'^([a-z_0-9]+)\s*\(', rt, re.M))
calls = set(re.findall(r'(?<![:\w.])([a-z_][a-z_0-9]*)\s*\(', rt))
print('unqualified calls defined in stock scripts:')
for c in sorted(calls - own):
    if c in defs:
        print('   ', c, sorted(defs[c])[:4])
