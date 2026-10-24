"""Flag catalog-restricted NEW picks that a non-catalog ripped model fits at least as well (possible false positives);
writes contested=true onto bod_placements_catalog.json and reports spawn coverage. Usage (64-bit Python): catalog_contest.py"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import match_placements as M  # noqa: E402

GEO = Path(r"E:\ClaudeWork\bo3\bod_port\t8_world\geo")
PATH = GEO / "bod_placements_catalog.json"


def main():
    table = json.loads(M.BOUNDS.read_text())
    names = sorted(n for n in table if n.startswith(("p7_", "p8_")))
    idx = {n: i for i, n in enumerate(names)}
    lo = np.array([table[n][0] for n in names]); hi = np.array([table[n][1] for n in names])
    centre, half = (lo + hi) / 2, (hi - lo) / 2
    recs = M.records()
    rows = json.loads(PATH.read_text())
    stat = Counter()
    for p in rows:
        if p.get("source") != "catalog" or "prior_model" in p:
            continue
        r = recs[p["record"]]
        e = M.errors(r, M.forward(r["inv"], True) * p.get("k", 1.0), centre, half)
        mine = e[idx[p["model"]]] if p["model"] in idx else np.inf
        rivals = [names[j] for j in np.argsort(e)[:6] if names[j] != p["model"] and e[j] <= mine + 0.25]
        p["contested"] = bool(rivals)
        p["rivals"] = rivals[:3]
        stat[(p["tier"], "contested" if rivals else "clean", "big" if p["size"] >= 128 else "small")] += 1
    PATH.write_text(json.dumps(rows))
    for k, v in sorted(stat.items()):
        print(k, v)
    amn, amx = recs["absmin"].astype(float), recs["absmax"].astype(float)
    c, ext = (amn + amx) / 2, amx - amn
    foot = np.clip(ext[:, 0], 1, None) * np.clip(ext[:, 1], 1, None)
    d = np.linalg.norm(c - np.array([-1815, 8033, 1432]), axis=1)
    placed = {p["record"] for p in rows}
    clean = {p["record"] for p in rows if not p.get("contested")}
    for R in (1500, 3000):
        a = np.nonzero((d < R) & (ext.max(1) >= 128))[0]
        print(f"<{R}u arch footprint placed {foot[[i for i in a if i in placed]].sum() / foot[a].sum():.0%}"
              f" (uncontested {foot[[i for i in a if i in clean]].sum() / foot[a].sum():.0%})")
        a = np.nonzero(d < R)[0]
        print(f"   all records placed {sum(i in placed for i in a)}/{len(a)}")


if __name__ == "__main__":
    main()
