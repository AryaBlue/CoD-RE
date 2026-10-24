"""Resolve far string pointers in the BoD entity list by local-delta voting: a candidate delta scores by how many nearby pointers it also lands on clean string starts."""
import bisect, json, re, struct
from collections import Counter
import entitylist as E

mm = E.mm
D0 = 0x1d234570 - 0xd0513d9      # script_struct anchor
SPAN = 0x6000                    # search half-width around D0
NEAR = 0x400                     # neighbourhood (in pointer space) used for voting
ID = re.compile(rb"[A-Za-z0-9_$][A-Za-z0-9_ ./:,\-\$#]{0,200}\x00")

def collect():
    ptrs = Counter()
    for st, n in E.runs():
        for k in range(n):
            r = st + k * 0x20
            key, = struct.unpack_from("<Q", mm, r); t, = struct.unpack_from("<H", mm, r + 0x18); p, = struct.unpack_from("<Q", mm, r + 8)
            for q in ((key,) + ((p,) if t == E.STRING else ())):
                if q >> 32 == 0x40000000 and E.ptr_str(q).startswith("<ptr:"): ptrs[q & 0xFFFFFFFF] += 1
    return ptrs

def starts(lo, hi):
    return {m.start() for m in ID.finditer(mm, max(lo, 1), hi) if mm[m.start() - 1] == 0}

def solve(ptrs, base=D0):
    vs = sorted(ptrs)
    S = starts(vs[0] + base - SPAN, vs[-1] + base + SPAN)
    out = {}
    for v in vs:
        cands = [P - v for P in range(v + base - SPAN, v + base + SPAN) if P in S]
        if not cands: continue
        a = bisect.bisect_left(vs, v - NEAR); b = bisect.bisect_right(vs, v + NEAR)
        nb = [w for w in vs[a:b] if w != v]
        best = max(cands, key=lambda d: (sum(1 for w in nb if w + d in S), -abs(d - base)))
        score = sum(1 for w in nb if w + best in S)
        if score >= max(2, len(nb) // 2) or (not nb and abs(best - base) < 0x400): out[v] = (v + best, score, len(nb))
    return out

if __name__ == "__main__":
    ptrs = collect()
    m = solve(Counter({v: c for v, c in ptrs.items() if v >= 0x7200000}))
    m.update(solve(Counter({v: c for v, c in ptrs.items() if v < 0x7200000}), E.DELTA))
    try: prev = json.load(open(r"F:\ClaudeWork\bo4_recon\strpool_map.json"))
    except FileNotFoundError: prev = {}
    hits = sum(ptrs[v] for v in m)
    print(f"unique ptrs {len(ptrs)} resolved {len(m)}; references covered {hits}/{sum(ptrs.values())}")
    prev.update({f"{v:x}": E.cstr(P) for v, (P, _, _) in m.items()})
    json.dump(prev, open(r"F:\ClaudeWork\bo4_recon\strpool_map.json", "w"), indent=0)
    for v in (0xd0513d9, 0xd024ab7, 0xd0eae4d, 0xd111411, 0xd11ba71, 0xd01a8c7, 0xd024ac4, 0xd01a8da, 0xd0fb8b9, 0xd044fbb):
        print(hex(v), repr(E.cstr(m[v][0])) if v in m else None, m[v][1:] if v in m else "")
