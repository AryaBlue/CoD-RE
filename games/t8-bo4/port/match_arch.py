"""Large-architecture placement resolution (records >= 128u that match_confident left unresolved), in three tiers:
  exact   - one rip model fits within max(4u, 3% of size), best < half the runner-up (match_confident's rule);
  variant - every fitting model has identical local bounds (texture variants like _dark/_grime): geometry is certain;
  family  - the near-tied fits share one name stem (pillar_ext_01/02/03): near-identical geometry, best fit taken;
  bestfit - other near-ties: the closest-fitting shape (family + bestfit go to arch_tiebreak.json);
  proxy   - no 1:1 fit, but one model fits after a uniform extra scale k (0.85..1.2) - same shape, size unconfirmed.
Everything else big is the rip gap: no ripped model has its shape (a Greyhound shopping list, with solved local size).
Usage (64-bit Python): match_arch.py [--min-size 128]"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, r"E:\ClaudeWork\bo3\bod_port\geo")
import match_placements as M  # noqa: E402
from smodel_lib import axis_to_angles, axis_roundtrip_error  # noqa: E402

GEO = Path(r"E:\ClaudeWork\bo3\bod_port\t8_world\geo")
CONF = GEO / "bod_props_bounds_confident.json"
LANDMARK = np.array([-1815.0, 8033.0, 1432.0])  # s_warden_box


VARIANT_SUFFIX = re.compile(r"(_(\d+|dark|grime|frosted|flat|red|white|wet|crooked|burnt|oak|seaside|lod))+$")


def stem(name):
    return VARIANT_SUFFIX.sub("", name)


def placement(r, a, model, kscale=1.0, **extra):
    scale = float(np.linalg.norm(a, axis=0).mean())
    axis = (a / np.linalg.norm(a, axis=0)).T.ravel()  # COD rows forward/left/up = columns of local->world
    if np.linalg.det(axis.reshape(3, 3)) < 0 or axis_roundtrip_error(axis) > 1e-3:
        return None
    return {"model": model, "origin": r["origin"].astype(float).round(4).tolist(), "angles": [round(x, 4) for x in axis_to_angles(axis)],
            "axis": axis.round(6).tolist(), "scale": round(scale * kscale, 6), **extra}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-size", type=float, default=128.0)
    args = ap.parse_args()
    table = json.loads(M.BOUNDS.read_text())
    names = sorted(table)
    lo = np.array([table[n][0] for n in names]); hi = np.array([table[n][1] for n in names])
    centre, half = (lo + hi) / 2, (hi - lo) / 2
    done = {p["record"] for p in json.loads(CONF.read_text())}
    out, tie, proxy, gap, status = [], [], [], [], Counter()
    for i, r in enumerate(M.records()):
        size = float((r["absmax"] - r["absmin"]).max())
        if i in done or size < args.min_size:
            continue
        a = M.forward(r["inv"], True)
        rc, rh = (r["absmin"] + r["absmax"]) / 2, (r["absmax"] - r["absmin"]) / 2
        tol = max(4.0, 0.03 * size)
        meta = {"contents": int(r["contents"]), "record": i, "size": round(size, 1), "dist_landmark": round(float(np.linalg.norm(rc - LANDMARK)))}
        e = M.errors(r, a, centre, half)
        order = np.argsort(e)
        fit = [j for j in order if e[j] < tol]
        if fit:
            same = all(np.abs(lo[j] - lo[fit[0]]).max() < 0.5 and np.abs(hi[j] - hi[fit[0]]).max() < 0.5 for j in fit)
            clear = len(fit) == 1 or e[fit[1]] >= 2 * e[fit[0]] + 0.5
            if clear or same:
                p = placement(r, a, names[fit[0]], tier="exact" if clear else "variant", err=round(float(e[fit[0]]), 3),
                              variants=[names[j] for j in fit[1:]] if not clear else [], **meta)
                status[p["tier"] if p else "mirrored"] += 1
                if p:
                    out.append(p)
                continue
            near = [j for j in fit if e[j] < 2 * e[fit[0]] + 0.5]
            if len({stem(names[j]) for j in near}) == 1:  # near-ties are one model family (pillar_ext_01/02/03, junk_pile_96/_02/_frosted)
                p = placement(r, a, names[fit[0]], tier="family", err=round(float(e[fit[0]]), 3), variants=[names[j] for j in near[1:]], **meta)
                status["family" if p else "mirrored"] += 1
                if p:
                    tie.append(p)
                continue
            # bestfit: cross-family near-ties; the closest-fitting shape, kept apart as the least certain tier
            p = placement(r, a, names[fit[0]], tier="bestfit", err=round(float(e[fit[0]]), 3), variants=[names[j] for j in near[1:]], **meta)
            status["bestfit" if p else "mirrored"] += 1
            if p:
                tie.append(p)
            continue
        # proxy: least-squares uniform k on the half-sizes, then residual on centre and size
        wh = half @ np.abs(a).T
        wc = centre @ a.T
        k = (wh * rh).sum(1) / np.maximum((wh * wh).sum(1), 1e-9)
        res = np.maximum(np.abs(r["origin"] + wc * k[:, None] - rc).max(1), np.abs(wh * k[:, None] - rh).max(1))
        res[(k < 0.85) | (k > 1.2)] = np.inf
        po = np.argsort(res)
        if res[po[0]] < tol and res[po[1]] >= 2 * res[po[0]] + 0.5:
            p = placement(r, a, names[po[0]], float(k[po[0]]), tier="proxy", k=round(float(k[po[0]]), 4), err=round(float(res[po[0]]), 3), **meta)
            status["proxy" if p else "mirrored"] += 1
            if p:
                proxy.append(p)
            continue
        status["rip gap"] += 1
        local = np.linalg.lstsq(np.abs(a), rh, rcond=None)[0] * 2 / np.linalg.norm(a, axis=0).mean()  # unscaled local size
        gap.append({"record": i, "centre": rc.round(1).tolist(), "aabb": (rh * 2).round(1).tolist(), "local_size": np.abs(local).round(1).tolist(),
                    "scale": round(float(np.linalg.norm(a, axis=0).mean()), 4), "dist_landmark": meta["dist_landmark"],
                    "nearest": names[order[0]], "nearest_err": round(float(e[order[0]]), 1)})
    (GEO / "bod_props_arch_resolved.json").write_text(json.dumps(out))
    (GEO / "bod_props_arch_tiebreak.json").write_text(json.dumps(tie))
    (GEO / "bod_props_arch_proxy.json").write_text(json.dumps(proxy))
    (GEO / "bod_rip_gap.json").write_text(json.dumps(sorted(gap, key=lambda g: g["dist_landmark"])))
    print(dict(status), f"-> arch_resolved {len(out)}, arch_tiebreak {len(tie)}, arch_proxy {len(proxy)}, rip_gap {len(gap)}")
    print("resolved:", Counter(p["model"] for p in out).most_common(12))
    print("proxy:", Counter((p["model"], round(p["k"], 2)) for p in proxy).most_common(12))


if __name__ == "__main__":
    main()
