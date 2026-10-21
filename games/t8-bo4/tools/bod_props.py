#!/usr/bin/env python3
# BoD (zm_escape) placement extractor + BoD->MotD(zm_prison) transform solver.
# Offline only. Input is an ACTS entity_list dump (entitylist.json). No game files baked in.
# Run the stub tests with:  python -I bod_props.py --selftest
# Extract real props with:  python -I bod_props.py --entitylist <entitylist.json> --out bod_props.json
# Solve a transform with:   python -I bod_props.py --pairs pairs.json   (see pair schema below)
#
# Confirmed ACTS entitylist schema (read from ate47/bo4-source, 2026-10-21):
#   { "name": str, "spawnVars": [ entity, ... ] }
#   entity = { "modelIndex": int, "origin": str(noise), "angles": str(noise),
#              "spawnVars": [ { "key": str, "type": str, "value": str, "unk1a"?: bool }, ... ] }
# The entity-level origin/angles hold uninitialised float noise; the CLEAN values are the
# "origin"/"angles" key-value pairs inside the nested spawnVars. Props carry a "model" kv.

import argparse, json, math, sys
from pathlib import Path

PROP_CLASSES = {  # entity classnames that place a visible/scripted BoD object
    "script_model", "misc_model", "scriptbundle_scene", "script_brushmodel",
    "script_origin", "script_struct", "trigger_use", "trigger_radius",
}


def _kv(entity):
    out = {}
    for pair in entity.get("spawnVars") or []:
        k = pair.get("key")
        if k is not None:
            out[k] = pair.get("value")
    return out


def _floats(text, n):
    # tolerant parse of a "x y z" value string; returns None when not n finite floats
    if text is None:
        return None
    parts = str(text).replace(",", " ").split()
    if len(parts) != n:
        return None
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None
    return vals if all(math.isfinite(v) for v in vals) else None


def extract_props(entitylist_path):
    data = json.loads(Path(entitylist_path).read_text(encoding="utf-8", errors="replace"))
    ents = data.get("spawnVars") or []
    props, skipped = [], 0
    for ent in ents:
        kv = _kv(ent)
        origin = _floats(kv.get("origin"), 3)
        if origin is None:  # never trust entity-level noise; a prop must have a clean kv origin
            skipped += 1
            continue
        angles = _floats(kv.get("angles"), 3) or [0.0, 0.0, 0.0]
        classname = kv.get("classname")
        model = kv.get("model")
        if classname not in PROP_CLASSES and model is None:
            skipped += 1
            continue
        scale = _floats(kv.get("modelscale"), 1) or _floats(kv.get("scale"), 1) or [1.0]
        props.append({
            "classname": classname,
            "targetname": kv.get("targetname"),
            "objectid": kv.get("objectid"),
            "scriptbundlename": kv.get("scriptbundlename") or kv.get("bundle"),
            "model": model,
            "modelIndex": ent.get("modelIndex"),
            "origin": origin,
            "angles": angles,
            "scale": scale[0],
            "spawnflags": kv.get("spawnflags"),
        })
    return props, skipped


# ---- transform: BoD source point -> MotD(zm_prison) target point ---------------------
# Rigid yaw-about-Z + translation (T7/T8 share inch units => no XY scale), optional X mirror,
# Z handled as offset (scale 1). Nothing is baked in; the caller supplies landmark pairs.

def _solve_yaw_xy(src, dst):
    n = len(src)
    cs = (sum(p[0] for p in src) / n, sum(p[1] for p in src) / n)
    cd = (sum(p[0] for p in dst) / n, sum(p[1] for p in dst) / n)
    sxx = sxy = syx = syy = 0.0
    for s, d in zip(src, dst):
        ax, ay = s[0] - cs[0], s[1] - cs[1]
        bx, by = d[0] - cd[0], d[1] - cd[1]
        sxx += ax * bx; sxy += ax * by; syx += ay * bx; syy += ay * by
    theta = math.atan2(sxy - syx, sxx + syy)  # 2D Procrustes optimal rotation
    c, s_ = math.cos(theta), math.sin(theta)
    tx = cd[0] - (c * cs[0] - s_ * cs[1])
    ty = cd[1] - (s_ * cs[0] + c * cs[1])
    return theta, (c, s_), (tx, ty)


def _apply_xy(pt, rot, t):
    c, s_ = rot
    return (c * pt[0] - s_ * pt[1] + t[0], s_ * pt[0] + c * pt[1] + t[1])


def solve_transform(pairs, allow_mirror=True):
    # pairs = [ {"bod":[x,y,z], "motd":[x,y,z], "name"?:str}, ... ]
    if len(pairs) < 2:
        raise ValueError("need >= 2 landmark pairs (3+ recommended)")
    best = None
    for mirror in ((False, True) if allow_mirror else (False,)):
        src = [((-p["bod"][0] if mirror else p["bod"][0]), p["bod"][1], p["bod"][2]) for p in pairs]
        dst = [p["motd"] for p in pairs]
        theta, rot, t = _solve_yaw_xy(src, dst)
        zoff = sum(d[2] - s[2] for s, d in zip(src, dst)) / len(pairs)
        res = []
        for s, d in zip(src, dst):
            px, py = _apply_xy(s, rot, t)
            pz = s[2] + zoff
            res.append(math.dist((px, py, pz), d))
        rms = math.sqrt(sum(r * r for r in res) / len(res))
        cand = {"mirror_x": mirror, "yaw_deg": math.degrees(theta) % 360.0,
                "translation": [t[0], t[1], zoff], "rms_error": rms,
                "per_pair_error": res}
        if best is None or rms < best["rms_error"]:
            best = cand
    return best


def transform_point(pt, tf):
    x = -pt[0] if tf["mirror_x"] else pt[0]
    th = math.radians(tf["yaw_deg"]); c, s_ = math.cos(th), math.sin(th)
    tx, ty, tz = tf["translation"]
    return [c * x - s_ * pt[1] + tx, s_ * x + c * pt[1] + ty, pt[2] + tz]


# ---- stub tests ----------------------------------------------------------------------

def _synth_entitylist():
    def ent(cls, origin, angles="0 0 0", model=None, extra=None):
        sv = [{"key": "classname", "type": "string", "value": cls},
              {"key": "origin", "type": "string", "value": origin},
              {"key": "angles", "type": "string", "value": angles}]
        if model:
            sv.append({"key": "model", "type": "string", "value": model})
        for k, v in (extra or {}).items():
            sv.append({"key": k, "type": "string", "value": v})
        return {"modelIndex": 7, "origin": "5.0476e-41 3008 9376", "angles": "nan 0 0", "spawnVars": sv}
    return {"name": "#maps/zm/zm_escape.d3dbsp", "spawnVars": [
        ent("scriptbundle_scene", "-1815 8033 1432", "0 276 0", extra={"targetname": "s_warden_box", "objectid": "warden_box"}),
        ent("script_model", "100 200 1376", "0 90 0", model="p7_zm_al_perk_jug"),
        ent("mp_tdm_spawn", "3008 9376 1376", "0 90 0"),           # no model, not a prop class -> skipped
        ent("script_struct", "512 -256 1400", "0 45 0", extra={"targetname": "pap_quest_01"}),
    ]}


def _selftest():
    import tempfile, os
    ok = True
    # 1) extractor against the confirmed schema
    tmp = Path(tempfile.gettempdir()) / "_bod_stub_entitylist.json"
    tmp.write_text(json.dumps(_synth_entitylist()), encoding="utf-8")
    props, skipped = extract_props(tmp)
    names = {p["targetname"] for p in props}
    assert len(props) == 3, f"expected 3 props, got {len(props)}"
    assert skipped == 1, f"expected 1 skipped (mp_tdm_spawn), got {skipped}"
    box = next(p for p in props if p["targetname"] == "s_warden_box")
    assert box["origin"] == [-1815.0, 8033.0, 1432.0], box["origin"]
    assert box["angles"] == [0.0, 276.0, 0.0], box["angles"]
    assert "pap_quest_01" in names
    jug = next(p for p in props if p["model"] == "p7_zm_al_perk_jug")
    assert jug["origin"] == [100.0, 200.0, 1376.0]
    print("[ok] extractor: 3 props, 1 skipped, clean kv origins parsed, noise ignored")
    os.remove(tmp)

    # 2) transform solver recovers a known yaw+translation (no mirror)
    import random
    rng = random.Random(1)
    true_yaw, true_t = 123.0, (400.0, -900.0, 56.0)
    th = math.radians(true_yaw); c, s_ = math.cos(th), math.sin(th)
    bod = [(rng.uniform(-4000, 4000), rng.uniform(-4000, 4000), rng.uniform(1300, 1500)) for _ in range(5)]
    motd = [[c * x - s_ * y + true_t[0], s_ * x + c * y + true_t[1], z + true_t[2]] for (x, y, z) in bod]
    pairs = [{"bod": list(b), "motd": m} for b, m in zip(bod, motd)]
    tf = solve_transform(pairs, allow_mirror=True)
    assert not tf["mirror_x"], "should not pick mirror for a non-mirrored case"
    assert abs(((tf["yaw_deg"] - true_yaw + 180) % 360) - 180) < 1e-3, tf["yaw_deg"]
    assert tf["rms_error"] < 1e-6, tf["rms_error"]
    # round-trip a fresh point
    p = (1234.0, -567.0, 1410.0)
    exp = [c * p[0] - s_ * p[1] + true_t[0], s_ * p[0] + c * p[1] + true_t[1], p[2] + true_t[2]]
    got = transform_point(p, tf)
    assert max(abs(a - b) for a, b in zip(exp, got)) < 1e-6
    print(f"[ok] transform: recovered yaw {tf['yaw_deg']:.3f} deg (true 123), rms {tf['rms_error']:.2e}")

    # 3) transform solver detects an X mirror
    bodm = [(-x, y, z) for (x, y, z) in bod]
    motdm = [[c * x - s_ * y + true_t[0], s_ * x + c * y + true_t[1], z + true_t[2]] for (x, y, z) in bodm]
    pairs2 = [{"bod": list(b), "motd": m} for b, m in zip(bod, motdm)]  # bod un-mirrored, target implies mirror
    tf2 = solve_transform(pairs2, allow_mirror=True)
    assert tf2["mirror_x"], "should detect the X mirror"
    assert tf2["rms_error"] < 1e-6, tf2["rms_error"]
    print(f"[ok] transform: mirror case detected (mirror_x={tf2['mirror_x']}, rms {tf2['rms_error']:.2e})")
    print("ALL STUB TESTS PASSED")
    return ok


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--entitylist")
    ap.add_argument("--out", default="bod_props.json")
    ap.add_argument("--pairs", help="JSON file: [{bod:[x,y,z],motd:[x,y,z],name?}]")
    ap.add_argument("--no-mirror", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return 0 if _selftest() else 1
    if args.entitylist:
        props, skipped = extract_props(args.entitylist)
        Path(args.out).write_text(json.dumps(props, indent=1), encoding="utf-8")
        print(f"wrote {len(props)} props to {args.out} ({skipped} entities skipped)")
    if args.pairs:
        pairs = json.loads(Path(args.pairs).read_text(encoding="utf-8"))
        tf = solve_transform(pairs, allow_mirror=not args.no_mirror)
        print(json.dumps(tf, indent=1))
    if not (args.entitylist or args.pairs):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
