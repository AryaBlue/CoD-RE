"""Bounds oracle for BoD static-model placements. For every collision static-model record (zone @0x1D3898E4, 96 B:
origin, invScaledAxis[3][3], absmin, absmax, u32, flags, u32, u64 xmodel ptr, contents) predict each rip model's world AABB
and compare with absmin/absmax.
  1. validate: score the worker's bod_props.json names (pass/fail);
  2. reverse-match: find the rip models whose transformed bounds fit each record, no hashing involved.
Usage (64-bit Python): match_placements.py [bod_props.json] [--tol 2.0]"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

ZONE = Path(r"PATH/TO/zm_escape.ff.dec")  # set this to your own path
RECORDS, COUNT = 0x1D3898E4, 42559
BOUNDS = Path(r"PATH/TO/rip_bounds.json")  # set this to your own path
OUT = Path(r"PATH/TO/bod_props_bounds_matched.json")  # set this to your own path
REC = np.dtype([("origin", "<3f4"), ("inv", "<9f4"), ("absmin", "<3f4"), ("absmax", "<3f4"), ("u0", "<u4"),
                ("flags", "<u4"), ("u1", "<u4"), ("xmodel", "<u8"), ("contents", "<u4")])


def records():
    with open(ZONE, "rb") as f:
        f.seek(RECORDS)
        return np.frombuffer(f.read(COUNT * REC.itemsize), REC)


def forward(inv, transpose):
    """invScaledAxis -> local-to-world matrix (rows of inv are the axes divided by scale)."""
    m = inv.reshape(3, 3).astype(float)
    scale = 1 / np.linalg.norm(m, axis=1).mean()
    axes = m * scale * scale  # axis_i * scale
    return axes.T if transpose else axes


def errors(rec, a, centre, half):
    """Max abs error between each model's predicted world AABB and the record's (centre and half-size)."""
    rc = (rec["absmin"] + rec["absmax"]) / 2.0
    rh = (rec["absmax"] - rec["absmin"]) / 2.0
    wc = rec["origin"] + centre @ a.T
    wh = half @ np.abs(a).T
    return np.maximum(np.abs(wc - rc).max(1), np.abs(wh - rh).max(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("props", nargs="?", type=Path)
    ap.add_argument("--tol", type=float, default=2.0)
    args = ap.parse_args()
    table = json.loads(BOUNDS.read_text())
    names = sorted(table)
    lo = np.array([table[n][0] for n in names]); hi = np.array([table[n][1] for n in names])
    centre, half = (lo + hi) / 2, (hi - lo) / 2
    recs = records()

    # pick the axis convention that fits more records outright
    best = None
    for transpose in (False, True):
        fits = sum(errors(r, forward(r["inv"], transpose), centre, half).min() < args.tol for r in recs[:2000])
        print(f"convention transpose={transpose}: {fits}/2000 sample records fit some rip model within {args.tol}u")
        best = (fits, transpose) if best is None or fits > best[0] else best
    transpose = best[1]

    matched, status = [], Counter()
    for i, r in enumerate(recs):
        a = forward(r["inv"], transpose)
        e = errors(r, a, centre, half)
        fit = np.nonzero(e < args.tol)[0]
        if len(fit) == 0:
            status["no fit"] += 1
            continue
        cands = sorted((float(e[j]), names[j]) for j in fit)
        status["unique" if len(cands) == 1 else "ambiguous"] += 1
        matched.append({"record": i, "origin": r["origin"].tolist(), "axis": (a / np.linalg.norm(a, axis=0)).T.ravel().round(6).tolist(),
                        "scale": round(float(np.linalg.norm(a, axis=1).mean()), 6), "contents": int(r["contents"]),
                        "candidates": cands[:8]})
    OUT.write_text(json.dumps({"tol": args.tol, "transpose": transpose, "records": COUNT, "matched": matched}))
    print(f"reverse-match over {COUNT} records: {dict(status)} -> {OUT}")

    if args.props:
        placements = json.loads(args.props.read_text())
        by_origin = {tuple(np.round(r["origin"], 2)): i for i, r in enumerate(recs)}
        verdict, examples = Counter(), {}
        for p in placements:
            if not p.get("model"):
                verdict["unnamed"] += 1
                continue
            i = by_origin.get(tuple(np.round(np.array(p["origin"], np.float32), 2)))
            if i is None:
                verdict["no record at origin"] += 1
                continue
            if p["model"] not in table:
                verdict["model not in rip"] += 1
                continue
            j = names.index(p["model"])
            err = errors(recs[i], forward(recs[i]["inv"], transpose), centre[j:j + 1], half[j:j + 1])[0]
            key = "pass" if err < args.tol else "fail"
            verdict[key] += 1
            examples.setdefault(key, Counter())[p["model"]] += 1
        print("worker names:", dict(verdict))
        for key in ("pass", "fail"):
            print(f"  top {key}:", examples.get(key, Counter()).most_common(6))


if __name__ == "__main__":
    main()
