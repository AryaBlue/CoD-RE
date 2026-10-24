"""Cross-check bounds-matched names against a BoD model catalog (default: the xpak render catalog, which includes static
scenery) and fix names in two gated passes; writes *_catcheck.json beside each input.
  sibling - a listed variant/family sibling is catalogued, same object category, in the rip;
  edit    - a catalogued, ripped, same-category name within edit distance 3 whose bounds ALSO fit the record.
Usage (64-bit Python): catalog_check.py [--catalog bod_render_catalog_xpak.json] [--max-ed 3]"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import match_placements as M  # noqa: E402

GEO = Path(r"E:\ClaudeWork\bo3\bod_port\t8_world\geo")
RIP = Path(r"E:\ClaudeWork\bo3\greyhound\app\exported_files\black_ops_4\xmodels")
FILES = ["bod_props_bounds_confident.json", "bod_props_arch_resolved.json", "bod_props_arch_tiebreak.json", "bod_props_arch_proxy.json"]


KINDS = [("rubble", ("debris", "rubble", "junk_pile", "junk_trim", "dust_trim")), ("rock", ("rock",)), ("pillar", ("pillar",)),
         ("pipe", ("pipe",)), ("beam", ("beam", "ibeam")), ("metal_sheet", ("sheet_metal",)), ("molding", ("molding",))]


def kind(name):
    """Object category for swap gating: rubble->rubble is fine, rubble->fireplace grate is not."""
    return next((k for k, keys in KINDS if any(w in name for w in keys)), None)


MATERIALS = ("concrete", "wood", "metal", "brick", "stone", "glass", "cloth", "ice")


def same_kind(a, b, stem_len=12):
    ma, mb = {m for m in MATERIALS if m in a}, {m for m in MATERIALS if m in b}
    if ma and mb and not ma & mb:  # concrete chunk -> wood splinter pile is a different object
        return False
    ka, kb = kind(a), kind(b)
    return ka == kb if ka or kb else a[:stem_len] == b[:stem_len]  # uncategorised: same family prefix


def names(obj):
    """Accept a list of names, a list of {name|model: ...} (null names skipped) or a {name: ...} dict."""
    if isinstance(obj, dict):
        obj = obj.get("names") or obj.get("models") or obj.get("catalog") or list(obj)
    out = (o if isinstance(o, str) else o.get("name") or o.get("model") for o in obj)
    return {n.lower() for n in out if n}


def edit_distance(a, b, cap):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="bod_render_catalog_xpak.json")
    ap.add_argument("--max-ed", type=int, default=3)
    args = ap.parse_args()
    cat = names(json.loads((GEO / args.catalog).read_text()))
    rip = {d.name.lower() for d in RIP.iterdir()}
    table = json.loads(M.BOUNDS.read_text())
    recs = M.records()
    pool = sorted(n for n in cat if n in rip and n in table)
    print(f"catalog {args.catalog}: {len(cat)} names, {len(pool)} ripped with bounds")

    @lru_cache(maxsize=None)
    def near(model):
        return tuple(n for n in pool if n != model and same_kind(model, n) and edit_distance(model, n, args.max_ed) <= args.max_ed)

    def fits(p, name):
        r = recs[p["record"]]
        lo, hi = np.array(table[name][0]), np.array(table[name][1])
        a = M.forward(r["inv"], True) * p.get("k", 1.0)
        size = float((r["absmax"] - r["absmin"]).max())
        e = M.errors(r, a, ((lo + hi) / 2)[None], ((hi - lo) / 2)[None])[0]
        return e < max(4.0, 0.03 * size), e

    for f in FILES:
        rows = json.loads((GEO / f).read_text())
        by, flagged, swaps = defaultdict(Counter), Counter(), Counter()
        for p in rows:
            model = p["model"].lower()
            key = "in catalog"
            if model not in cat:
                alt = next((v for v in p.get("variants", []) if v.lower() in cat and v.lower() in rip and same_kind(model, v.lower())), None)
                if alt:
                    key = "sibling swap"
                else:
                    fit = sorted((e, n) for n in near(model) for ok, e in [fits(p, n)] if ok)
                    alt = fit[0][1] if fit else None
                    key = "edit swap" if alt else "edit near, bounds reject" if near(model) else "NOT in catalog"
                if alt:
                    p["swapped_from"], p["model"] = p["model"], alt
                    swaps[(p["swapped_from"], alt)] += 1
            p["in_catalog"] = key in ("in catalog", "sibling swap", "edit swap")
            by[p.get("tier", "confident")][key] += 1
            if not p["in_catalog"]:
                flagged[p["model"]] += 1
        (GEO / f.replace(".json", "_catcheck.json")).write_text(json.dumps(rows))
        print(f"\n{f} ({len(rows)}):")
        for tier, c in by.items():
            n = sum(c.values())
            print(f"  {tier:10s} {n:6d}  " + "  ".join(f"{k} {v} ({v / n:.0%})" for k, v in c.most_common()))
        print("  top swaps:", swaps.most_common(8))
        print("  top NOT-in-catalog:", flagged.most_common(8))


if __name__ == "__main__":
    main()
