"""Print field lists of selected structs from the OAT T5 and T6 headers side by side (difflib unified)."""
import difflib, re, sys
d = sys.argv[1]
def bodies(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    out = {}
    for m in re.finditer(r'^\s*(struct|union)\s+(\w+)\s*\n\s*\{', src, re.M):
        i = src.index('{', m.end() - 1); depth = 0
        for j in range(i, len(src)):
            if src[j] == '{': depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0: break
        lines = [re.sub(r'\s+', ' ', l.split('//')[0]).strip() for l in src[i + 1:j].splitlines()]
        out.setdefault(m.group(2), [l for l in lines if l and l not in ('{', '}', '};')])
    return out
t5, t6 = bodies(d + '/T5_Assets.h'), bodies(d + '/T6_Assets.h')
for name in sys.argv[2:]:
    a, b = t5.get(name), t6.get(name)
    print('=' * 20, name, '=' * 20)
    if a is None or b is None:
        print('T5:' if a else 'T5: (none)'); print('\n'.join(a or [])); print('T6:' if b else 'T6: (none)'); print('\n'.join(b or [])); continue
    for l in difflib.unified_diff(a, b, 'T5', 'T6', n=99, lineterm=''):
        if l.startswith(('---', '+++', '@@')): continue
        print(l)
