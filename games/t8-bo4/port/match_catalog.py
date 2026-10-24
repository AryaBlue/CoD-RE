"""Catalog-restricted re-match of ALL static-model records against the render catalog (bod_render_catalog_xpak.json
intersected with rip bounds), merged with the earlier picks into one per-placement name set for the rebuild.
Per record: classify against catalog models (exact / variant / family / bestfit / proxy, as match_arch.py);
a catalog pick replaces an earlier pick only when it is exact/variant/family/proxy or the same category and material;
otherwise the earlier pick stays (the catalog has unnamed hashes, so absence is not evidence).
Usage (64-bit Python): match_catalog.py [--min-size 24]"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, r"E:\ClaudeWork\bo3\bod_port\geo")
import match_placements as M  # noqa: E402
from catalog_check import names as catalog_names, same_kind  # noqa: E402
from match_arch import placement, stem, LANDMARK  # noqa: E402

GEO = Path(r"E:\ClaudeWork\bo3\bod_port\t8_world\geo")
PRIOR = ["bod_props_bounds_confident.json", "bod_props_arch_resolved.json", "bod_props_arch_tiebreak.json", "bod_props_arch_proxy.json"]
OUT = GEO / "bod_placements_catalog.json"
SKIP = ("collision_", "nodraw")  # helper meshes, never rendered


def classify(r, a, size, names, lo, hi, centre, half):
    """(tier, index, k, err) of the best catalog fit for one record, or None."""
    rc, rh = (r["absmin"] + r["absmax"]) / 2, (r["absmax"] - r["absmin"]) / 2
    tol = max(4.0 if size >= 128 else 2.0, 0.03 * size)
    e = M.errors(r, a, centre, half)
    order = np.argsort(e)
    fit = [j for j in order[:16] if e[j] < tol]
    if fit:
        if len(fit) == 1 or e[fit[1]] >= 2 * e[fit[0]] + 0.5:
            return "exact", fit[0], 1.0, e[fit[0]]
        if all(np.abs(lo[j] - lo[fit[0]]).max() < 0.5 and np.abs(hi[j] - hi[fit[0]]).max() < 0.5 for j in fit):
            return "variant", fit[0], 1.0, e[fit[0]]
        near = [j for j in fit if e[j] < 2 * e[fit[0]] + 0.5]
        return ("family" if len({stem(names[j]) for j in near}) == 1 else "bestfit"), fit[0], 1.0, e[fit[0]]
    wh, wc = half @ np.abs(a).T, centre @ a.T
    k = (wh * rh).sum(1) / np.maximum((wh * wh).sum(1), 1e-9)
    res = np.maximum(np.abs(r["origin"] + wc * k[:, None] - rc).max(1), np.abs(wh * k[:, None] - rh).max(1))
    res[(k < 0.85) | (k > 1.2)] = np.inf
    po = np.argsort(res)[:2]
    if res[po[0]] < tol and res[po[1]] >= 2 * res[po[0]] + 0.5:
        return "proxy", po[0], float(k[po[0]]), res[po[0]]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-size", type=float, default=24.0)
    args = ap.parse_args()
    table = json.loads(M.BOUNDS.read_text())
    cat = catalog_names(json.loads((GEO / "bod_render_catalog_xpak.json").read_text()))
    names = sorted(n for n in table if n in cat and not n.startswith(SKIP))
    lo = np.array([table[n][0] for n in names]); hi = np.array([table[n][1] for n in names])
    centre, half = (lo + hi) / 2, (hi - lo) / 2
    prior = {}
    for f in PRIOR:
        for p in json.loads((GEO / f).read_text()):
            prior.setdefault(p["record"], dict(p, tier=p.get("tier", "confident")))
    print(f"catalog pool {len(names)} models; prior picks {len(prior)}")
    out, status, changed = [], Counter(), Counter()
    for i, r in enumerate(M.records()):
        size = float((r["absmax"] - r["absmin"]).max())
        old = prior.get(i)
        if old and old["model"].startswith(SKIP):
            status["dropped helper"] += 1
            continue
        hit = None
        if size >= args.min_size:
            a = M.forward(r["inv"], True)
            c = classify(r, a, size, names, lo, hi, centre, half)
            if c and (c[0] != "bestfit" or size >= 128 or old):
                tier, j, k, err = c
                rc = (r["absmin"] + r["absmax"]) / 2
                meta = {"contents": int(r["contents"]), "record": i, "size": round(size, 1),
                        "dist_landmark": round(float(np.linalg.norm(rc - LANDMARK)))}
                hit = placement(r, a, names[j], k, tier=tier, err=round(float(err), 3), source="catalog",
                                **({"k": round(k, 4)} if tier == "proxy" else {}), **meta)
        if old and hit and hit["model"] != old["model"]:
            if hit["tier"] in ("exact", "variant", "family", "proxy") or same_kind(old["model"], hit["model"]):
                hit["prior_model"] = old["model"]
                changed[(old["model"], hit["model"])] += 1
                status[f"corrected ({hit['tier']})"] += 1
                out.append(hit)
            else:
                status["kept prior (catalog pick crossed category)"] += 1
                out.append(dict(old, source="prior"))
        elif hit:
            status["confirmed" if old else f"NEW ({hit['tier']})"] += 1
            out.append(hit if not old else dict(old, source="catalog-confirmed"))
        elif old:
            status["kept prior (no catalog fit)"] += 1
            out.append(dict(old, source="prior"))
        else:
            status["unresolved"] += 1
    OUT.write_text(json.dumps(out))
    print(dict(status))
    print(f"{len(out)} placements, {len({p['model'] for p in out})} models -> {OUT}")
    print("top corrections:", changed.most_common(12))


if __name__ == "__main__":
    main()
