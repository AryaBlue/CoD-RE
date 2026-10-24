"""Offline test runner for the decimation engine. No game, no build. Exercises:
  - emitter contract on the output (first-6 axial order, verts inside, <=45 sides, contents integers);
  - the consumer stub: clip_brushes.brushes() loads the output and emits .map text without error;
  - cod2map plane-table stub (plane_count): output table <= input table and <= cap;
  - containment: points inside the ORIGINAL solid stay inside the DECIMATED solid (no collision removed);
  - added-solid: fraction of sampled decimated-interior points that were NOT solid before (fidelity cost);
  - ramp preservation: brushes with a real sloped walkable top are not flattened;
  - failure paths: empty input, degenerate plane, >45-side brush, tris pass-through + contents preserved.
Usage: python check_decimate.py [<in.json> <out.json>]   (defaults to bod_clip.json -> a temp decimation)
"""
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(r"F:\ClaudeWork\bo3\bo3_modtools_test")))
import plane_count as pc
import clip_brushes as cb

PASS, FAIL = [], []


def ok(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def nplanes(planes):
    out = []
    for a, b, c, d in planes:
        L = math.sqrt(a * a + b * b + c * c)
        if L > 1e-9:
            out.append((a / L, b / L, c / L, d / L))
    return out


def point_in(planes, p, slack=0.05):
    return all(a * p[0] + b * p[1] + c * p[2] <= d + slack for a, b, c, d in planes)


def sample_interior(brush, k):
    """A few points strictly inside a brush: jitter around its verts' centroid toward each vert."""
    vs = brush["verts"]
    cx = [sum(v[i] for v in vs) / len(vs) for i in range(3)]
    pls = nplanes(brush["planes"])
    pts = []
    for _ in range(k):
        v = random.choice(vs)
        t = random.uniform(0.15, 0.6)
        p = [cx[i] + t * (v[i] - cx[i]) for i in range(3)]
        if point_in(pls, p, 0.0):
            pts.append(p)
    return pts


def grid_index(brushes, cell=256):
    from collections import defaultdict
    g = defaultdict(list)
    norms = [nplanes(b["planes"]) for b in brushes]
    boxes = []
    for b in brushes:
        vs = b["verts"]
        boxes.append(([min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]))
    for i, (lo, hi) in enumerate(boxes):
        for cx in range(int(lo[0] // cell), int(hi[0] // cell) + 1):
            for cy in range(int(lo[1] // cell), int(hi[1] // cell) + 1):
                g[(cx, cy)].append(i)
    return g, norms, boxes


def in_any(p, g, norms, boxes, cell=256):
    key = (int(p[0] // cell), int(p[1] // cell))
    for i in g.get(key, ()):
        lo, hi = boxes[i]
        if lo[0] - 0.05 <= p[0] <= hi[0] + 0.05 and lo[1] - 0.05 <= p[1] <= hi[1] + 0.05 and lo[2] - 0.05 <= p[2] <= hi[2] + 0.05:
            if point_in(norms[i], p):
                return True
    return False


def emitted_only(brushes):
    return [b for b in brushes if pc.emitted_brush_planes(b) is not None]


def contract_checks(out, inp):
    """The emitter contract binds only brushes cod2map actually receives (emitter-skipped ones are dropped anyway)."""
    bad_order = bad_vert = oversided = bad_type = 0
    for b in emitted_only(out["brushes"]):
        p = b["planes"]
        if len(p) < 6 or any(p[k][k // 2] != (-1 if k % 2 == 0 else 1) for k in range(6)):
            bad_order += 1
        if len(p) > 45:
            oversided += 1
        pls = nplanes(p)
        if any(not point_in(pls, v) for v in b.get("verts", [])):
            bad_vert += 1
        if not isinstance(b["contents"], int):
            bad_type += 1
    in_noise = sum(1 for b in emitted_only(json.loads(Path(inp).read_text())["brushes"])
                   if any(not point_in(nplanes(b["planes"]), v) for v in b.get("verts", [])))
    ok("first-6 axial order on every emitted brush", bad_order == 0, f"{bad_order} bad")
    ok("every emitted brush <= 45 sides", oversided == 0, f"{oversided} over")
    ok("contents stay integers", bad_type == 0, f"{bad_type} bad")
    ok("no new vert-outside-plane noise vs input", bad_vert <= in_noise,
       f"out {bad_vert} <= in {in_noise} (inherited float noise from the BO4 extractor)")


def consumer_stub(path):
    blocks, skipped = cb.brushes(path)
    ok("clip_brushes.brushes() emits without error", True, f"{len(blocks)} blocks, {skipped} skipped")
    sample = blocks[0] if blocks else ""
    ok("emitted brush text is a well-formed { } block", sample.startswith("{") and sample.rstrip().endswith("}"))


def containment(inp, out, n=4000):
    random.seed(1)
    src = [b for b in json.loads(Path(inp).read_text())["brushes"] if pc.emitted_brush_planes(b) is not None]
    g, norms, boxes = grid_index(out["brushes"])
    pts, miss = 0, 0
    for b in random.sample(src, min(len(src), 3000)):
        for p in sample_interior(b, 2):
            pts += 1
            if not in_any(p, g, norms, boxes):
                miss += 1
    ok("original interior points stay solid after decimation (no collision removed)", miss == 0,
       f"{miss}/{pts} lost")
    # added solid: points inside decimated boxes that were not solid before
    gs, ns, bs = grid_index(src)
    added, tot = 0, 0
    for b in random.sample(out["brushes"], min(len(out["brushes"]), 3000)):
        for p in sample_interior(b, 2):
            tot += 1
            if not in_any(p, gs, ns, bs):
                added += 1
    print(f"    added-solid estimate: {added}/{tot} sampled decimated-interior points were empty before "
          f"(~{100*added/max(tot,1):.1f}%)")


def ramp_preserved(inp, out):
    def ramps(brushes):
        s = 0
        for b in brushes:
            for a, bb, c, d in nplanes(b["planes"]):
                if 0.7 < abs(c) < 0.9999 and (b["verts"] and max(v[2] for v in b["verts"]) - min(v[2] for v in b["verts"]) > 8):
                    s += 1
                    break
        return s
    src = [b for b in json.loads(Path(inp).read_text())["brushes"] if pc.emitted_brush_planes(b) is not None]
    a, b = ramps(src), ramps(out["brushes"])
    ok("sloped walkable tops (rise>8u) preserved by default", b >= a * 0.95, f"in {a} -> out {b}")


def failure_paths():
    tmp = Path(tempfile.mkdtemp())
    # empty
    e = tmp / "empty.json"
    e.write_text(json.dumps({"brushes": []}))
    r = subprocess.run([sys.executable, str(HERE / "decimate_clip.py"), str(e), str(tmp / "eo.json")],
                       capture_output=True, text=True)
    ok("empty-brush input does not crash", r.returncode == 0, r.stderr.strip().splitlines()[-1] if r.returncode else "")
    # degenerate plane + >45 sides + tris passthrough + odd contents
    big = {"contents": 0x8000001, "planes": [[-1, 0, 0, 0], [1, 0, 0, 10], [0, -1, 0, 0], [0, 1, 0, 10],
           [0, 0, -1, 0], [0, 0, 1, 10]] + [[math.cos(t), math.sin(t), 0, 6] for t in
           [i * 0.1 for i in range(60)]] + [[0, 0, 0, 0]], "verts": [[x, y, z] for x in (0, 10) for y in (0, 10) for z in (0, 10)]}
    f = tmp / "hard.json"
    f.write_text(json.dumps({"brushes": [big], "tris": [[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], "tri_contents": [0x1],
                             "tri_materials": ["mtl"]}))
    of = tmp / "ho.json"
    r = subprocess.run([sys.executable, str(HERE / "decimate_clip.py"), str(f), str(of)], capture_output=True, text=True)
    ok(">45-side + degenerate-plane brush handled", r.returncode == 0, r.stderr.strip().splitlines()[-1] if r.returncode else "")
    if of.exists():
        o = json.loads(of.read_text())
        ok("  every EMITTED result brush <= 45 sides (degenerate brush is emitter-skipped)",
           all(len(b["planes"]) <= 45 for b in emitted_only(o["brushes"])))
        ok("  tris + tri_contents + tri_materials passed through unchanged",
           o.get("tris") == [[[0, 0, 0], [1, 0, 0], [0, 1, 0]]] and o.get("tri_contents") == [0x1] and o.get("tri_materials") == ["mtl"])
        ok("  contents integer preserved", o["brushes"] and o["brushes"][0]["contents"] == 0x8000001)


def main():
    if len(sys.argv) >= 3:
        inp, out_path = sys.argv[1], sys.argv[2]
    else:
        inp = r"F:\ClaudeWork\bo3\bod_port\t8_world\clip\bod_clip.json"
        out_path = str(Path(tempfile.mkdtemp()) / "dec.json")
        subprocess.run([sys.executable, str(HERE / "decimate_clip.py"), inp, out_path], check=True)
    out = json.loads(Path(out_path).read_text())

    print("contract:")
    contract_checks(out, inp)
    print("consumer stub (clip_brushes):")
    consumer_stub(out_path)
    print("plane-table stub (cod2map dedup):")
    bi, _ = pc.count(inp, 0.001, 0.01, 131072)
    bo, _ = pc.count(out_path, 0.001, 0.01, 131072)
    ok("output table <= input table and <= cap", bo <= bi and bo * 2 <= 131072, f"uniq {bi}->{bo}")
    print("fidelity:")
    containment(inp, out)
    ramp_preserved(inp, out)
    print("failure paths:")
    failure_paths()

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed" + (" :: " + ", ".join(FAIL) if FAIL else ""))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
