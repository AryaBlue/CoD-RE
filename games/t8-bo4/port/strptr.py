"""Resolve BO4 stream string pointers (0x40000000_xxxxxxxx) to .dec offsets via a monotone piecewise delta learned from anchors."""
import bisect, re
import entitylist as E

mm = E.mm
STR_RE = re.compile(rb"[\x20-\x7e]{1,250}\x00")

def string_starts(lo, hi):
    out = []
    for m in STR_RE.finditer(mm, lo, hi):
        if mm[m.start() - 1] == 0: out.append(m.start())
    return out

class Resolver:
    def __init__(self, ptrs, anchors, lo=0x1d000000, hi=0x1d400000, window=(0x101d0000, 0x10200000)):
        self.starts = string_starts(lo, hi)
        self.sset = set(self.starts)
        self.window = window
        self.map = dict(anchors)
        self.solve(sorted(set(ptrs)))

    def bounds(self, v):
        ks = sorted(self.map); i = bisect.bisect_left(ks, v)
        lo = self.map[ks[i - 1]] - ks[i - 1] if i > 0 else self.window[0]
        hi = self.map[ks[i]] - ks[i] if i < len(ks) else self.window[1]
        if i < len(ks) and ks[i] == v: lo = hi = self.map[v] - v
        return lo, hi

    def solve(self, ptrs):
        changed = True
        while changed:
            changed = False
            for v in ptrs:
                if v in self.map: continue
                lo, hi = self.bounds(v)
                if lo > hi: continue
                a = bisect.bisect_left(self.starts, v + lo); b = bisect.bisect_right(self.starts, v + hi)
                cands = self.starts[a:b]
                if len(cands) == 1: self.map[v] = cands[0]; changed = True
        self.ambig = [v for v in ptrs if v not in self.map]

    def get(self, v):
        if v < 0x7200000:
            o = v + E.DELTA
            return E.cstr(o) if mm[o - 1] == 0 else None
        o = self.map.get(v)
        return E.cstr(o) if o is not None else None

    def guess(self, v):
        # ambiguous pointer: nearest-delta candidate
        lo, hi = self.bounds(v)
        a = bisect.bisect_left(self.starts, v + lo)
        return E.cstr(self.starts[a]) if a < len(self.starts) and self.starts[a] <= v + hi else None
