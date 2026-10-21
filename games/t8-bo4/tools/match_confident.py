"""Strict hash-free placement resolution: static props only (p7_/p8_), tolerance max(2u, 3% of size), records >= 24u,
best fit < half the runner-up. Writes smodel-schema placements {model, origin, angles, axis, scale} for stage_bod_geo.py.
Usage (64-bit Python): match_confident.py [out.json]"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))  # match_placements + smodel_lib co-located
import match_placements as M  # noqa: E402
from smodel_lib import axis_to_angles, axis_roundtrip_error  # noqa: E402

OUT = Path(r"PATH/TO/bod_props_bounds_confident.json")  # set this to your own path
MIN_SIZE = 24.0


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    table = json.loads(M.BOUNDS.read_text())
    names = sorted(n for n in table if n.startswith(("p7_", "p8_")))
    lo = np.array([table[n][0] for n in names]); hi = np.array([table[n][1] for n in names])
    centre, half = (lo + hi) / 2, (hi - lo) / 2
    out, status = [], Counter()
    for i, r in enumerate(M.records()):
        a = M.forward(r["inv"], True)
        e = M.errors(r, a, centre, half)
        size = float((r["absmax"] - r["absmin"]).max())
        tol = max(2.0, 0.03 * size)
        best, second = np.argsort(e)[:2]
        if e[best] >= tol:
            status["no fit"] += 1
        elif size < MIN_SIZE:
            status["too small to trust"] += 1
        elif e[second] < tol and e[second] < 2 * e[best] + 0.5:
            status["ambiguous"] += 1
        else:
            scale = float(np.linalg.norm(a, axis=0).mean())
            axis = (a / np.linalg.norm(a, axis=0)).T.ravel()  # COD rows forward/left/up = columns of local->world
            if np.linalg.det(axis.reshape(3, 3)) < 0 or axis_roundtrip_error(axis) > 1e-3:
                status["mirrored or non-orthonormal"] += 1
                continue
            status["confident"] += 1
            out.append({"model": names[best], "origin": r["origin"].astype(float).round(4).tolist(),
                        "angles": [round(x, 4) for x in axis_to_angles(axis)], "axis": axis.round(6).tolist(),
                        "scale": round(scale, 6), "contents": int(r["contents"]), "record": i,
                        "err": round(float(e[best]), 3), "size": round(size, 1)})
    out_path.write_text(json.dumps(out))
    print(dict(status))
    models = Counter(p["model"] for p in out)
    print(f"{len(out)} confident placements, {len(models)} models -> {out_path}")
    print(models.most_common(10))


if __name__ == "__main__":
    main()
